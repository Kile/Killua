import sys, os, json
from quart import jsonify, Quart, request
from zmq import REQ
from zmq.asyncio import Context
from datetime import datetime
from typing import List, Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # This is a necessary hacky fix for importing issues
sys.path.append(os.path.dirname(SCRIPT_DIR))

with open("config.json", "r") as config_file: # Needs to be read here again else hypercorn will get mad
    config = json.loads(config_file.read())

PASSWORD = config["password"]
# PORT = config["port"]
IPC_TOKEN: str = config["ipc"]

commands_chache = {}

ratelimit_manager: Dict[str, List[datetime]] = {}
ratelimited = {}

app = Quart(__name__)

# Create async IPC request maker
async def make_request(route: str, data: dict) -> dict:
    context = Context()
    socket = context.socket(REQ)
    # socket.setsockopt_string()
    socket.plain_username = b"killua"
    socket.plain_password = IPC_TOKEN.encode("UTF-8")
    socket.connect("tcp://localhost:5555")

    await socket.send_json({"route": route, "data": data})
    return socket.recv_json()

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
        commands_chache = await (await make_request("commands", data = {}))

    return jsonify(commands_chache), 200

@app.route("/stats/", methods=["GET"])
async def stats():
    """Returns bot stats"""
    # Check for ratetlimit
    if not check_ratelimit(request.remote_addr) if request.remote_addr else check_ratelimit(request.headers["X-Forwarded-For"]):
        return jsonify({"error": "You are ratelimited"}), 429
        
    return jsonify(await (await make_request("stats", data = {}))), 200

@app.errorhandler(404)
def page_not_found(_):
    return jsonify({"error": "Not found. You should not be on this page."}), 404