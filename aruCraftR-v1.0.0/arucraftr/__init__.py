
import asyncio
from typing import Any, Callable, Optional

from mcdreforged.api.types import PluginServerInterface, Info, InfoFilter

from . import shared
from .command import register_commands
from .config import Config, InfoFilterConfig, InfoFilterMethod
from .websocket import ws_loop


async def on_load(server: PluginServerInterface, prev_module: Optional[Any]):
    shared.plg_server_inst = server
    shared.config = server.load_config_simple(target_class=Config)
    register_commands(server)
    if shared.config.info_filter: # type: ignore
        CustomInfoFilter.rebuild_filter_cache(shared.config.info_filter) # type: ignore
        server.register_info_filter(CustomInfoFilter())
    shared.ws_future = asyncio.run_coroutine_threadsafe(ws_loop(), asyncio.get_running_loop())


async def on_unload(server: PluginServerInterface):
    shared.ws_future.cancel()
    if hasattr(shared, 'ws_connection'):
        await shared.ws_connection.close(reason='插件卸载')


class CustomInfoFilter(InfoFilter):
    filter_cache: list[Callable[[str], bool]]
    def filter_server_info(self, info: Info) -> bool:
        if (content := info.content) is None:
            return True
        return not any(i(content) for i in self.filter_cache) # type: ignore

    @classmethod
    def rebuild_filter_cache(cls, filters: list[InfoFilterConfig]):
        filter_cache = []
        for i in filters:
            target = i.target
            match i.method:
                case InfoFilterMethod.keyword:
                    filter_cache.append(lambda x: target in x)
                case InfoFilterMethod.startswith:
                    filter_cache.append(lambda x: x.startswith(target))
                case InfoFilterMethod.endswith:
                    filter_cache.append(lambda x: x.endswith(target))
        cls.filter_cache = filter_cache
