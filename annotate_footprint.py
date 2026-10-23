#!/usr/bin/env python3
"""按 all_log.txt 的 trace 步骤时间给 footprint_all.xlsx 添加前台应用和步骤。

默认在原表第 4、5 列插入新列，原有列右移，并在覆盖原表前保存备份。
只使用 Python 标准库；针对同目录的 footprint_all.xlsx 大文件逐行处理 XML。
"""

import argparse
from bisect import bisect_right
from datetime import datetime, time, timedelta
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile


DEFAULT_DIR = Path('/Users/clover/Desktop/Result7i/Result/basic3')
LOG_PATTERN = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
    r'.*?iTrace\.py\[line:\d+\].*?trace 同步日志内容 '
    r'\[([^\]]+)\]\[(.*)\]\s*$'
)
CELL_REF = re.compile(rb'(<c\b[^>]*\br=")([A-Z]+)(\d+)(")')
FIRST_CELL = re.compile(rb'<c\s+r="A\d+"\s+t="s"><v>(\d+)</v></c>')
XML_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def column_number(letters):
    n = 0
    for char in letters:
        n = n * 26 + char - 64
    return n


def column_letters(number):
    result = bytearray()
    while number:
        number, remainder = divmod(number - 1, 26)
        result.append(65 + remainder)
    return bytes(reversed(result))


def shift_ref(match):
    number = column_number(match.group(2))
    return (match.group(1) + column_letters(number + 2 if number >= 4 else number)
            + match.group(3) + match.group(4))


def inline_cell(column, row_number, value):
    value = escape(value)
    return (f'<c r="{column}{row_number}" t="inlineStr">'
            f'<is><t>{value}</t></is></c>').encode('utf-8')


def read_events(path):
    events = []
    with path.open('r', encoding='utf-8-sig', errors='replace') as source:
        for line in source:
            match = LOG_PATTERN.match(line.rstrip('\r\n'))
            if match:
                timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
                events.append((timestamp, match.group(2), match.group(3)))
    if not events:
        raise ValueError('日志中没有找到“trace 同步日志内容 [应用][步骤]”记录')
    events.sort(key=lambda item: item[0])
    return events


def read_shared_strings(archive):
    with archive.open('xl/sharedStrings.xml') as stream:
        tree = ET.parse(stream)
    return [''.join(node.itertext()) for node in tree.getroot().findall(f'{XML_NS}si')]


def parse_sample_time(value, current_date, previous_time):
    # 此文件的 A 列为 HH:MM:SS.mmm；跨午夜时向后推进日期。
    parsed = time.fromisoformat(value.strip())
    if previous_time is not None and parsed < previous_time:
        current_date += timedelta(days=1)
    return datetime.combine(current_date, parsed), current_date, parsed


def alter_prefix(prefix):
    dimension = re.search(rb'<dimension ref="A1:([A-Z]+)(\d+)"/>', prefix)
    if not dimension:
        raise ValueError('不支持的工作表维度格式')
    last_col = column_number(dimension.group(1))
    replacement = b'<dimension ref="A1:' + column_letters(last_col + 2) + dimension.group(2) + b'"/>'
    prefix = prefix[:dimension.start()] + replacement + prefix[dimension.end():]

    def shift_selection(match):
        number = column_number(match.group(1))
        return match.group(0)[:match.start(1)-match.start(0)] + column_letters(
            number + 2 if number >= 4 else number) + match.group(2)

    prefix = re.sub(rb'(?<=activeCell=")([A-Z]+)(\d+)(?=")', shift_selection, prefix)
    prefix = re.sub(rb'(?<=sqref=")([A-Z]+)(\d+)(?=")', shift_selection, prefix)

    cols = re.search(rb'<cols>(.*?)</cols>', prefix, re.DOTALL)
    if cols:
        old = cols.group(1)
        def shift_col(match):
            first, last = int(match.group(1)), int(match.group(2))
            if first >= 4:
                first += 2
                last += 2
            return b'<col min="%d" max="%d"' % (first, last)
        old = re.sub(rb'<col min="(\d+)" max="(\d+)"', shift_col, old)
        new = (b'<col min="4" max="4" width="20" customWidth="1"/>'
               b'<col min="5" max="5" width="65" customWidth="1"/>')
        split = old.find(b'<col min="6"')
        if split < 0:
            raise ValueError('无法确认列宽定义的插入位置')
        prefix = (prefix[:cols.start()] + b'<cols>' + old[:split] + new
                  + old[split:] + b'</cols>' + prefix[cols.end():])
    return prefix


