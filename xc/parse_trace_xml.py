#!/usr/bin/env python3
"""将单个或目录内全部 activity-monitor XML 转换成同名 _res.xlsx。"""

import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from xctrace_tools.config import DEFAULT_RESULT_DIR
from xctrace_tools.files import find_activity_xml
from xctrace_tools.memory import XCTraceXMLParser


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path, default=DEFAULT_RESULT_DIR,
                        help='XML 文件或结果目录')
    parser.add_argument('--columns', nargs='+', help='仅导出指定 mnemonic 列')
    args = parser.parse_args(argv)
    source = args.input.expanduser()
    try:
        if source.is_file():
            if source.suffix.lower() != '.xml':
                parser.error('输入文件必须使用 .xml 扩展名')
            paths = [source]
        else:
            paths = find_activity_xml(source)
        if not paths:
            parser.error('没有找到 PerformanceDynamic_*.xml')
        failed = 0
        for index, path in enumerate(paths, 1):
            try:
                records = XCTraceXMLParser(path, args.columns).parse()
                print(f'[{index}/{len(paths)}] 已转换 {len(records)} 条记录: {path}')
            except (OSError, ValueError, ET.ParseError) as exc:
                failed += 1
                print(f'转换失败: {path}: {exc}', file=sys.stderr)
    except ModuleNotFoundError as exc:
        if exc.name not in ('pandas', 'openpyxl'):
            raise
        parser.exit(1, '缺少依赖，请运行：python3 -m pip install -r requirements.txt\n')
    except OSError as exc:
        parser.exit(1, f'转换失败：{exc}\n')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
