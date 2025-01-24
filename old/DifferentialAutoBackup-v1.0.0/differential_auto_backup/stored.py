"""
Author       : noeru_desu
Date         : 2022-06-15 06:32:46
LastEditors  : noeru_desu
LastEditTime : 2022-07-21 17:45:57
Description  : 
"""
from mcdreforged.api.types import PluginServerInterface, Metadata
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import Config
    from .core import DifferentialBackupper
    from .clock import DifferentialAutoBackupTimer

online_player_api: Any
config: 'Config'
metadata: Metadata
server: PluginServerInterface
core_inst: 'DifferentialBackupper'
clock_inst: 'DifferentialAutoBackupTimer'
cmd_prefix = '!!dab'