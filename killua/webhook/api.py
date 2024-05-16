import sys, os, json
from quart import jsonify, Quart, request
from zmq import DEALER, POLLIN
from zmq.asyncio import Context, Poller
from datetime import datetime
from typing import List, Dict
import uuid
from quart_cors import cors
from cachetools import TTLCache

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # This is a necessary hacky fix for importing issues
sys.path.append(os.path.dirname(SCRIPT_DIR))

with open("config.json", "r") as config_file: # Needs to be read here again else hypercorn will get mad
    config = json.loads(config_file.read())

PASSWORD = config["password"]
# PORT = config["port"]
IPC_TOKEN: str = config["ipc"]

commands_chache = {}

ratelimit_manager: TTLCache[str, List[datetime]] = TTLCache(maxsize=100, ttl=600)
ratelimited = {}

app = Quart(__name__)

app = cors(app, allow_origin="*")

# Create async IPC request maker
async def make_request(route: str, data: dict) -> dict:
    context = Context.instance()
    socket = context.socket(DEALER)
    socket.identity = uuid.uuid4().hex.encode('utf-8')
    socket.plain_username = b"killua"
    socket.plain_password = IPC_TOKEN.encode("UTF-8")
    socket.connect("tcp://localhost:5555")

    request = json.dumps({"route": route, "data": data}).encode('utf-8')
    socket.send(request)

    poller = Poller()
    poller.register(socket, POLLIN)

    while True:
        events = dict(await poller.poll())
        if socket in events and events[socket] == POLLIN:
            multipart = json.loads((await socket.recv_multipart())[0].decode())
            socket.close()
            context.term()
            return multipart

async def is_authorised(headers: dict) -> bool:
    if not "Authorization" in headers:
        return False

    if headers["Authorization"] != PASSWORD:
        return False

    return True

def check_ratelimit(ip: str) -> bool:
    """Checks if the user is ratelimited, returns false if they are. Also ratelimit a user if they made more than 5 requests in 5 seconds"""
    now = datetime.now()
    
    if ip in ratelimited:
        if (now - ratelimited[ip]).seconds/3600 >= 1: # One hour ratelimit
            del ratelimited[ip]
            return True
        else:
            return False
        
    if ip in ratelimit_manager:
        recent_requests = 0
        for i in ratelimit_manager[ip]:
            if (now - i).seconds < 5:
                recent_requests += 1
            if recent_requests > 5:
                ratelimited[ip] = now
                return False
            
    if ip in ratelimit_manager:
        ratelimit_manager[ip].append(now)
    else:
        ratelimit_manager[ip] = [now]
        
    return True

@app.route("/vote/", methods=["POST", "PUT"])
async def vote():
    """Handles a vote event and calls the right function within the bots code"""

    if not await is_authorised(request.headers):
        return jsonify({"error": "Unauthorised"}), 401
        
    data = await request.get_json()
    
    if data is None:
        return jsonify({"error": "No request body provided"}), 400

    await make_request("vote", data = dict(data))

    return jsonify({"message": "Success"}), 200

@app.route("/commands/", methods=["GET"])
async def commands():
    """Returns a list of all commands"""
    global commands_chache
    
    # Check for ratetlimit
    if not check_ratelimit(request.remote_addr) if request.remote_addr else check_ratelimit(request.headers["X-Forwarded-For"]):
        return jsonify({"error": "You are ratelimited"}), 429
    
    if not commands_chache:
        commands_chache = await make_request("commands", data = {})

    return jsonify(commands_chache), 200

@app.route("/stats/", methods=["GET"])
async def stats():
    """Returns bot stats"""
    # Check for ratetlimit
    if not check_ratelimit(request.remote_addr) if request.remote_addr else check_ratelimit(request.headers["X-Forwarded-For"]):
        return jsonify({"error": "You are ratelimited"}), 429
        
    return jsonify(await make_request("stats", data = {})), 200

@app.errorhandler(404)
def page_not_found(_):
    return jsonify({"error": "Not found. You should not be on this page."}), 404