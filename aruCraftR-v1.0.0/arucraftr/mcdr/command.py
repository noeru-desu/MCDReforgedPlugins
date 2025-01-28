
import json as jsonlib

import re
from traceback import format_exc
from mcdreforged.api.types import PluginServerInterface, CommandSource
from mcdreforged.api.rtext import RText, RColor, RTextList
from mcdreforged.api.command import GreedyText, Literal, Text
from mcdreforged.command.builder.tools import Requirements

from arucraftr import shared
from arucraftr.websocket.event import ArcEvent
from arucraftr.websocket.handler import exec_json as _exec_json

CMD = '!!acr'

def admin_literal(literal: str):
    return Literal(literal).requires(Requirements.has_permission(3), lambda src: RText('权限不足', RColor.red))

def console_literal(literal: str):
    return Literal(literal).requires(Requirements.is_console(), lambda src: RText('仅允许控制台执行json命令', RColor.red))

hr = RText('-----', color=RColor.gray)
cmd = RText(CMD)

HELP = f"""{RTextList(hr, RText('aruCraftR', color=RColor.dark_aqua), RText(' 插件帮助信息', color=RColor.gray), hr)}
{RTextList(cmd, ' ', RText('reload', color=RColor.gold), RText(' | 重载配置文件', color=RColor.gray))}
{RTextList(cmd, ' ', RText('reconnect', color=RColor.gold), RText(' | 重连nonebot插件', color=RColor.gray))}
{RTextList(cmd, ' ', RText('filter count', color=RColor.gold), RText(' | 查询过滤器计数', color=RColor.gray))}
{RTextList(cmd, ' ', RText('debug', color=RColor.gold), RText(' | 调试相关', color=RColor.gray))}
"""

DEBUG_HELP = f"""{RTextList(hr, RText('aruCraftR', color=RColor.dark_aqua), RText(' Debug帮助信息', color=RColor.gray), hr)}
{RTextList(cmd, ' debug ', RText('event <事件名>', color=RColor.gold), RText(' | 测试事件发送', color=RColor.gray))}
"""


def register_commands(server: PluginServerInterface):
    server.register_command(
        admin_literal(CMD).runs(lambda src: src.reply(HELP)).
        then(Literal('help').runs(lambda src: src.reply(HELP))).
        then(Literal('reload').runs(reload_plg)).
        then(Literal('reconnect').runs(reconnect_ws)).
        then(
            Literal('filter').
            then(Literal('count').runs(print_filter_count))
        ).
        then(
            Literal('debug').runs(lambda src: src.reply(DEBUG_HELP)).
            then(Literal('event').then(Text('event_name').runs(debug_event)))
        ).
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


def print_filter_count(src: CommandSource):
    if shared.config.auto_optimize_info_filter:
        src.reply(f'拦截计数如下:\n{'\n'.join(f'{i.target.pattern if isinstance(i.target, re.Pattern) else i.target}: {i.count}' for i in shared.info_filter.filter_cache)}')
    else:
        src.reply('未启用计数器')


async def debug_event(src: CommandSource, ctx: dict):
    try:
        if (event := ArcEvent.get(ctx['event_name'])) is None:
            src.reply(RText(f'事件ID不存在: {ctx['event_name']}', color=RColor.red))
        await event.debug_report()
    except Exception:
        src.reply(RText(f'出现错误: {format_exc(limit=5)}', color=RColor.red))
    else:
        src.reply(RText(f'已发送事件{ctx['event_name']}', color=RColor.green))


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
            event.dispatch(kwargs)
