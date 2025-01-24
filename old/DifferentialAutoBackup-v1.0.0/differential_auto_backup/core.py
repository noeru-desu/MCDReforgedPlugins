"""
Author       : noeru_desu
Date         : 2022-07-03 14:22:12
LastEditors  : noeru_desu
LastEditTime : 2022-07-21 17:49:22
Description  : 
"""
from collections import deque
from pickle import load, dump
from math import inf
from os import makedirs, mkdir, remove, walk
from os.path import getmtime, join, exists, split, abspath, getsize, sep
from shutil import copy2, rmtree
from threading import Event
from traceback import print_exc
from typing import TYPE_CHECKING, Iterable, Literal, Optional, Union
from time import sleep, time, strftime, localtime

from . import stored

from mcdreforged.api.all import RTextList, CommandSource, new_thread, RText, RColor, RAction, RTextBase

if TYPE_CHECKING:
    from os import PathLike

    TimeSet = set[tuple[PathLike[str], float]]
    ChangedTimeSet = set[tuple[PathLike[str], float]]
    SlotInfo = dict[Literal['time', 'time_stamp', 'file_timestamps', 'included_files', 'backup_size'], Union[str, float, list, int, TimeSet]]
    SlotData = tuple(PathLike[str], SlotInfo)


def print_message(source: 'CommandSource', msg, tell=True, prefix='[DAB] ', force_tell=False):
    msg = RTextList(prefix, msg)
    if force_tell or (source.is_player and not tell):
        stored.server.say(msg)
        if source.is_console:
            source.reply(msg)
    else:
        source.reply(msg)


def command_run(message, text, command: str) -> RTextBase:
    fancy_text = message.copy() if isinstance(message, RTextBase) else RText(message)
    return fancy_text.set_hover_text(text).set_click_event(RAction.run_command, command)


empty_info = {
    'time': 'Unknown',
    'time_stamp': -inf,
    'included_files': set(),
    'backup_size': 0,
    'file_timestamps': set()
}


def pi(*msg):
    stored.server.logger.warning(msg)


class Slots(object):
    def __init__(self, start: int, end: int, slot_index: int):
        """start与end均包含"""
        self.starting_slot = start
        self.ending_slot = end
        self.slot_index = slot_index
        self.slots = end - start    # 等同于len(self.slots_deque) - 1, 即self.slots_deque的最大下标
        self.slots_deque: deque[tuple['PathLike[str]', 'SlotInfo']] = None
        self.used_slots_count: int = -1
        self.load_slots_info()

    def get_used_slots_count(self):
        if self.used_slots_count == -1:
            self.used_slots_count = sum(si['time_stamp'] != -inf for p, si in self.slots_deque)
        return self.used_slots_count

    def get_slot_index(self, displayed_slot_id: int) -> int:
        """返回值<0代表指定的显示ID不属于此Slots"""
        index = self.ending_slot - displayed_slot_id    # 该值为负数时其绝对值-1为后一分区的下标偏移量
        if index > self.slots:
            return -1   # 此时index-self.slots-1为前一分区的下标负偏移量. 尚未使用, 故直接返回-1作为标识
        return index

    def get_slot_data(self, slot_index: int) -> tuple['PathLike[str]', 'SlotInfo']:
        return self.slots_deque[slot_index]

    def load_slots_info(self):
        slots_list = []
        for i in range(self.starting_slot, self.ending_slot + 1):
            slot_path = join(stored.config.backup_path, f'slot{i}')
            if not exists(slot_path):
                makedirs(slot_path)
                slots_list.append((slot_path, empty_info))
                continue
            info_file = join(slot_path, 'info.pickle')
            if not exists(info_file):
                slots_list.append((slot_path, empty_info))
                continue
            with open(info_file, 'rb') as f:
                info: 'SlotInfo' = load(f)
                slots_list.append((slot_path, info))
        self.sort_slots_deque(slots_list)

    def sort_slots_deque(self, slots_iter: Iterable = ...):
        if slots_iter is Ellipsis:
            slots_iter = self.slots_deque
        self.slots_deque = deque(sorted(slots_iter, key=lambda v: v[1]['time_stamp']), maxlen=self.slots + 1)

    def add_slot_data(self, data: tuple['PathLike[str]', 'SlotInfo']):
        self.used_slots_count += 1
        self.slots_deque.append(data)
        if stored.config.auto_merge_backup and self.used_slots_count > self.slots and self.slot_index + 1 < len(stored.core_inst.slots.slots_list):
            stored.core_inst._merge_slots(stored.server.get_plugin_command_source(), self.starting_slot, self.ending_slot, self.slot_index + 1)
            self.used_slots_count = 0

    def get_oldest_slot(self):  # 即最左端
        return self.slots_deque[0]

    def get_latest_slot(self):  # 即最右端
        return self.slots_deque[-1]


