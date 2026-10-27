#!/usr/bin/env python3
"""导出 trace 的 hitches 表，并合并为卡顿 summary.csv。"""

import argparse
import csv
import logging
from pathlib import Path
import xml.etree.ElementTree as ET

from xctrace_tools.config import HITCH_SCHEMA
from xctrace_tools.export import export_trace
from xctrace_tools.files import find_traces
from xctrace_tools.xmlio import build_id_map, resolve_element

logger = logging.getLogger(__name__)
FIELDS = ['start-time', 'process', 'process_name', 'hitches_timeduration']


def parse_hitches_summary(hitches_summary_xml_path):
    root = ET.parse(hitches_summary_xml_path).getroot()
    references = build_id_map(root)
    results = []
    for index, row in enumerate(root.iter('row'), 1):
        if row.find('process') is None:
            continue
        values = {}
        for field in ('process', 'duration', 'start-time'):
            element = resolve_element(row.find(field), references)
            value = element.get('fmt')
            if value is None:
                raise ValueError(f'第 {index} 行 {field} 缺少 fmt')
            values[field] = value
        results.append({'start-time': values['start-time'], 'process': values['process'],
                        'process_name': values['process'].split('(')[0].strip(),
                        'hitches_timeduration': values['duration']})
    return results


def parse_all_xml(hitches_summary_file_path):
    return parse_hitches_summary(hitches_summary_file_path)


def gen_xml(trace_file, is_regen_xml=True, *, developer_dir=None):
    trace = Path(trace_file)
    output = trace.with_name(trace.stem + '_hitches_summary.xml')
    export_trace(trace, output, HITCH_SCHEMA, force=is_regen_xml, developer_dir=developer_dir)
    return str(output)


def gen_result(all_trace_file, is_just_genxml=False, output='summary.csv', *,
               force=False, developer_dir=None):
    traces = list(all_trace_file)
    if not traces:
        raise ValueError('没有找到 .trace 文件')
    results, errors = [], []
    for trace in traces:
        try:
            xml = gen_xml(trace, is_regen_xml=force, developer_dir=developer_dir)
            if not is_just_genxml:
                results.extend(parse_all_xml(xml))
        except (OSError, ValueError, RuntimeError, ET.ParseError) as exc:
            errors.append((str(trace), str(exc)))
            logger.error('%s: %s', trace, exc)
    if not is_just_genxml:
        output = Path(output).expanduser()
        if output.suffix.lower() != '.csv':
            raise ValueError('输出文件必须使用 .csv 扩展名')
        if output.resolve() in {Path(trace).resolve() for trace in traces}:
            raise ValueError('输出不能覆盖源 trace')
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(results)
    return results, errors


def run(result_dir_path, *, output='summary.csv', export_only=False, force=False, developer_dir=None):
    return gen_result(find_traces(result_dir_path), export_only, output,
                      force=force, developer_dir=developer_dir)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result-dir', '-r', type=Path, default=Path('/Users/clover/Desktop/Basic1'))
    parser.add_argument('--output', '-o', type=Path, default=Path('summary.csv'))
    parser.add_argument('--export-only', action='store_true', help='仅导出 XML，不生成 CSV')
    parser.add_argument('--force', action='store_true', help='重新导出已有 XML')
    parser.add_argument('--developer-dir', type=Path)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    if not args.export_only and args.output.suffix.lower() != '.csv':
        parser.error('输出文件必须使用 .csv 扩展名')
    try:
        records, errors = run(args.result_dir, output=args.output, export_only=args.export_only,
                             force=args.force, developer_dir=args.developer_dir)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'卡顿汇总失败：{exc}\n')
    print(f'卡顿记录: {len(records)}；失败 trace: {len(errors)}')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
