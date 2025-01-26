

from enum import Enum
from typing import Any, Optional, Tuple

from mcdreforged.api.event import LiteralEvent

from . import shared
from .websocket import WebSocketMessage, send_msg


events = {}


class ArcEvent(Enum):
    server_startup = LiteralEvent('arc.server_startup')
    server_stop = LiteralEvent('arc.server_stop')

    @classmethod
    def get(cls, name: str) -> Optional['ArcEvent']:
        return cls.__members__.get(name)

    async def report(self, **kwargs):
        await send_msg(WebSocketMessage('event', {'name': self.name, 'kwargs': kwargs}))


def dispatch_event(event: ArcEvent, kwargs: dict[str, Any]):
    pass
    # shared.plg_server_inst.dispatch_event(event.value, kwargs)
