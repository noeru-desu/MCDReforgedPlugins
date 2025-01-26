
import json as jsonlib

from mcdreforged.api.types import PluginServerInterface, CommandSource
from mcdreforged.api.rtext import RText, RColor, RTextList
from mcdreforged.api.command import GreedyText, Literal, Text
from mcdreforged.command.builder.tools import Requirements

from . import shared
from .event import ArcEvent
from .websocket import exec_json as _exec_json

CMD = '!!acr'

def admin_literal(literal: str):
    return Literal(literal).requires(Requirements.has_permission(3), lambda src: RText('权限不足', RColor.red))

def console_literal(literal: str):
    return Literal(literal).requires(Requirements.is_console(), lambda src: RText('仅允许控制台执行json命令', RColor.red))

hr = RText('-----', color=RColor.gray)
cmd = RText(CMD)

HELP = f"""{RTextList(hr, RText('aruCraftR', color=RColor.dark_aqua), RText('插件帮助信息', color=RColor.gray), hr)}
{RTextList(cmd, ' ', RText('reload', color=RColor.gold), RText(' | 重载配置文件', color=RColor.gray))}
{RTextList(cmd, ' ', RText('reconnect', color=RColor.gold), RText(' | 重连nonebot插件', color=RColor.gray))}
"""


def register_commands(server: PluginServerInterface):
    server.register_command(
        admin_literal(CMD).runs(lambda src: src.reply(HELP)).
        then(Literal('help').runs(lambda src: src.reply(HELP))).
        then(Literal('reload').runs(reload_plg)).
        then(Literal('reconnect').runs(reconnect_ws)).
        then(
            console_literal('exec').
            then(
                Literal('json').then(
                    GreedyText('json').runs(exec_json)
                )
            ).
            then(
                Literal('event').then(
                    Text('event_name').then(GreedyText('kwargs').runs(exec_event))
                )
            )
        )
    )


def reload_plg(src: CommandSource):
    src.reply(RText('正在重载插件', color=RColor.yellow))
    if shared.plg_server_inst.reload_plugin(shared.plg_server_inst.get_self_metadata().id):
        src.reply(RText('重载成功', color=RColor.green))


async def reconnect_ws(src: CommandSource):
    if shared.ws_connection is not None:
        await shared.ws_connection.close(reason='插件卸载')
        src.reply(RText('已断开当前ws连接', color=RColor.yellow))
    else:
        src.reply(RText('当前没有ws连接', color=RColor.yellow))


def exec_json(src: CommandSource, ctx: dict):
    try:
        json = jsonlib.loads(ctx['json'])
    except jsonlib.JSONDecodeError as e:
        src.reply(f'解析json时出现错误: {repr(e)}')
    else:
        if (result := _exec_json(json)) is not None:
            src.reply(result)


def exec_event(src: CommandSource, ctx: dict):
    if (event := ArcEvent.get(ctx['event_name'])) is not None and ctx['kwargs']:
        try:
            kwargs = jsonlib.loads(ctx['kwargs'])
        except jsonlib.JSONDecodeError as e:
            src.reply(f'解析事件参数时出现错误: {repr(e)}')
        else:
            src.reply('暂不支持事件消息类型')
            # dispatch_event(event, kwargs)