class SlotsManager(object):
    def __init__(self):
        self.overwrite_backup_info = None
        self.slots_count_list = []
        self.slots_list: list['Slots'] = []
        self.build_slots()
        overwrite_backup_info_file = join(stored.config.backup_path, stored.config.overwrite_backup_folder, 'info.pickle')
        if exists(overwrite_backup_info_file):
            with open(overwrite_backup_info_file, 'rb') as f:
                self.overwrite_backup_info = load(f)

    @property
    def all_slot_generator(self):
        for i in self.slots_list:
            yield from reversed(i.slots_deque)

    def get_used_slots_count(self):
        return sum(i.get_used_slots_count() for i in self.slots_list)

    def get_slot_data(self, displayed_slot_id: int) -> tuple['PathLike[str]', 'SlotInfo']:
        for i in self.slots_list:
            index = i.get_slot_index(displayed_slot_id)
            if index >= 0:
                return i.slots_deque[index]
        raise ValueError('nonexistent displayed_slot_id')

    def build_slots(self):
        self.slots_list.clear()
        if stored.config.auto_merge_backup:
            starting = 1
            ending = 0
            for i, v in enumerate(stored.config.auto_merge_rules.values()):
                ending += v
                self.slots_list.append(Slots(starting, ending, i))
                starting += v

    def add_slot_data(self, data: tuple['PathLike[str]', 'SlotInfo']):
        self.slots_list[0].add_slot_data(data)

    def clear_slot_data(self, displayed_slot_id: int, del_files=False):
        for i in self.slots_list:
            index = i.get_slot_index(displayed_slot_id)
            if index >= 0:
                slot_path = i.slots_deque[index][0]
                if del_files:
                    rmtree(slot_path)
                    mkdir(slot_path)
                del i.slots_deque[index]
                i.slots_deque.appendleft((slot_path, empty_info))
                i.used_slots_count -= 1
                return

    def clear_slots_data(self, s: int, e: int, del_files=False):
        index_list: list[tuple['Slots', int, str]] = []
        for displayed_slot_id in range(s, e + 1):
            for i in self.slots_list:
                index = i.get_slot_index(displayed_slot_id)
                if index >= 0:
                    slot_path = i.slots_deque[index][0]
                    if del_files:
                        rmtree(slot_path)
                        mkdir(slot_path)
                    index_list.append((i, index, slot_path))
                    i.used_slots_count -= 1
                    break
        for d, i, slot_path in index_list:
            del d.slots_deque[i]
            d.slots_deque.appendleft((slot_path, empty_info))

    def get_oldest_slot(self):
        return self.slots_list[0].get_oldest_slot()

    def get_latest_slot(self):
        for i in self.slots_list:
            l = i.get_latest_slot()
            if l[1]['time_stamp'] != -inf:
                return l
        return self.slots_list[0].get_latest_slot()

