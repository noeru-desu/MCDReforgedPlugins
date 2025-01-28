

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from asyncio import Future
    from websockets import ClientConnection
    from mcdreforged.api.types import PluginServerInterface, ServerInterface
    from arucraftr.config import Config
    from arucraftr.mcdr.info_filter import CustomInfoFilter


plg_server_inst: 'PluginServerInterface'
std_server_inst: 'ServerInterface'
config: 'Config'
ws_future: 'Future'
info_filter_opti_future: 'Future'
info_filter: 'CustomInfoFilter'
ws_connection: 'ClientConnection' = None # type: ignore
