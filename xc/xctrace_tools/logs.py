"""步骤日志解析及采样点前台应用匹配。"""

import re
from decimal import Decimal
from pathlib import Path

STEP_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*:\s*\[([^\]]+)\]\[([^\]]+)\]')


def parse_step_log(path):
    path = Path(path)
    text = path.read_text(encoding='utf-8-sig', errors='replace')
    case = path.name.split('-')[0]
    return sorted(
        ({'case_name': case, 'step_ts': int(Decimal(match[1]) * 1_000_000_000),
          'app_name': match[2].strip(), 'step': match[3].strip()}
         for match in STEP_PATTERN.finditer(text)),
        key=lambda event: event['step_ts'],
    )


def step_at_sample(xml_path, sample_ns):
    log_path = Path(xml_path).with_suffix('.log')
    if not log_path.is_file():
        return '', '', '缺少配套 .log，无法判断前台'
    events = parse_step_log(log_path)
    if not events:
        return '', '', '日志没有有效前台应用记录'
    preceding = [event for event in events if event['step_ts'] <= sample_ns]
    event = preceding[-1] if preceding else events[0]
    note = '' if preceding else '采样早于首次日志，按该 trace 首条步骤标注前台'
    return event['app_name'], event['step'], note
