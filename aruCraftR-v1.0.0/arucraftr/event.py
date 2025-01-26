

from enum import Enum
from typing import Any, Optional, Tuple
import json as jsonlib

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
        await send_msg(WebSocketMessage('event', self.data(kwargs)))

    def data(self, kwargs) -> dict:
        return {'name': self.name, 'kwargs': kwargs}
