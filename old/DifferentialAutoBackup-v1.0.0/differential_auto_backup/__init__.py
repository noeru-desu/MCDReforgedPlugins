"""
Author       : noeru_desu
Date         : 2022-06-14 21:16:31
LastEditors  : noeru_desu
LastEditTime : 2022-07-08 08:32:43
Description  : 
"""
from math import inf
from time import sleep
from typing import TYPE_CHECKING

from . import stored
from .core import DifferentialBackupper
from .clock import DifferentialAutoBackupTimer

from mcdreforged.api.all import Serializable, Literal, RequirementNotMet, Integer, RTextList, RText, RAction, UnknownArgument, RTextBase, new_thread

if TYPE_CHECKING:
    from mcdreforged.api.types import PluginServerInterface, CommandSource
    import differential_auto_backup


def print_message(source: 'CommandSource', msg, tell=True, prefix='[DAB] ', force_tell=False):
    msg = RTextList(prefix, msg)
    if force_tell or (source.is_player and not tell):
        stored.server.say(msg)
        if source.is_console:
            source.reply(msg)
    else:
        source.reply(msg)


class Config(Serializable):
    enabled: bool = True
    turn_off_auto_save: bool = True
    ignored_files: list[str] = [
        'session.lock'
    ]
    backup_path: str = './differential_backup'
    overwrite_backup_folder: str = 'overwrite'
    server_path: str = './server'
    world_name: str = 'world'
    interval: float = 30.0  # minutes
    saving_timeout: int = 60     # second
    minimum_permission_level: dict[str, int] = {
        'make': 1,
        'back': 2,
        'merge': 2,
        'del': 2,
        'confirm': 1,
        'abort': 1,
        'reload': 2,
        'list': 0,
        'debug': 4
    }
    auto_merge_backup: bool = False
    auto_merge_rules: dict[str, int] = {
        'normal': 5
    }
    slots: int = 5


command_prefix = '!!dab'


def print_help_message(source: 'CommandSource'):
    if source.is_player:
        source.reply('')
    print_message(
        source,
        f''' ------ {stored.metadata.name} v{stored.metadata.version} ------
一个支持多槽位的快速§a差异备份§r&§c回档§r插件
§d[格式说明]§r
§7{stored.cmd_prefix}§r 显示帮助信息
§7{stored.cmd_prefix} make§r 创建一个储存至位次§61§r的§a备份§r
§7{stored.cmd_prefix} back §6[<slot>]§r §c回档§r为位次§6<slot>§r的备份
§7{stored.cmd_prefix} merge §6<starting_slot>§r §6[<ending_slot>]§r §c合并§r位次§6<starting_slot>~<ending_slot>§r的备份§7(包括端点)§r
§7{stored.cmd_prefix} del §6<starting_slot>§r §c删除§r位次§6<starting_slot>~§4最后一个位次§r的备份§7(包括端点)§r
§7{stored.cmd_prefix} confirm§r 再次确认是否进行§c回档§r
§7{stored.cmd_prefix} abort§r 在任何时候键入此指令可中断§c回档§r
§7{stored.cmd_prefix} list§r 显示全部位次的备份信息
§7{stored.cmd_prefix} reload§r 重新加载配置文件与槽位信息
当 §6<slot>§r 未被指定时默认选择位次§61§r
当 §6<ending_slot>§r 未被指定时默认选择最后一个位次''',
        prefix=''
    )
    stored.core_inst.print_slots_info_rtext(source)
    print_message(
        source,
        f'§d[快捷操作]§r',
        prefix=''
    )
    print_message(
        source,
        RTextList(
            RText('>>> §a点我输入进行备份的指令§r <<<').c(RAction.suggest_command, f'{stored.cmd_prefix} make'),
            '\n',
            RText('>>> §c点我输入回档至最近的指令§r <<<').c(RAction.suggest_command, f'{stored.cmd_prefix} back')
        ),
        prefix=''
    )


def load_config(source=None):
    stored.config = stored.server.load_config_simple('./config/differential_backup.json', target_class=Config, in_data_folder=False, source_to_reply=source)
    if hasattr(stored, 'core_inst'):
        stored.core_inst.slots.build_slots()


def on_info(server, info):
    if not info.is_user and info.content in ['Saved the game', 'Saved the world']:
        stored.core_inst.saved_game()