def rows_from_sheet(stream):
    buffer = b''
    before_first = True
    while True:
        block = stream.read(1024 * 1024)
        if block:
            buffer += block
        while True:
            start = buffer.find(b'<row ')
            if start < 0:
                break
            end = buffer.find(b'</row>', start)
            if end < 0:
                break
            if before_first:
                yield 'prefix', buffer[:start]
                before_first = False
            elif start:
                yield 'between', buffer[:start]
            end += len(b'</row>')
            yield 'row', buffer[start:end]
            buffer = buffer[end:]
        if not block:
            if before_first:
                raise ValueError('工作表没有数据行')
            yield 'suffix', buffer
            break


def annotate(source_path, log_path, output_path, backup):
    events = read_events(log_path)
    event_times = [item[0] for item in events]
    counts = {'rows': 0, 'matched': 0, 'blank': 0}
    current_date = events[0][0].date()
    previous_time = None
    last_sample = None
    last_label = None

    with zipfile.ZipFile(source_path) as source:
        names = set(source.namelist())
        if 'xl/sharedStrings.xml' not in names or 'xl/worksheets/sheet1.xml' not in names:
            raise ValueError('输入表缺少预期的共享字符串或第一个工作表')
        strings = read_shared_strings(source)
        with tempfile.NamedTemporaryFile(dir=output_path.parent, suffix='.xlsx', delete=False) as tmp:
            temp_path = Path(tmp.name)
        try:
            with zipfile.ZipFile(temp_path, 'w') as target:
                for info in source.infolist():
                    if info.filename != 'xl/worksheets/sheet1.xml':
                        target.writestr(info, source.read(info.filename))
                        continue
                    with source.open(info) as sheet, target.open(info, 'w') as destination:
                        for kind, data in rows_from_sheet(sheet):
                            if kind == 'prefix':
                                if b'<mergeCells' in data or b'<conditionalFormatting' in data:
                                    raise ValueError('此脚本未处理合并单元格或条件格式')
                                destination.write(alter_prefix(data))
                            elif kind == 'row':
                                number_match = re.match(rb'<row r="(\d+)"', data)
                                if not number_match:
                                    raise ValueError('无法读取行号')
                                row_number = int(number_match.group(1))
                                if b'<f' in data:
                                    raise ValueError('此脚本未处理公式单元格')
                                if row_number == 1:
                                    head = FIRST_CELL.search(data)
                                    if not head or strings[int(head.group(1))] != 'timestamp':
                                        raise ValueError('首列标题不是 timestamp')
                                    fourth = re.search(rb'<c r="D1" t="s"><v>(\d+)</v></c>', data)
                                    if not fourth or strings[int(fourth.group(1))] != 'proc_name':
                                        raise ValueError('第 4 列不是 proc_name；可能已经处理过')
                                    app, step = '前台应用', '步骤'
                                else:
                                    first = FIRST_CELL.search(data)
                                    if not first:
                                        raise ValueError(f'第 {row_number} 行的 timestamp 不是共享字符串')
                                    sample, current_date, previous_time = parse_sample_time(
                                        strings[int(first.group(1))], current_date, previous_time)
                                    if sample == last_sample:
                                        label = last_label
                                    else:
                                        index = bisect_right(event_times, sample) - 1
                                        label = events[index][1:] if index >= 0 else ('', '')
                                        last_sample, last_label = sample, label
                                    app, step = label
                                    counts['rows'] += 1
                                    counts['matched' if app else 'blank'] += 1
                                data = CELL_REF.sub(shift_ref, data)
                                data = re.sub(rb'\bspans="1:\d+"', b'spans="1:15"', data, count=1)
                                insert_at = data.find(b'</c>', data.find(b'<c r="C' + str(row_number).encode() + b'"'))
                                if insert_at < 0:
                                    raise ValueError(f'第 {row_number} 行没有 C 列')
                                insert_at += len(b'</c>')
                                data = (data[:insert_at] + inline_cell('D', row_number, app)
                                        + inline_cell('E', row_number, step) + data[insert_at:])
                                destination.write(data)
                            else:
                                destination.write(data)
            with zipfile.ZipFile(temp_path) as check:
                if check.testzip() is not None:
                    raise ValueError('输出文件 ZIP 校验失败')
            if backup and output_path.resolve() == source_path.resolve():
                backup_path = source_path.with_name(source_path.stem + '.before_labels.xlsx')
                if not backup_path.exists():
                    shutil.copy2(source_path, backup_path)
                    print(f'备份：{backup_path}')
            temp_path.replace(output_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, default=DEFAULT_DIR / 'all_log.txt')
    parser.add_argument('--xlsx', type=Path, default=DEFAULT_DIR / 'footprint_all.xlsx')
    parser.add_argument('--output', type=Path, help='输出路径；不指定则写回原表并备份')
    args = parser.parse_args()
    output = args.output or args.xlsx
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = annotate(args.xlsx, args.log, output, backup=args.output is None)
    print(f'完成：{output}')
    print(f"数据行：{counts['rows']}，匹配：{counts['matched']}，早于首条日志而留空：{counts['blank']}")


if __name__ == '__main__':
    main()
