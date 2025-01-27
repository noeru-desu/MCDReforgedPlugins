
import asyncio
from typing import Any, Sequence
import websockets
import json as jsonlib

from mcdreforged.api.rtext import RText, RColor

from arucraftr import shared
from arucraftr.utils import tell_admin
from arucraftr.websocket.event import ArcEvent
from arucraftr.websocket.types import WebSocketMessage, RequestTypes


async def ws_loop():
    while True:
        try:
            shared.ws_connection = await websockets.connect(
                shared.config.ws_server,
                additional_headers=websockets.Headers(token=shared.config.token, name=shared.config.name)
            )
        except websockets.exceptions.ConnectionClosedError as e:
            if e.code == 1008:
                tell_admin(RText(f'ws设置不正确: {e.reason or 'token错误'}', color=RColor.red))
                return
        except websockets.exceptions.InvalidURI as e:
            tell_admin(RText(f'ws地址不正确: {e.uri}', color=RColor.red))
            return
        except asyncio.CancelledError as e:
            raise e from e
        except Exception:
            pass
        else:
            tell_admin(RText('ws已连接', color=RColor.green))
            await recv_msg(shared.ws_connection)
            continue
        shared.plg_server_inst.logger.info('连接失败, 重试')
        await asyncio.sleep(3)


async def recv_msg(websocket: websockets.ClientConnection):
    while True:
        try:
            try:
                message = WebSocketMessage(**jsonlib.loads(await websocket.recv(True)))
            except jsonlib.JSONDecodeError as e:
                tell_admin(RText(f'解析来自ws的消息时出现问题: {repr(e)}', color=RColor.red))
                continue
            match message.msg_type:
                case 'command':
                    exec_command(message.content) # type: ignore
                case 'event':
                    if (event := ArcEvent.get(message.content['name'])) is not None: # type: ignore
                        event.dispatch(message.content['kwargs']) # type: ignore
                    else:
                        tell_admin(RText(f'未知事件: {message.content['name']}', color=RColor.yellow)) # type: ignore
                case 'request':
                    await exec_feedback(message.content) # type: ignore
                case 'json':
                    exec_json(message.content)
        except asyncio.CancelledError as e:
            raise e from e
        except websockets.ConnectionClosed:
            tell_admin(RText('ws连接中断, 正在尝试重连', color=RColor.red))
            return
        except Exception as e:
            tell_admin(RText(f'处理ws消息时出现意外错误: {repr(e)}', color=RColor.red))


def exec_json(json: Any):
    pass


def exec_command(command: str | Sequence[str]):
    if isinstance(command, str):
        shared.plg_server_inst.execute(command)
    else:
        for i in command:
            shared.plg_server_inst.execute(i)


async def exec_feedback(request_name: str):
    if (feedback := RequestTypes.get(request_name)) is None:
        tell_admin(RText(f'未知请求目标: {request_name}', color=RColor.yellow))
        return
    await feedback()
