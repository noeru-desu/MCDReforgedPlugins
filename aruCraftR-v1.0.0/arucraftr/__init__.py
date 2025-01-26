
import asyncio
from typing import Any, Optional

from mcdreforged.api.types import PluginServerInterface, Info

from . import shared
from .command import register_commands
from .config import Config
from .websocket import WebSocketMessage, send_msg, ws_loop
from .info_filter import CustomInfoFilter
from .event import ArcEvent


async def on_load(server: PluginServerInterface, prev_module: Optional[Any]):
    shared.plg_server_inst = server
    shared.config = server.load_config_simple(target_class=Config)
    server.save_config_simple(shared.config)
    register_commands(server)
    if shared.config.info_filter: # type: ignore
        CustomInfoFilter.rebuild_filter_cache(shared.config.info_filter) # type: ignore
        server.register_info_filter(CustomInfoFilter())
    shared.ws_future = asyncio.run_coroutine_threadsafe(ws_loop(), shared.plg_server_inst.get_event_loop())


async def on_unload(server: PluginServerInterface):
    shared.ws_future.cancel()
    if shared.ws_connection is not None:
        await shared.ws_connection.close(reason='插件卸载')


async def on_server_startup(server: PluginServerInterface):
    await ArcEvent.server_startup.report()


async def on_server_stop(server: PluginServerInterface, server_return_code: int):
    await ArcEvent.server_stop.report(code=server_return_code)


async def on_user_info(server: PluginServerInterface, info: Info):
    if info.content is None or not info.content.startswith(shared.config.forwarding_message_prefix):
        return
    if not (msg := info.content.lstrip('.')):
        return
    player = '控制台' if info.player is None else info.player
    await send_msg(WebSocketMessage('forward', f'<{player}> {msg}'))
    info.cancel_send_to_server()


def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    try:
        if server.get_permission_level(player) >= 3:
            server.execute(f'tag {player} add admin')
    except Exception as e:
        shared.plg_server_inst.logger.warning(f'尝试检测{player}的权限时失败: {repr(e)}')
