
import asyncio
from traceback import print_exc
from typing import Any, NamedTuple, Sequence
import websockets
import json as jsonlib

from mcdreforged.api.rtext import RText, RColor

from . import shared
from .utils import tell_admin


async def ws_loop():
    while True:
        try:
            shared.ws_connection = await websockets.connect(
                shared.config.ws_server,
                additional_headers=websockets.Headers(token=shared.config.token, name=shared.config.name)
            )
        except websockets.exceptions.ConnectionClosedError as e:
            if e.code == 1008:
                shared.plg_server_inst.logger.warning(f'[aruCraftR] ws设置不正确: {e.reason or 'token错误'}')
        except websockets.exceptions.InvalidURI as e:
            shared.plg_server_inst.logger.error(f'[aruCraftR] ws地址不正确: {e.uri}')
        except asyncio.CancelledError as e:
            raise e from e
        except Exception:
            print_exc(limit=3)
        else:
            tell_admin(RText('ws已连接', color=RColor.green))
            await recv_msg(shared.ws_connection)
            continue
        shared.plg_server_inst.logger.info('连接失败, 重试')
        await asyncio.sleep(3)


class WebSocketMessage(NamedTuple):
    msg_type: str
    content: str | list | dict


async def recv_msg(websocket: websockets.ClientConnection):
    try:
        while True:
            try:
                message = WebSocketMessage(**jsonlib.loads(await websocket.recv()))
            except jsonlib.JSONDecodeError as e:
                shared.plg_server_inst.logger.warning(f'[aruCraftR] 加载来自ws的json时出现问题: {repr(e)}')
            match message.msg_type:
                case 'command':
                    exec_command(message.content) # type: ignore
                case 'json':
                    exec_json(message.content)
    except websockets.ConnectionClosed:
        tell_admin(RText('ws连接中断, 正在尝试重连', color=RColor.red))


def exec_json(json: Any):
    pass


def exec_command(command: str | Sequence[str]):
    if isinstance(command, str):
        shared.plg_server_inst.execute(command)
    else:
        for i in command:
            shared.plg_server_inst.execute(i)
