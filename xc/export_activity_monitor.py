#!/usr/bin/env python3
"""批量导出 activity-monitor-process-live XML，与源 trace 保存在同一目录。"""

import argparse
import logging
from pathlib import Path

from xctrace_tools.config import ACTIVITY_SCHEMA, DEFAULT_RESULT_DIR
from xctrace_tools.export import export_traces
from xctrace_tools.files import find_traces

BASE_PATH = DEFAULT_RESULT_DIR
XCODE_DEVELOPER_DIR = Path('/Applications/Xcode.app/Contents/Developer')


def find_trace_files(result_dir=None):
    return find_traces(result_dir if result_dir is not None else BASE_PATH)


def gen_activitymonitor_all_traces(result_dir=None, *, force=False, developer_dir=None):
    traces = find_trace_files(result_dir)
    if not traces:
        raise ValueError('没有找到 .trace 文件')
    return export_traces(traces, ACTIVITY_SCHEMA, force=force, developer_dir=developer_dir)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-dir', '-r', type=Path, default=BASE_PATH)
    parser.add_argument('--force', action='store_true', help='重新导出已有 XML')
    parser.add_argument('--developer-dir', type=Path, help='指定 Xcode Developer 目录；默认使用系统配置')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    try:
        stats = gen_activitymonitor_all_traces(args.result_dir, force=args.force,
                                              developer_dir=args.developer_dir)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'导出失败：{exc}\n')
    return 1 if stats.failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
