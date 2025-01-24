"""
Author       : noeru_desu
Date         : 2022-06-14 21:16:31
LastEditors  : noeru_desu
LastEditTime : 2022-07-10 08:42:07
Description  : 
"""
'''
Author       : noeru_desu
Date         : 2021-12-03 21:04:17
LastEditors  : noeru_desu
LastEditTime : 2021-12-04 06:50:52
Description  : 
'''
from threading import Thread, Event
from time import time, strftime, localtime

from mcdreforged.api.all import RTextList

from . import stored


class DifferentialAutoBackupTimer(Thread):
    def __init__(self):
        super().__init__(name=self.__class__.__name__, daemon=True)
        self.time_since_backup = time()
        self.stop_event = Event()
        self.is_enabled = stored.config.enabled
        self.player_joined = False
        self.schedule_skipped = False

    @staticmethod
    def __get_interval() -> float:
        return stored.config.interval

    @classmethod
    def get_backup_interval(cls):
        return cls.__get_interval() * 60

    def broadcast(self, message):
        rtext = RTextList('[DAB] ', message)
        if stored.server.is_server_startup():
            stored.server.broadcast(rtext)
        else:
            stored.server.logger.info(rtext)

    def set_enabled(self, value: bool):
        self.is_enabled = value
        self.reset_timer()

    def reset_timer(self):
        self.time_since_backup = time()

    def get_next_backup_message(self):
        return f'下次自动备份时间: §3{strftime("%Y/%m/%d %H:%M:%S", localtime(self.time_since_backup + self.get_backup_interval()))}§r'

    def broadcast_next_backup_time(self):
        self.broadcast(self.get_next_backup_message())

    def on_backup_created(self):
        self.reset_timer()
        self.broadcast_next_backup_time()

    def run(self):
        saving_time = 0
        while True:  # loop until stop
            while True:  # loop for backup interval
                if self.stop_event.wait(1):
                    return
                if not stored.core_inst.creating_backup_event.is_set():
                    saving_time += 1
                    if saving_time > stored.config.saving_timeout:
                        force_restart_server()
                        stored.core_inst.stop_backup = True
                        stored.core_inst.game_saved = True
                        saving_time = 0
                        self.reset_timer()
                    continue
                if time() - self.time_since_backup > self.get_backup_interval():
                    break
            if self.is_enabled and stored.server.is_server_startup():
                if self.player_joined:
                    if not stored.online_player_api.have_player():
                        self.player_joined = False
                    self.broadcast(f'每§6{self.__get_interval()}§r分钟一次的定时备份触发')
                    saving_time = 0
                    stored.core_inst.stop_backup = False
                    stored.core_inst.make_back_up(stored.server.get_plugin_command_source(), wait=True)    # 非堵塞
                else:
                    self.reset_timer()
                    stored.server.logger.info(f'[DAB] 自上次备份后没有玩家上线, 跳过此次备份, {self.get_next_backup_message()}')
                    self.schedule_skipped = True

    def stop(self):
        self.stop_event.set()


def force_restart_server():
    stored.server.kill()
    # stored.server.wait_for_start()
    # stored.server.start()
