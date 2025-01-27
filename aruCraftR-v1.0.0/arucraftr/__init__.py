
import asyncio
import re
from typing import Any, Optional

from mcdreforged.api.types import PluginServerInterface, Info

from arucraftr import shared
from arucraftr.mcdr.command import register_commands
from arucraftr.config import Config
from arucraftr.websocket import send_msg
from arucraftr.websocket.handler import WebSocketMessage, ws_loop
from arucraftr.websocket.types import WebSocketMessage
from arucraftr.mcdr.info_filter import CustomInfoFilter
from arucraftr.websocket.event import ArcEvent
from arucraftr.utils import tell_admin


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


bots = set()


async def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    try:
        if server.get_permission_level(player) >= 3:
            server.execute(f'tag {player} add admin')
    except Exception as e:
        shared.plg_server_inst.logger.warning(f'尝试检测{player}的权限时失败: {repr(e)}')
    await ArcEvent.player_joined.report(player=player, is_bot=False)
    # bot检测并记录到bots


async def on_player_left(server: PluginServerInterface, player: str):
    if player in bots:
        bots.remove(player)
    await ArcEvent.player_left.report(player=player)



list_re = re.compile(r'There are \d+ of a max of \d+ players online: (.+)')

async def on_info(server: PluginServerInterface, info: Info):
    if (not info.is_from_server) or info.content is None:
        return
    if info.content.startswith('There'):
        await match_online_list(info.content)


async def match_online_list(content: str):
    regex = re.match(list_re, content)
    players_str = regex.group()
    try:
        players = (i.strip(' ') for i in players_str.split(','))
    except (ValueError, AttributeError) as e:
        tell_admin(f'玩家列表解析失败, 匹配目标[{players_str}]: {repr(e)}')
    else:
        await ArcEvent.update_player_list.report(player_list=[[i, i in bots] for i in players])
        shared.plg_server_inst.logger.info(f'已上报玩家列表: {players}')
