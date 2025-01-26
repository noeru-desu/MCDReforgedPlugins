
import asyncio
from enum import Enum
from typing import Any, NamedTuple, Optional, Sequence
import websockets
import json as jsonlib

from mcdreforged.api.rtext import RText, RColor

from . import shared
# from .event import dispatch_event
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


class WebSocketMessage(NamedTuple):
    msg_type: str
    content: str | list | dict

    def json(self) -> str:
        return jsonlib.dumps({'msg_type': self.msg_type, 'content': self.content}, separators=(',', ':'), ensure_ascii=False)


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
                    tell_admin(RText('暂不支持事件消息类型', color=RColor.yellow))
                    # dispatch_event(message.content['name'], message.content['kwargs']) # type: ignore
                case 'request':
                    await exec_request(message.content) # type: ignore
                case 'json':
                    exec_json(message.content)
        except asyncio.CancelledError as e:
            raise e from e
        except websockets.ConnectionClosed:
            tell_admin(RText('ws连接中断, 正在尝试重连', color=RColor.red))
            return
        except Exception as e:
            tell_admin(RText(f'处理ws消息时出现意外错误: {repr(e)}', color=RColor.red))


async def send_msg(message: WebSocketMessage):
    if shared.ws_connection is not None and shared.ws_connection.state == websockets.State.OPEN:
        await shared.ws_connection.send(message.json(), True)


def exec_json(json: Any):
    pass


def exec_command(command: str | Sequence[str]):
    if isinstance(command, str):
        shared.plg_server_inst.execute(command)
    else:
        for i in command:
            shared.plg_server_inst.execute(i)


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


class RequestType(Enum):
    player_list=feedback_player_list

    @classmethod
    def get(cls, name: str) -> Optional['RequestType']:
        return cls.__members__.get(name)

    async def feedback(self):
        await self.value()


async def exec_request(request_name: str):
    if (request := RequestType.get(request_name)) is None:
        tell_admin(RText(f'未知请求目标: {request_name}', color=RColor.yellow))
        return
    await request.feedback()
