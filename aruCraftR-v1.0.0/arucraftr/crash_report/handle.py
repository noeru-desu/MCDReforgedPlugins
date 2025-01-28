
from collections import OrderedDict
from pathlib import Path
import re
from typing import Generator, TextIO, TypedDict

from arucraftr import shared


SKIP_LINES = 2
SKIP_CATEGORIES = {'Minecraft Crash Report', 'Thread Dump', 'Performance stats'}

forge_pattern = {
    'System Details': ['\n\n-- Mod list --']
}


category_re = re.compile(r'-+ (?P<category>[\w ]+) -+')


def analyze_category(file_path: Path) -> Generator[tuple[str, str]]:
    with file_path.open() as f:
        current_category: str = None # type: ignore
        skiping = True
        line_num = 0
        while True:
            line_num += 1
            line = f.readline().strip()
            if not line:
                return
            if line_num <= SKIP_LINES or line.startswith('//'):
                continue
            if current_category is None and line.startswith('Description'):
                current_category = 'Minecraft Crash Report'
                skiping = False
            elif (category_regex := category_re.match(line)) is not None:
                    current_category = category_regex['category'].split('(', 2)[0].strip()
                    skiping = current_category in SKIP_CATEGORIES
                    continue
            if skiping:
                continue
            yield current_category, line


forge_mod_re = re.compile(r'^(?P<file>[^\|]+)\|(?P<name>[^\|]+)\|(?P<namespace>[^\|]+)\|(?P<version>[^\|]+)\|(?P<other>[^\|]+)?')
traceback_re = re.compile(r'^(?P<trace>at.+)(?=\{)')


def analyze_forge_crash_report(path: Path) -> OrderedDict[str, list[str]]:
    # 1. 根据 -- xxx -- 进行目录分割
    # 2. 对某些目录进行特殊操作并记录
    shared.plg_server_inst.logger.warning(f'\n{'-'*30}\n\n{' '*4}正在处理崩溃日志, 请稍等\n\n{'-'*30}')
    formated_crash_report: OrderedDict[str, list] = OrderedDict(forge_pattern)
    for category, line in analyze_category(path):
        if (lines := formated_crash_report.get(category)) is None:
            lines = formated_crash_report[category] = [f'\n\n-- {category} --']
        match category:
            case 'System Details':
                line = line.strip('|')
                if (regex := forge_mod_re.match(line)) is None:
                    continue
                lines.append(regex['name'].strip(' '))
            case c:
                if line.startswith('at') and (regex := traceback_re.match(line)) is not None:
                    line = regex['trace'].strip()
                    continue
                lines.append(line)
    return formated_crash_report
