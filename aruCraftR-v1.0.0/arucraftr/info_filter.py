
from typing import Callable

from mcdreforged.api.types import InfoFilter, Info

from .config import InfoFilterConfig, InfoFilterMethod
from . import shared


class CustomInfoFilter(InfoFilter):
    filter_cache: list[Callable[[str], bool]]
    def filter_server_info(self, info: Info) -> bool:
        if info.is_player or (content := info.raw_content) is None:
            return True
        return not any(i(content) for i in self.filter_cache) # type: ignore

    @classmethod
    def rebuild_filter_cache(cls, filters: list[InfoFilterConfig]):
        filter_cache = []
        for i in filters:
            match i.method:
                case InfoFilterMethod.keyword:
                    filter_cache.append(_keyword_filter(i.target))
                case InfoFilterMethod.startswith:
                    filter_cache.append(_startswith_filter(i.target))
                case InfoFilterMethod.endswith:
                    filter_cache.append(_endswith_filter(i.target))
        cls.filter_cache = filter_cache
        shared.plg_server_inst.logger.info(f'已加载{len(filter_cache)}条输出过滤规则')


def _keyword_filter(target):
    return lambda x: target in x


def _startswith_filter(target):
    return lambda x: x.startswith(target)


def _endswith_filter(target):
    return lambda x: x.endswith(target)
