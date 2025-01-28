

from collections import OrderedDict
from enum import Enum
from typing import Any, Optional

from mcdreforged.api.event import PluginEvent

from arucraftr import shared
from arucraftr.websocket import send_msg
from arucraftr.websocket.types import WebSocketMessage


events = {}


class WsEvent(PluginEvent):
    def __init__(self, event_id: str, default_kwargs: Optional[OrderedDict[str, Any]] = None, debug_kwargs: Optional[dict[str, Any]] = None):
        super().__init__(event_id)
        self.id = f'acr.{event_id}'
        self.ws_id = event_id
        self.default_kwargs = default_kwargs
        self.debug_kwargs = {} if debug_kwargs is None else debug_kwargs

    def dispatch(self, kwargs: Optional[dict[str, Any]] = None):
        """调用MCDR的事件分发方法, 由于MCDR限制, 目标方法的参数顺序必须与默认kwargs相同

        Args:
            kwargs (可选dict): 用于当前事件的关键字参数. None则使用默认值
        """
        if self.default_kwargs is None:
            shared.plg_server_inst.dispatch_event(self, ())
        else:
            if kwargs is None:
                available_kwargs = self.default_kwargs
            else:
                available_kwargs = self.default_kwargs.copy()
                available_kwargs.update(kwargs)
            shared.plg_server_inst.dispatch_event(self, tuple(available_kwargs.values()))

    async def report(self, kwargs: Optional[dict[str, Any]] = None):
        """上报事件到Nonebot插件

        Args:
            kwargs (可选dict): 用于当前事件的关键字参数. None时使用调试参数
        """
        if kwargs is None:
            kwargs = self.debug_kwargs
        await send_msg(WebSocketMessage('event', {'name': self.ws_id, 'kwargs': kwargs}))


class ArcEvent(Enum):
    server_startup = WsEvent(
        'server_startup'
    )
    server_stop = WsEvent(
        'server_stop', OrderedDict(code='未知'),
        {'code': '测试'}
    )
    player_joined = WsEvent(
        'player_joined', OrderedDict(player='未知', is_bot=True),
        {'player': '测试', 'is_bot': True}
    )
    player_left = WsEvent(
        'player_left', OrderedDict(player='未知'),
        {'player': '测试'}
    )
    update_player_list = WsEvent(
        'update_player_list', OrderedDict(player_list=[]),
        {'player_list': [('测试', True)]}
    )
    crash = WsEvent(
        'crash', OrderedDict(crash_report=OrderedDict()),
        {'crash_report': OrderedDict()}
    )

    @classmethod
    def get(cls, name: str) -> Optional['ArcEvent']:
        return cls.__members__.get(name)

    def dispatch(self, kwargs):
        self.value.dispatch(kwargs)

    async def report(self, **kwargs):
        await self.value.report(kwargs)

    async def debug_report(self):
        await self.value.report()
