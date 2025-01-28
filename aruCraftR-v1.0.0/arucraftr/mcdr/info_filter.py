
import asyncio
from dataclasses import dataclass
from re import compile, Pattern
from threading import Lock
from typing import Type

from mcdreforged.api.types import InfoFilter, Info

from arucraftr.config import InfoFilterConfig, InfoFilterMethod
from arucraftr import shared


class CustomInfoFilter(InfoFilter):
    lock = Lock()
    filter_cache: list['FilterLike']

    def filter_server_info(self, info: Info) -> bool:
        if info.is_player or (content := info.raw_content) is None or self.lock.locked():
            return True
        try:
            return not any(i(content) for i in self.filter_cache)
        except Exception:
            shared.plg_server_inst.logger.exception('过滤消息时出现错误')
            return True

    @classmethod
    def rebuild_filter_cache(cls, filters: list[InfoFilterConfig]):
        filter_map = counter_filters if shared.config.auto_optimize_info_filter else normal_filters
        filter_cache = []
        for i in filters:
            target = i.target
            if i.method in {InfoFilterMethod.re_match, InfoFilterMethod.re_search}:
                target = compile(target)
            filter_cache.append(filter_map[i.method](target))
        cls.filter_cache = filter_cache
        shared.plg_server_inst.logger.info(f'已加载{len(cls.filter_cache)}条输出过滤规则')

    @classmethod
    def optimize_order(cls):
        if not shared.config.auto_optimize_info_filter:
            return
        cls.filter_cache.sort(key=lambda x: x.count)

    @classmethod
    async def optimize_order_loop(cls):
        while True:
            await asyncio.sleep(shared.config.info_filter_optimization_interval)
            with cls.lock:
                cls.optimize_order()


@dataclass(slots=True)
class FilterLike:
    target: str | Pattern
    count: int = 0

    def __call__(self, x: str) -> bool:
        raise NotImplementedError


@dataclass(slots=True)
class KeywordFilter:
    target: str

    def __call__(self, x: str) -> bool:
        return x in self.target


@dataclass(slots=True)
class StartswithFilter:
    target: str

    def __call__(self, x: str) -> bool:
        return x.startswith(self.target)


@dataclass(slots=True)
class EndswithFilter:
    target: str

    def __call__(self, x: str) -> bool:
        return x.endswith(self.target)


@dataclass(slots=True)
class RegexMatchFilter:
    target: Pattern

    def __call__(self, x: str) -> bool:
        return self.target.match(x) is not None


@dataclass(slots=True)
class RegexSearchFilter:
    target: Pattern

    def __call__(self, x: str) -> bool:
        return self.target.search(x) is not None


normal_filters: dict[InfoFilterMethod, Type[FilterLike]] = {
    InfoFilterMethod.keyword: KeywordFilter,
    InfoFilterMethod.startswith: StartswithFilter,
    InfoFilterMethod.endswith: EndswithFilter,
    InfoFilterMethod.re_match: RegexMatchFilter,
    InfoFilterMethod.re_search: RegexSearchFilter
} # type: ignore


@dataclass(slots=True)
class KeywordFilterWithCounter:
    target: str
    count: int = 0

    def __call__(self, x: str) -> bool:
        if x in self.target:
            self.count += 1
            return True
        return False


@dataclass(slots=True)
class StartswithFilterWithCounter:
    target: str
    count: int = 0

    def __call__(self, x: str) -> bool:
        if x.startswith(self.target):
            self.count += 1
            return True
        return False


@dataclass(slots=True)
class EndswithFilterWithCounter:
    target: str
    count: int = 0

    def __call__(self, x: str) -> bool:
        if x.endswith(self.target):
            self.count += 1
            return True
        return False


@dataclass(slots=True)
class RegexMatchFilterWithCounter:
    target: Pattern
    count: int = 0

    def __call__(self, x: str) -> bool:
        if self.target.match(x) is not None:
            self.count += 1
            return True
        return False


@dataclass(slots=True)
class RegexSearchFilterWithCounter:
    target: Pattern
    count: int = 0

    def __call__(self, x: str) -> bool:
        if self.target.search(x) is not None:
            self.count += 1
            return True
        return False


counter_filters: dict[InfoFilterMethod, Type[FilterLike]] = {
    InfoFilterMethod.keyword: KeywordFilterWithCounter,
    InfoFilterMethod.startswith: StartswithFilterWithCounter,
    InfoFilterMethod.endswith: EndswithFilterWithCounter,
    InfoFilterMethod.re_match: RegexMatchFilterWithCounter,
    InfoFilterMethod.re_search: RegexSearchFilterWithCounter
} # type: ignore
