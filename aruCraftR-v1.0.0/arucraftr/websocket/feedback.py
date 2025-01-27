
import asyncio

from arucraftr import shared


async def feedback_player_list():
    if shared.plg_server_inst.is_server_startup():
        shared.plg_server_inst.execute('list')
        return
    shared.plg_server_inst.logger.info('正在等待服务器启动')
    while True:
        await asyncio.sleep(3)
        if shared.plg_server_inst.is_server_startup():
            shared.plg_server_inst.execute('list')
            return
