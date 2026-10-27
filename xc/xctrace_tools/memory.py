"""通用 XML 转表及两种步骤内存分析方式。"""

from bisect import bisect_right
from collections import defaultdict
import math
import re
from pathlib import Path

from .config import (ACTIVITY_SCHEMA, DESK_PROCESS, GRAPH_PROCESS, INPUT_PROCESS,
                     IOS_PACKAGES_MAP, SERVICE_IGNORED, bytes_to_mb)
from .files import paired_activity_files
from .logs import parse_step_log
from .xmlio import TraceTable, build_id_map, resolve_element


def write_records(records, output, sheet_name, *, include_index=False):
    # 只在输出时报表依赖 pandas，纯解析无需加载 Excel 引擎。
    import pandas as pd

    output = Path(output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    # xlsxwriter 对字符串默认尝试解析公式，显式使用 openpyxl 并将外部文本标为文本。
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(records).to_excel(writer, sheet_name=sheet_name, index=include_index)
        for row in writer.sheets[sheet_name]:
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = 's'
    return output


class XCTraceXMLParser:
    def __init__(self, xml_path, schema_columns=None):
        self.xml_path = str(xml_path)
        self.schema_columns = list(schema_columns or ())
        self.tree = self.root = None
        self.records = []
        self.id_map = {}
        self.schema = {}

    def parse(self, export=True, output=None):
        """重复调用会重置结果；错误交由调用方处理，避免输出残缺数据。"""
        self.records = []
        self.schema = {}
        self.id_map = {}
        self.tree = self.root = None
        table = TraceTable(self.xml_path, ACTIVITY_SCHEMA)
        self.tree, self.root = table.tree, table.root
        self.schema = table.schema
        self.id_map = table.references
        self.records = table.records(self.schema_columns)
        if export:
            target = output or Path(self.xml_path).with_name(Path(self.xml_path).stem + '_res.xlsx')
            write_records(self.records, target, 'xctrace数据', include_index=True)
        return self.records

    def parse_schema(self, schema_node):
        self.schema = {col.findtext('mnemonic'): {'name': col.findtext('name'),
                                                 'type': col.findtext('engineering-type')}
                       for col in schema_node.findall('col')}

    def build_id_map(self, rows):
        self.id_map = {}
        for row in rows:
            self.id_map.update(build_id_map(row))

    def parse_row(self, row):
        if len(row) != len(self.schema):
            raise ValueError('XML 行列数与 schema 不一致')
        return {name: self.parse_element(element)
                for name, element in zip(self.schema, row)
                if not self.schema_columns or name in self.schema_columns}

    def parse_element(self, element):
        return TraceTable.value(self, element)

    def resolve(self, element):
        return resolve_element(element, self.id_map)


def sample_timestamps(records, time_field='start'):
    return sorted({int(record[time_field]) for record in records})


def memory_totals(case_name, app, step_id, step_name, records):
    totals = defaultdict(int)
    for record in records:
        process = record['process']
        footprint = int(record['memory-physical-footprint'])
        compressed = int(record['memory-compressed'])
        if footprint < 0 or compressed < 0:
            raise ValueError(f'进程 {process} 的内存值为负数')
        if process in IOS_PACKAGES_MAP:
            groups = ['应用内存']
            if IOS_PACKAGES_MAP[process] == app:
                groups.append('前台应用内存')
        elif process in SERVICE_IGNORED:
            continue
        else:
            # 图形、大桌面和输入法为系统服务的子集，保留原统计口径。
            groups = ['系统服务内存']
            for processes, group in ((GRAPH_PROCESS, '图形内存'), (DESK_PROCESS, '大桌面'),
                                     (INPUT_PROCESS, '输入法')):
                if process in processes:
                    groups.append(group)
        for group in groups:
            totals[group] += footprint
            totals[group + '(压缩)'] += compressed
    result = {'用例': case_name, '应用': app, '步骤id': step_id, '操作步骤': step_name}
    for group in ('前台应用内存', '应用内存', '系统服务内存', '图形内存', '大桌面', '输入法'):
        for key in (group, group + '(压缩)'):
            result[key] = bytes_to_mb(totals[key])
    result.update({'内核+驱动': None, '预留': None})
    return result


class MemoryAnalyse:
    """一个 XML/log 文件对，按步骤结束前一秒选样；最后一步默认延后五秒。"""

    def __init__(self, case_log_folder, time_field='start', *, last_step_seconds=5):
        if not math.isfinite(last_step_seconds) or last_step_seconds < 0:
            raise ValueError('最后一步采样偏移必须为非负有限数值')
        self.case_log_folder = str(case_log_folder)
        self.time_field = time_field
        self.last_step_seconds = last_step_seconds
        self.case_records, self.log_path, self.case_name = self.get_xml_and_log()
        self.record_ts_list = self.get_ts_list()
        if not self.record_ts_list:
            raise ValueError('XML 没有采样记录')
        self._records_by_time = defaultdict(list)
        for record in self.case_records:
            self._records_by_time[int(record[self.time_field])].append(record)
        self.case_steps = self.parse_log()
        if not self.case_steps:
            raise ValueError(f'日志没有有效步骤: {self.log_path}')

    def get_xml_and_log(self):
        pairs = paired_activity_files(self.case_log_folder)
        if len(pairs) != 1:
            raise ValueError('单文件分析需要且仅需要一个 XML/log 文件对；多个步骤请使用 MemoryAnalyseNew')
        xml, log = pairs[0]
        records = XCTraceXMLParser(xml).parse(export=False)
        return records, str(log), log.name.split('-')[0]

    def get_ts_list(self):
        return sample_timestamps(self.case_records, self.time_field)

    def parse_log(self):
        return parse_step_log(self.log_path)

    def get_trace_records_by_time(self, cur_time):
        # 精确命中采样点时选择该点，落在两点之间时选择前一点。
        index = max(0, bisect_right(self.record_ts_list, cur_time) - 1)
        return self._records_by_time[self.record_ts_list[index]]

    def get_case_step_memory(self, step_idx):
        step = self.case_steps[step_idx]
        target = (self.case_steps[step_idx + 1]['step_ts'] - 1_000_000_000
                  if step_idx + 1 < len(self.case_steps)
                  else step['step_ts'] + int(self.last_step_seconds * 1_000_000_000))
        return memory_totals(self.case_name, step['app_name'], step_idx + 1, step['step'],
                             self.get_trace_records_by_time(target))

    def get_case_mem(self, output=None):
        records = [self.get_case_step_memory(index) for index in range(len(self.case_steps))]
        write_records(records, output or Path(self.case_log_folder) / f'{self.case_name}.xlsx', '用例内存数据')
        return records


class MemoryAnalyseNew:
    """每一步一个 XML/log 文件对，取第二个不同时间戳；保留文件名中的步骤 ID。"""

    def __init__(self, case_log_folder, time_field='start'):
        self.case_log_folder = str(case_log_folder)
        self.time_field = time_field
        self.xml_path_list, self.log_path_list, self.case_name = self.get_xml_and_log()

    def get_xml_and_log(self):
        pairs = paired_activity_files(self.case_log_folder)
        cases = {log.name.split('-')[0] for _, log in pairs}
        if len(cases) != 1:
            raise ValueError('步骤分析目录包含多个用例，请分别指定用例目录')
        return [str(xml) for xml, _ in pairs], [str(log) for _, log in pairs], cases.pop()

    def get_case_mem(self, output=None):
        steps = {}
        for xml_path, log_path in zip(self.xml_path_list, self.log_path_list):
            match = re.search(r'-step_(\d+)-', Path(xml_path).stem)
            if not match:
                raise ValueError(f'文件名缺少 step_ 步骤编号: {xml_path}')
            step_id = int(match[1])
            if step_id in steps:
                raise ValueError(f'重复步骤编号 {step_id}，请分别指定每次运行的目录')
            steps[step_id] = (xml_path, log_path)
        records = []
        for step_id, (xml_path, log_path) in sorted(steps.items()):
            step, sample = self.parse_xml_and_log(xml_path, log_path)
            records.append(self.get_case_step_memory(step['app_name'], step_id, step['step'], sample))
        write_records(records, output or Path(self.case_log_folder) / f'{self.case_name}.xlsx', '用例内存数据')
        return records

    def parse_xml_and_log(self, xml_path, log_path):
        records = XCTraceXMLParser(xml_path).parse(export=False)
        timestamps = self.get_ts_list(records)
        if len(timestamps) < 2:
            raise ValueError(f'XML 少于两个采样点: {xml_path}')
        sample = [row for row in records if int(row[self.time_field]) == timestamps[1]]
        steps = self.parse_log(log_path)
        if len(steps) != 1:
            raise ValueError(f'步骤日志应包含且仅包含一条步骤记录: {log_path}')
        return steps[0], sample

    def get_ts_list(self, case_records):
        return sample_timestamps(case_records, self.time_field)

    def parse_log(self, log_path):
        return parse_step_log(log_path)

    def get_case_step_memory(self, app, step_idx, step_name, step_records):
        return memory_totals(self.case_name, app, step_idx, step_name, step_records)
