
from enum import Enum
from mcdreforged.api.utils import Serializable


class InfoFilterMethod(Enum):
    keyword=0
    startswith=1
    endswith=2


class InfoFilterConfig(Serializable):
    method: InfoFilterMethod
    target: str


class Config(Serializable):
    ws_server: str = 'ws://127.0.0.1:8080'
    token: str = 'xxx'
    name: str = '请更改名称'
    info_filter: list[InfoFilterConfig] = [InfoFilterConfig(method=InfoFilterMethod.startswith, target='example')]
    debug: bool = False
