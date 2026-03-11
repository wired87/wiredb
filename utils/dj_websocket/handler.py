import os

from qbrain.graph.utils import Utils

class ConnectionManager:

    """
    Utils class for vaidation and connection store
    """

    def __init__(self):
        self.all_ips_len = None
        local_origins = ["127.0.0.1", "localhost"]
        prod_origins =  ["bestbrain.tech"]
        self.request_urls = []
        self.allowed_origins = local_origins if os.name == "nt" else prod_origins
        self.active_connections = {}

        self.all_ready = False
        self.utils = Utils()
        self.all_authenticated = False


    async def connect(self, websocket, env_id):
        granted = await self._validate_origin(env_id, websocket)
        if granted and env_id not in self.active_connections:
            #
            self.active_connections[env_id] = websocket





    async def _validate_origin(self, env_id, websocket):
        print(f"validate received WS request to Host ")
        def validate_sender_url():
            ok = False
            for item in self.allowed_origins:
                if websocket.url.hostname.startswith(item):
                    ok=True
            return ok

        if validate_sender_url():
            print("connection accepted")
            await websocket.accept()
            return websocket.url.hostname
        else:
            print("connection declined")
            await websocket.close(code=1008)
            return None



















class WebsocketHandler:
    """
    """

    def __init__(self, uri):
        self.uri=uri
        print("WS handler initialized")

    async def establish_connection(self):
        try:
            print(f"Establish connection to {self.uri}")
            return websockets.connect(self.uri)
        except Exception as e:
            print("WS couldn't be established:", e)

