
from pathlib import Path

from arucraftr import shared
from arucraftr.websocket.event import ArcEvent
from arucraftr.crash_report.handle import analyze_forge_crash_report


async def report_crash(path: Path):
    match shared.plg_server_inst.get_mcdr_config()['handler']:
        case 'vanilla_handler':
            pass
        case 'forge_handler':
            crash_report = analyze_forge_crash_report(path)
    await ArcEvent.crash.report(crash_report=crash_report)
