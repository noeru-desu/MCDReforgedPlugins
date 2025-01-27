
from websockets import State

from arucraftr import shared
from arucraftr.websocket.types import WebSocketMessage


async def send_msg(message: WebSocketMessage):
    if shared.ws_connection is not None and shared.ws_connection.state == State.OPEN:
        await shared.ws_connection.send(message.json, True)



