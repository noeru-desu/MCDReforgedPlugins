

from enum import Enum
from typing import Optional

from mcdreforged.api.event import PluginEvent

from . import shared
from .websocket import WebSocketMessage, send_msg


events = {}


class Event(PluginEvent):
    def __init__(self, event_id: str, debug_kwargs: Optional[dict] = None):
        super().__init__(event_id)
        self.debug_kwargs = {} if debug_kwargs is None else debug_kwargs


class ArcEvent(Enum):
    server_startup = Event('arc.server_startup')
    server_stop = Event('arc.server_stop', {'code': '测试'})

    @classmethod
    def get(cls, name: str) -> Optional['ArcEvent']:
        return cls.__members__.get(name)

    async def report(self, **kwargs):
        await send_msg(WebSocketMessage('event', self.data(kwargs)))

    async def debug_report(self):
        await send_msg(WebSocketMessage('event', self.data(self.value.debug_kwargs)))

    def data(self, kwargs) -> dict:
        return {'name': self.name, 'kwargs': kwargs}
