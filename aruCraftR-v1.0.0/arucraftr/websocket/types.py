
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Callable, Optional
import json as jsonlib

from arucraftr.websocket.feedback import feedback_player_list


@dataclass
class WebSocketMessage:
    msg_type: str
    content: str | list | dict

    @cached_property
    def json(self) -> str:
        return jsonlib.dumps({'msg_type': self.msg_type, 'content': self.content}, separators=(',', ':'), ensure_ascii=False)


class RequestTypes:
    player_list = feedback_player_list

    @classmethod
    def get(cls, name: str) -> Optional[Callable]:
        try:
            return getattr(cls, name)
        except AttributeError:
            return None