def get_literal_node(literal):
        lvl = stored.config.minimum_permission_level.get(literal, 0)
        return Literal(literal).requires(lambda src: src.has_permission(lvl)).on_error(RequirementNotMet, lambda src: src.reply('§c权限不足'), handled=True)


def get_slot_node(name='slot'):
        return Integer(name).requires(lambda src, ctx: (1 <= ctx[name] and stored.core_inst.slots.get_slot_data(ctx[name])[1]['time_stamp'] != -inf) or (stored.core_inst.slots.overwrite_backup_info is not None and ctx[name] == 0)).on_error(RequirementNotMet, lambda src: src.reply('位次输入错误'), handled=True)


def command_run(message, text, command: str) -> RTextBase:
    fancy_text = message.copy() if isinstance(message, RTextBase) else RText(message)
    return fancy_text.set_hover_text(text).set_click_event(RAction.run_command, command)


def print_unknown_argument_message(source: 'CommandSource', error: UnknownArgument):
    print_message(source, command_run(
        f'参数错误! 请输入§7{stored.cmd_prefix}§r以获取插件信息'
        '点击查看帮助',
        stored.cmd_prefix
    ))


def print_not_implemented_error(source: 'CommandSource'):
    print_message(source, '此功能正在开发')


def on_load(server: 'PluginServerInterface', old: 'differential_auto_backup'):
    stored.server = server
    stored.online_player_api = server.get_plugin_instance('online_player_api')
    server.register_help_message(command_prefix, '差异备份')
    load_config()

    stored.metadata = server.get_self_metadata()
    stored.core_inst = DifferentialBackupper()
    stored.clock_inst = DifferentialAutoBackupTimer()
    stored.clock_inst.start()
    if stored.online_player_api.have_player():
        stored.clock_inst.player_joined = True

    server.register_command(
        Literal(stored.cmd_prefix).
        runs(print_help_message).
        on_error(UnknownArgument, print_unknown_argument_message, handled=True).
        then(
            get_literal_node('make').
            runs(stored.core_inst.make_back_up)
        ).
        then(
            get_literal_node('back').
            runs(lambda src: stored.core_inst.restore_backup(src, 1)).
            then(get_slot_node().runs(lambda src, ctx: stored.core_inst.restore_backup(src, ctx['slot'])))
        ).
        then(
            get_literal_node('merge').runs(print_not_implemented_error)
            # then(get_slot_node('starting_slot').runs(lambda src, ctx: stored.core_inst.del_backup(src, ctx['starting_slot']))).
            # then(get_slot_node('ending_slot').runs(lambda src, ctx: stored.core_inst.del_backup(src, ctx['starting_slot'], ctx['ending_slot'])))
        ).
        then(
            get_literal_node('del').
            then(get_slot_node('starting_slot').runs(lambda src, ctx: stored.core_inst.del_backup(src, ctx['starting_slot'])))
        ).then(
            get_literal_node('debug').
            then(Literal('list').runs(stored.core_inst.debug_print_slots_info_rtext))
        ).
        then(get_literal_node('confirm').runs(stored.core_inst.confirm_restore)).
        then(get_literal_node('abort').runs(stored.core_inst.trigger_abort)).
        then(get_literal_node('list').runs(stored.core_inst.print_slots_info_rtext)).
        then(get_literal_node('reload').runs(load_config))
    )


def on_unload(server):
    stored.core_inst.unload()
    server.logger.info('插件卸载，停止时钟')
    stored.clock_inst.stop()


def on_remove(server):
    server.logger.info('插件被移除，停止时钟')
    stored.clock_inst.stop()


@new_thread('DAB-Player-Join-Backup')
def on_player_joined(server: 'PluginServerInterface', player, info):
    stored.clock_inst.player_joined = True
    if stored.clock_inst.schedule_skipped:
        stored.clock_inst.schedule_skipped = False
        sleep(3)
        stored.clock_inst.broadcast(f'§6{stored.config.interval}§r分钟内无玩家加入后的玩家进入备份触发')
        stored.core_inst.make_back_up(server.get_plugin_command_source())


def on_player_left(server: 'PluginServerInterface', player):
    if not stored.online_player_api.have_player():
        stored.clock_inst.player_joined = False
