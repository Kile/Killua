import sys, os
from quart import jsonify, Quart, request
from zmq import REQ
from zmq.asyncio import Context

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # This is a necessary hacky fix for importing issues
sys.path.append(os.path.dirname(SCRIPT_DIR))

from static.constants import PASSWORD, IPC_TOKEN

app = Quart(__name__)

# Create async IPC request maker
async def make_request(route: str, data: dict) -> dict:
    context = Context()
    socket = context.socket(REQ)
    socket.connect("tcp://localhost:5555")

    await socket.send_json({"route": route, "data": data})
    return socket.recv_json()

async def is_authorised(headers: dict) -> bool:
    if not "Authorization" in headers:
        return False

    if headers["Authorization"] != PASSWORD:
        return False

    return True

@app.route("/vote/", methods=["POST", "PUT"])
async def vote():
    """Handles a vote event and calls the right function within the bots code"""

    if not await is_authorised(request.headers):
        return jsonify({"error": "Unauthorised"}), 401
        
    data = await request.get_json()

    await make_request("vote", data = dict(data))

    return jsonify({"message": "Success"}), 200

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Not found. You should not be on this page."}), 404