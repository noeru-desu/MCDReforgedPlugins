
from enum import Enum
from mcdreforged.api.utils import Serializable


class InfoFilterMethod(Enum):
    keyword=0
    startswith=1
    endswith=2
    re_match=3
    re_search=4


class InfoFilterConfig(Serializable):
    method: InfoFilterMethod
    target: str


class Config(Serializable):
    ws_server: str = 'ws://127.0.0.1:8080'
    token: str = 'xxx'
    name: str = '请更改名称'
    forwarding_message_prefix = '.'
    info_filter: list[InfoFilterConfig] = [InfoFilterConfig(method=InfoFilterMethod.startswith, target='example')]
    auto_optimize_info_filter: bool = False
    info_filter_optimization_interval: int = 60
    debug: bool = False
