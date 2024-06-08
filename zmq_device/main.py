import logging
import os
import sys

import zmq

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

client_address = os.environ["ZMQ_CLIENT_ADDRESS"]
server_address = os.environ["ZMQ_SERVER_ADDRESS"]


def main():
    client, server, context = None, None, None
    try:
        logging.info("Starting device")
        context = zmq.Context(1)
        # Socket facing clients
        client = context.socket(zmq.XREP)
        client.bind(client_address)
        # Socket facing services
        server = context.socket(zmq.XREQ)
        server.bind(server_address)

        zmq.device(zmq.QUEUE, client, server)
    except Exception as e:
        logging.error("Device terminating due to error {}".format(e))
    finally:
        if client:
            client.close()
        if server:
            server.close()
        context.term()


if __name__ == "__main__":
    main()