class DifferentialBackupper(object):
    def __init__(self) -> None:
        self.slots = SlotsManager()
        self.game_saved = False
        self.unloaded = False
        self.stop_backup = False
        self.restore_slot_selected: Optional[tuple[int, tuple['PathLike[str]', 'SlotInfo']]] = None
        self.abort_restore = False
        self.restoring_backup_event = Event()
        self.creating_backup_event = Event()
        self.merging_backup_event = Event()
        self.restoring_backup_event.set()
        self.creating_backup_event.set()
        self.merging_backup_event.set()
        self.abs_server_path = abspath(stored.config.server_path)
        self.used_slots_count = self.get_used_slots_count()

    def get_used_slots_count(self):
        return self.slots.get_used_slots_count()

    def debug_print_slots_info_rtext(self, source):
        for n, i in enumerate(self.slots.slots_list):
            print_message(source, f'{n}: used={i.used_slots_count}, maxlen={i.slots + 1}, ')
            for p, v in i.slots_deque:
                slot_name = p.split(sep)[-1]
                print_message(source, f'{n}-{slot_name} {repr(v["included_files"])[:30]} {v["time"]}')

    def print_slots_info_rtext(self, source):
        print_message(source, '§d[备份位次]§r', prefix='')
        backup_size = 0
        for num, (path, slot_info) in enumerate(self.slots.all_slot_generator):
            if slot_info['time_stamp'] == -inf:
                continue
            num += 1
            backup_size += slot_info['backup_size']
            print_message(source, RTextList(
                f'[位次§6{num}§r]',
                ' ',
                RText('[▷] ', color=RColor.green).h(f'点击回档至位次§6{num}§r').c(RAction.run_command, f'{stored.cmd_prefix} back {num}'),
                RText('[×] ', color=RColor.red).h(f'点击删除位次§6{num}§r').c(RAction.suggest_command, f'{stored.cmd_prefix} del {num}'),
                f'§2{format_file_size(slot_info["backup_size"])}§r '
                f'时间: {slot_info["time"]}'
            ), prefix='')
        if self.slots.overwrite_backup_info is not None:
            print_message(source, RTextList(
                '[位次§60§r]',
                ' ',
                RText('[▷] ', color=RColor.green), #.h(f'点击回档至备份§6{num}§r').c(RAction.run_command, f'{stored.cmd_prefix} back {num}'),
                RText('[×] ', color=RColor.red).h('点击删除此备份').c(RAction.suggest_command, f'{stored.cmd_prefix} del 0'),
                f'§2{format_file_size(self.slots.overwrite_backup_info["backup_size"])}§r '
                f'时间: {self.slots.overwrite_backup_info["time"]} ',
                '§6(最近一次回档时的备份)§r'
            ), prefix='')
            backup_size += self.slots.overwrite_backup_info["backup_size"]
        print_message(source, f'备份总占用空间: §a{format_file_size(backup_size)}§r', prefix='')

    def get_all_file_mod_times(self, world) -> 'TimeSet':
        world = join(self.abs_server_path, world)
        offset = len(world) + 1
        modification_time_set = set()
        for top, dirs, files in walk(world):
            relative_path = top[offset:]
            modification_time_set.update((join(relative_path, file), getmtime(join(top, file))) for file in files if file not in stored.config.ignored_files)
        return modification_time_set

    def get_all_file(self, world) -> set['PathLike[str]']:
        world = join(self.abs_server_path, world)
        offset = len(world) + 1
        files: set['PathLike[str]'] = set()
        for top, dirs, file_list in walk(world):
            relative_path = top[offset:]
            files.update(join(relative_path, file) for file in file_list if file not in stored.config.ignored_files)
        return files

    def get_changed_file_set(self, last_time_set: 'TimeSet', latest_time_set: 'TimeSet') -> 'ChangedTimeSet':
        return latest_time_set - last_time_set

    def saved_game(self):
        self.game_saved = True

    def unload(self):
        self.unloaded = True

    @new_thread('DAB-Backup')
    def make_back_up(self, source: 'CommandSource', *, wait=False):
        if wait:
            if not self.restoring_backup_event.is_set():
                print_message(source, '正在§c回档§r中, 请不要尝试备份', tell=False)
                return
            if not self.merging_backup_event.is_set():
                print_message(source, '正在§a合并§r中, 请不要尝试备份', tell=False)
                return
            if not self.creating_backup_event.is_set():
                print_message(source, '正在§a备份§r中, 请不要重复输入', tell=False)
                return
        else:
            self.restoring_backup_event.wait()
            self.creating_backup_event.wait()
            self.merging_backup_event.wait()
        self.creating_backup_event.clear()
        try:
            slot_path, slot_data = self.slots.get_oldest_slot()
            start_time = time()
            self.game_saved = False
            print_message(source, '正在进行§a自动备份§r...', tell=True)
            if stored.config.turn_off_auto_save:
                stored.server.execute('save-off')
            stored.server.execute('save-all flush')
            while True:
                sleep(0.1)
                if self.game_saved:
                    if self.stop_backup:
                        self.stop_backup = False
                        print_message(source, '内部标志位已设置, §a备份§r中断!', tell=False)
                        return
                    break
                if self.unloaded:
                    print_message(source, '插件被重载, §a备份§r中断!', tell=False)
                    return
            print_message(source, '存档已保存, 正在备份有所更改的文件', tell=True)
            all_file_mod_times = self.get_all_file_mod_times(stored.config.world_name)
            changed_file_set = self.get_changed_file_set(self.slots.get_latest_slot()[1]['file_timestamps'], all_file_mod_times)
            backup_size = self.copy_worlds(
                stored.config.server_path, slot_path,
                changed_file_set
            )
            info = {
                    'time': strftime("%Y/%m/%d %H:%M:%S", localtime()),
                    'time_stamp': time(),
                    'backup_size': backup_size,
                    'included_files': {i for i, _ in changed_file_set},
                    'file_timestamps': all_file_mod_times
                }
            with open(join(slot_path, 'info.pickle'), 'wb') as f:
                dump(info, f)
            end_time = time()
            print_message(source, f'备份完成, 用时{round(end_time - start_time, 2)}秒, 备份大小: {format_file_size(backup_size)}', force_tell=True)
            self.slots.add_slot_data((slot_path, info))
            stored.clock_inst.on_backup_created()
        except Exception as e:
            print_exc()
            print_message(source, f'§a备份§r失败, 错误代码{e}', force_tell=True)
        finally:
            if self.used_slots_count < stored.config.slots:
                self.used_slots_count += 1
            self.creating_backup_event.set()
            if stored.config.turn_off_auto_save:
                stored.server.execute('save-on')

    def copy_worlds(self, src_path, dst_path, file_list: 'TimeSet') -> int:
        rmtree(dst_path)
        makedirs(dst_path)
        total_file_size = 0
        _src_path = join(src_path, stored.config.world_name)
        _dst_path = join(dst_path, stored.config.world_name)
        stored.server.logger.info(f'copying {_src_path} -> {_dst_path}')
        for file, time in file_list:
            src_file = join(_src_path, file)
            if split(src_file)[1] in stored.config.ignored_files:
                continue
            dst_file = join(_dst_path, file)
            makedirs(split(dst_file)[0], exist_ok=True)
            total_file_size += getsize(src_file)
            copy2(src_file, dst_file)
        return total_file_size

    def copy_files(self, src_file_list, dst_file_list) -> int:
        total_file_size = 0
        for src, dst in zip(src_file_list, dst_file_list, strict=True):
            if exists(dst):
                remove(dst)
            makedirs(split(dst)[0], exist_ok=True)
            total_file_size += getsize(src)
            copy2(src, dst)
        return total_file_size

    @new_thread('DAB-Backup')
    def del_backup(self, source: 'CommandSource', slot: int):
        if not (self.creating_backup_event.is_set() and self.restoring_backup_event.is_set()):
            print_message(source, '正在执行其他操作, 请不要尝试删除备份', tell=False)
            return
        try:
            if slot == 0:
                rmtree(join(stored.config.backup_path, stored.config.overwrite_backup_folder))
                self.slots.overwrite_backup_info = None
            else:
                print_message(source, '§c已关闭删除位次功能', tell=False)
                return
                slot_index = self.slots.get_slot_index(slot)
                slot_path, slot_info = self.slots.slots_deque[self.slots.get_slot_index(slot)]
                rmtree(slot_path)
                mkdir(slot_path)
                del self.slots.slots_deque[slot_index]
                self.slots.slots_deque.appendleft((slot_path, empty_info))
                if self.used_slot_number > 0:
                    self.used_slot_number -= 1
        except Exception as e:
            print_message(source, f'§4删除位次§6{slot}§r失败§r, 错误代码: {e}', tell=False)
        else:
            print_message(source, f'§a删除位次§6{slot}§r完成§r', tell=False)

    @new_thread('DAB-Restore')
    def restore_backup(self, source: CommandSource, slot: int):
        if not self.creating_backup_event.is_set():
            print_message(source, '正在§c备份§r中, 请不要尝试回档', tell=False)
            return
        if not self.merging_backup_event.is_set():
            print_message(source, '正在§a合并§r中, 请不要尝试回档', tell=False)
            return
        if not self.restoring_backup_event.is_set():
            print_message(source, '正在§a回档§r中, 请不要重复输入', tell=False)
            return
        if self.restore_slot_selected is not None:
            print_message(source, f'已有一个§a回档§r请求, 请使用§7{stored.cmd_prefix} confirm§r确认回档', tell=False)
            return
        self.restore_slot_selected = (slot, self.slots.get_slot_data(slot))
        self.abort_restore = False
        slot_info = self.restore_slot_selected[1][1]
        print_message(source, f'准备将存档恢复至位次§6{slot}§r, 存档时间: {slot_info["time"]}', force_tell=True)
        print_message(
            source,
            RTextList(
                command_run(f'使用§7{stored.cmd_prefix} confirm§r 确认§c回档§r', '点击确认', f'{stored.cmd_prefix} confirm'),
                ', ',
                command_run(f'§7{stored.cmd_prefix} abort§r 取消', '点击取消', f'{stored.cmd_prefix} abort')
            ), force_tell=True
        )

    def trigger_abort(self, source):
        self.abort_restore = True
        self.slot_selected = None
        print_message(source, '已终止操作', tell=False)

    @new_thread('DAB-Restore')
    def confirm_restore(self, source: CommandSource):
        if self.restore_slot_selected is None:
            print_message(source, '没有回档请求需要确认', tell=False)
        else:
            if not self.creating_backup_event.is_set():
                print_message(source, '正在§c备份§r中, 请不要尝试回档', tell=False)
                return
            if not self.merging_backup_event.is_set():
                print_message(source, '正在§a合并§r中, 请不要尝试回档', tell=False)
                return
            if not self.restoring_backup_event.is_set():
                print_message(source, '正在§a回档§r中, 请不要重复输入', tell=False)
                return
            self.restoring_backup_event.clear()
            self._do_restore_backup(source, self.restore_slot_selected[0])

    def _do_restore_backup(self, source: CommandSource, displayed_slot_id: int):
        try:
            print_message(source, '10秒后将关闭服务器进行§c回档§r', force_tell=True)
            for countdown in range(10, 0, -1):
                print_message(source, command_run(
                    f'{countdown}秒后关闭服务器',
                    '点击终止回档',
                    f'{stored.cmd_prefix} abort'
                ), force_tell=True)
                for _ in range(10):
                    sleep(0.1)
                    if self.abort_restore:
                        print_message(source, '已中断§c回档§r', force_tell=True)
                        return

            for i in stored.online_player_api.get_player_list():
                stored.server.execute('kick')
            stored.server.stop()
            stored.server.logger.info('Wait for server to stop')
            stored.server.wait_for_start()

            stored.server.logger.info('Backup current world to avoid idiot')
            overwrite_backup_path = join(stored.config.backup_path, stored.config.overwrite_backup_folder)
            if exists(overwrite_backup_path):
                rmtree(overwrite_backup_path)
            else:
                mkdir(overwrite_backup_path)

            overwritten_files = set()
            range_iter = range(displayed_slot_id, 0, -1).__iter__()
            _slot_path, _slot_info = self.slots.get_slot_data(next(range_iter))
            non_overwriteable_files = self.get_all_file(stored.config.world_name) - {f for f, t in _slot_info['file_timestamps']}
            _included_files: set['PathLike[str]'] = _slot_info['included_files'] - non_overwriteable_files
            source_files = {join(_slot_path, stored.config.world_name, i) for i in _included_files}
            overwritten_files |= _included_files
            for i in range_iter:
                slot_path, slot_info = self.slots.get_slot_data(i)
                included_files: set['PathLike[str]'] = slot_info['included_files'] - non_overwriteable_files
                source_files.update(join(slot_path, stored.config.world_name, i) for i in (included_files - overwritten_files))
                overwritten_files |= included_files

            src_file_list = [join(stored.config.server_path, stored.config.world_name, i) for i in overwritten_files]
            backup_size = self.copy_files(
                src_file_list,
                [join(overwrite_backup_path, stored.config.world_name, i) for i in overwritten_files]
            )
            info = {
                    'time': strftime("%Y/%m/%d %H:%M:%S", localtime()),
                    'time_stamp': time(),
                    'backup_size': backup_size,
                    'included_files': overwritten_files,
                    'file_timestamps': set()
                }
            with open(join(overwrite_backup_path, 'info.pickle'), 'wb') as f:
                dump(info, f)
            self.slots.overwrite_backup_info = info

            stored.server.logger.info('Delete new files since the selected archive was backed up')
            for i in non_overwriteable_files:
                remove(join(stored.config.server_path, stored.config.world_name, i))
            stored.server.logger.info('Restore backup')
            restore_size = self.copy_files(source_files, src_file_list)

            stored.server.logger.info(f'Done, the size of all restored files is {format_file_size(restore_size)}')
            source.get_server().start()
        except Exception:
            stored.server.logger.exception(f'Fail to restore backup to precedence {displayed_slot_id}, triggered by {source}')
        finally:
            self.abort_restore = False
            self.restore_slot_selected = None
            self.restoring_backup_event.set()

    @new_thread('DAB-merge')
    def merge_slots(self, source, starting: int, ending: int, target: int):
        if not self.creating_backup_event.is_set():
            print_message(source, '正在§c备份§r中, 请不要尝试合并', tell=False)
            return
        if not self.restoring_backup_event.is_set():
            print_message(source, '正在§a回档§r中, 请不要尝试合并', tell=False)
            return
        if not self.merging_backup_event.is_set():
            print_message(source, '正在§a合并§r中, 请不要重复输入', tell=False)
            return
        self._merge_slots(starting, ending, target, wait=False)

    def _merge_slots(self, source, starting: int, ending: int, target_slots_index: int,* ,  wait=True):
        if wait:
            self.restoring_backup_event.wait()
        try:
            self.merging_backup_event.clear()
            start_time = time()
            print_message(source, '正在进行§a合并§r...')
            overwritten_files: set['PathLike[str]'] = set()
            source_files = set()
            starting_slot_info = None
            for n in range(starting, ending + 1):
                slot_path, slot_info = self.slots.get_slot_data(n)
                for i in (slot_info['included_files'] - overwritten_files):
                    source_files.add(join(slot_path, stored.config.world_name, i))
                overwritten_files |= slot_info['included_files']
                if starting_slot_info is None:
                    starting_slot_info = slot_info
            slot_path, slot_info = self.slots.slots_list[target_slots_index].get_oldest_slot()
            merge_size = self.copy_files(
                source_files,
                [join(slot_path, stored.config.world_name, i) for i in overwritten_files]
            )
            info = {
                    'time': starting_slot_info['time'],
                    'time_stamp': starting_slot_info['time_stamp'],
                    'backup_size': merge_size,
                    'included_files': overwritten_files,
                    'file_timestamps': starting_slot_info['file_timestamps']
                }
            with open(join(slot_path, 'info.pickle'), 'wb') as f:
                dump(info, f)
            self.slots.slots_list[target_slots_index].add_slot_data((slot_path, info))
            s_deque = self.slots.slots_list[target_slots_index - 1].slots_deque
            for i, v in enumerate(s_deque):
                slot_path = v[0]
                rmtree(slot_path)
                mkdir(slot_path)
                s_deque[i] = (slot_path, empty_info)
            self.used_slots_count -= starting - ending
            end_time = time()
            print_message(source, f'合并完成, 用时{round(end_time - start_time, 2)}秒, 合并大小: {format_file_size(merge_size)}', force_tell=True)
        except Exception as e:
            print_exc()
            print_message(source, f'§a合并§r失败, 错误代码{e}', force_tell=True)
        finally:
            self.merging_backup_event.set()


def format_file_size(size: int) -> str:
    if size < 2 ** 30:
        return f'{round(size / 2 ** 20, 2)} MB'
    else:
        return f'{round(size / 2 ** 30, 2)} GB'
