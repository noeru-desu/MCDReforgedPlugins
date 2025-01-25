
import json as jsonlib

from mcdreforged.api.types import PluginServerInterface, CommandSource
from mcdreforged.api.rtext import RText, RColor, RTextList
from mcdreforged.api.command import Text, GreedyText, Literal
from mcdreforged.command.builder.tools import Requirements

from . import shared
from .config import Config
from .websocket import exec_json as _exec_json

CMD = '!!acr'

def admin_literal(literal: str):
    return Literal(literal).requires(Requirements.has_permission(3), lambda src: RText('权限不足', RColor.red))

def console_literal(literal: str):
    return Literal(literal).requires(Requirements.is_console(), lambda src: RText('仅允许控制台执行json命令', RColor.red))

hr = RText('-----', color=RColor.gray)
cmd = RText(CMD)

HELP = f"""{RTextList(hr, RText('插件帮助信息', color=RColor.dark_aqua), RText('插件帮助信息', color=RColor.gray), hr)}
{RTextList(cmd, ' ', RText('reload', color=RColor.gold), RText(' | 重载配置文件', color=RColor.gray))}
{RTextList(cmd, ' ', RText('reconnect', color=RColor.gold), RText(' | 重连nonebot插件', color=RColor.gray))}
"""


def register_commands(server: PluginServerInterface):
    server.register_command(
        admin_literal(CMD).
        then(
            Text('help').runs(lambda src: src.reply(HELP))
        )
    )
    server.register_command(
        admin_literal(CMD).
        then(
            Text('reload').runs(reload_config)
        )
    )
    server.register_command(
        admin_literal(CMD).
        then(
            Text('reconnect').runs(reconnect_ws)
        )
    )
    server.register_command(
        console_literal(CMD).
        then(
            Text('exec_json').then(
                GreedyText('json').runs(exec_json)
            )
        )
    )


async def reload_config(src: CommandSource):
    old_cfg = shared.config
    try:
        shared.config = shared.plg_server_inst.load_config_simple(target_class=Config, failure_policy='raise')
    except Exception as e:
        src.reply(RText(f'配置文件重载失败: {repr(e)}', color=RColor.red))
    else:
        src.reply(RText('已重载配置文件', color=RColor.green))
    if old_cfg.ws_server != shared.config.ws_server or old_cfg.token != shared.config.token or old_cfg.name != shared.config.name: # type: ignore
        src.reply(RText('由于配置文件更改, 自动重连ws', color=RColor.yellow))
        await reconnect_ws(src)


async def reconnect_ws(src: CommandSource):
    if shared.ws_connection:
        await shared.ws_connection.close(reason='插件卸载')
        src.reply(RText('已断开当前ws连接', color=RColor.yellow))
    else:
        src.reply(RText('当前没有ws连接', color=RColor.yellow))


def exec_json(src: CommandSource, ctx: dict):
    if (result := _exec_json(jsonlib.loads(ctx['json']))) is not None:
        src.reply(result)
