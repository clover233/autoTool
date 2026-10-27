#!/usr/bin/env python3
"""根据配套步骤日志，生成单个用例的内存分类 Excel。"""

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from xctrace_tools.config import DEFAULT_RESULT_DIR
from xctrace_tools.memory import MemoryAnalyse, MemoryAnalyseNew


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-dir', '-r', type=Path, default=DEFAULT_RESULT_DIR,
                        help='一个用例/一次运行的目录')
    parser.add_argument('--mode', choices=('single', 'steps'), default='steps',
                        help='single: 一个 XML/log；steps: 每步一个 XML/log（默认）')
    parser.add_argument('--last-step-seconds', type=float, default=5,
                        help='single 模式最后一步采样偏移，默认 5 秒；旧 xcnolog 为 1 秒')
    parser.add_argument('--output', '-o', type=Path, help='默认输出到用例目录的 用例名.xlsx')
    args = parser.parse_args(argv)
    if args.output and args.output.suffix.lower() != '.xlsx':
        parser.error('输出文件扩展名必须为 .xlsx')
    if not math.isfinite(args.last_step_seconds) or args.last_step_seconds < 0:
        parser.error('最后一步采样偏移必须为非负有限数值')
    try:
        if args.mode == 'single':
            analysis = MemoryAnalyse(args.result_dir.expanduser(), last_step_seconds=args.last_step_seconds)
        else:
            analysis = MemoryAnalyseNew(args.result_dir.expanduser())
        records = analysis.get_case_mem(args.output)
    except ModuleNotFoundError as exc:
        if exc.name not in ('pandas', 'openpyxl'):
            raise
        parser.exit(1, '缺少依赖，请运行：python3 -m pip install -r requirements.txt\n')
    except (OSError, ValueError, KeyError, ET.ParseError) as exc:
        parser.exit(1, f'内存分析失败：{exc}\n')
    print(f'已导出 {len(records)} 个步骤的内存数据')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
