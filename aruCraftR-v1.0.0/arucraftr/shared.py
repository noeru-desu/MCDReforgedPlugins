

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from asyncio import Future
    from websockets import ClientConnection
    from mcdreforged.api.types import PluginServerInterface, ServerInterface
    from .config import Config


plg_server_inst: 'PluginServerInterface'
std_server_inst: 'ServerInterface'
config: 'Config'
ws_future: 'Future'
ws_connection: 'ClientConnection'
