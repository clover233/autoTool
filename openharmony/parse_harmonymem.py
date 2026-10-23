#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存信息解析脚本
解析hidumper和/proc/memview的输出结果
"""

import re
import sys
from typing import Dict, List, Tuple


class MemoryParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.content = ""
        self.process_memory = {}
        self.memview_data = {}
        # 定义需要解析的进程列表（在这里统一管理，方便扩展）
        self.processes = [
            'com.huawei.hmos.camera',
            'camera_service',
            'CameraDaemon',
            'com.tencent.wechat'
        ]

    def read_file(self):
        """读取文件内容"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
        except Exception as e:
            print(f"读取文件失败: {e}")
            sys.exit(1)

    def parse_hidumper_output(self, process_name: str, text: str) -> Dict[str, int]:
        """解析单个进程的hidumper输出"""
        memory_data = {}

        # 查找Total行，格式如：
        # Total         233402         126872          36064         199792          16960             76             76          99864          96710           7689
        # 对应字段：Pss Total, Shared Clean, Shared Dirty, Private Clean, Private Dirty, Swap Total, SwapPss Total, Heap Size, Heap Alloc, Heap Free

        total_pattern = r'^\s*Total\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)'
        match = re.search(total_pattern, text, re.MULTILINE)

        if match:
            memory_data['Pss Total(kB)'] = int(match.group(1))
            memory_data['Shared Clean(kB)'] = int(match.group(2))
            memory_data['Shared Dirty(kB)'] = int(match.group(3))
            memory_data['Private Clean(kB)'] = int(match.group(4))
            memory_data['Private Dirty(kB)'] = int(match.group(5))
            memory_data['Swap Total(kB)'] = int(match.group(6))
            memory_data['SwapPss Total(kB)'] = int(match.group(7))
            memory_data['Heap Size(kB)'] = int(match.group(8))
            memory_data['Heap Alloc(kB)'] = int(match.group(9))
            memory_data['Heap Free(kB)'] = int(match.group(10))
        else:
            # 如果没有找到Total行，设置默认值为0
            for field in ['Pss Total(kB)', 'Shared Clean(kB)', 'Shared Dirty(kB)',
                         'Private Clean(kB)', 'Private Dirty(kB)', 'Swap Total(kB)',
                         'SwapPss Total(kB)', 'Heap Size(kB)', 'Heap Alloc(kB)', 'Heap Free(kB)']:
                memory_data[field] = 0

        return memory_data

    def parse_all_processes(self):
        """解析所有进程的内存信息"""
        # 将内容按照------[memory]------分割成多个部分
        memory_sections = re.split(r'-+\[memory\]-+', self.content)

        # 第一个部分通常是命令行，从第二个部分开始是实际的内存数据
        process_index = 0
        for section in memory_sections[1:]:  # 跳过第一个部分
            if process_index < len(self.processes):
                process_name = self.processes[process_index]
                self.process_memory[process_name] = self.parse_hidumper_output(process_name, section)
                process_index += 1
            else:
                break

        # 如果某些进程没有找到数据，设置默认值
        for process in self.processes:
            if process not in self.process_memory:
                self.process_memory[process] = {field: 0 for field in [
                    'Pss Total(kB)', 'Shared Clean(kB)', 'Shared Dirty(kB)',
                    'Private Clean(kB)', 'Private Dirty(kB)', 'Swap Total(kB)',
                    'SwapPss Total(kB)', 'Heap Size(kB)', 'Heap Alloc(kB)', 'Heap Free(kB)'
                ]}

    def parse_memview(self):
        """解析/proc/memview的输出"""
        # 查找cat /proc/memview之后的内容
        memview_match = re.search(r'cat\s+/proc/memview(.*?)$', self.content, re.DOTALL)

        if not memview_match:
            print("警告: 未找到/proc/memview的输出")
            return

        memview_text = memview_match.group(1)

        # 定义需要提取的字段
        fields = [
            'LDKSlabUnreclaimable',
            'KSysUsed',
            'CmaUsed',
            'KDrvUsed',
            'UdrvUsed',
            'DmaHeapTotalUsed',
            'GpuTotalUsed'
        ]

        for field in fields:
            # 匹配格式: FieldName: 数字 kB 或 FieldName:数字 kB
            # 例如: LDKSlabUnreclaimable:                    87668 kB
            pattern = rf'{field}:\s*(\d+)\s*kB'
            match = re.search(pattern, memview_text, re.IGNORECASE)
            if match:
                self.memview_data[field] = int(match.group(1))
            else:
                self.memview_data[field] = 0

        # 计算内核占用和驱动内存
        self.memview_data['内核占用'] = (
            self.memview_data.get('LDKSlabUnreclaimable', 0) +
            self.memview_data.get('KSysUsed', 0)
        )

        self.memview_data['驱动内存'] = (
            self.memview_data.get('CmaUsed', 0) +
            self.memview_data.get('KDrvUsed', 0) +
            self.memview_data.get('UdrvUsed', 0) -
            self.memview_data.get('DmaHeapTotalUsed', 0) -
            self.memview_data.get('GpuTotalUsed', 0)
        )

    def print_process_table(self):
        """打印进程内存表格"""
        print("\n" + "="*120)
        print("进程内存信息表格")
        print("="*120)

        # 表头
        headers = ['进程名', 'Pss Total(kB)', 'Shared Clean(kB)', 'Shared Dirty(kB)',
                   'Private Clean(kB)', 'Private Dirty(kB)', 'Swap Total(kB)',
                   'SwapPss Total(kB)', 'Heap Size(kB)', 'Heap Alloc(kB)', 'Heap Free(kB)']

        # 打印表头
        print(f"{headers[0]:<30}", end="")
        for header in headers[1:]:
            print(f"{header:>15}", end="")
        print()
        print("-"*120)

        # 打印每个进程的数据
        for process_name in self.processes:
            if process_name in self.process_memory:
                data = self.process_memory[process_name]
                print(f"{process_name:<30}", end="")
                for header in headers[1:]:
                    value = data.get(header, 0)
                    print(f"{value:>15,}", end="")
                print()

        print("="*120)

    def print_memview_table(self):
        """打印memview内核和驱动内存表格"""
        print("\n" + "="*100)
        print("内核和驱动内存信息表格 (来自 /proc/memview)")
        print("="*100)

        # 定义要显示的字段
        fields = [
            'LDKSlabUnreclaimable',
            'KSysUsed',
            '内核占用',
            'CmaUsed',
            'KDrvUsed',
            'UdrvUsed',
            'DmaHeapTotalUsed',
            'GpuTotalUsed',
            '驱动内存'
        ]

        # 打印表头
        print(f"{'字段名':<30}{'值(kB)':>20}")
        print("-"*100)

        # 打印数据
        for field in fields:
            value = self.memview_data.get(field, 0)
            if field in ['内核占用', '驱动内存']:
                print(f"{field:<30}{value:>20,}  (计算值)")
            else:
                print(f"{field:<30}{value:>20,}")

        print("="*100)

        # 打印计算公式说明
        print("\n计算公式:")
        print("  内核占用 = LDKSlabUnreclaimable + KSysUsed")
        print("  驱动内存 = CmaUsed + KDrvUsed + UdrvUsed - DmaHeapTotalUsed - GpuTotalUsed")

    def export_to_csv(self, output_prefix: str = "report"):
        """导出为CSV文件"""
        import csv

        # 导出进程内存表格
        process_csv = f"{output_prefix}_pro.csv"
        with open(process_csv, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            # 写入表头
            headers = ['进程名', 'Pss Total(kB)', 'Shared Clean(kB)', 'Shared Dirty(kB)',
                       'Private Clean(kB)', 'Private Dirty(kB)', 'Swap Total(kB)',
                       'SwapPss Total(kB)', 'Heap Size(kB)', 'Heap Alloc(kB)', 'Heap Free(kB)']
            writer.writerow(headers)

            # 写入数据
            for process_name in self.processes:
                if process_name in self.process_memory:
                    data = self.process_memory[process_name]
                    row = [process_name] + [data.get(h, 0) for h in headers[1:]]
                    writer.writerow(row)

        print(f"\n进程内存表格已导出到: {process_csv}")

        # 导出memview表格
        memview_csv = f"{output_prefix}_ker.csv"
        with open(memview_csv, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)

            # 字段名列表
            fields = [
                'LDKSlabUnreclaimable',
                'KSysUsed',
                '内核占用',
                'CmaUsed',
                'KDrvUsed',
                'UdrvUsed',
                'DmaHeapTotalUsed',
                'GpuTotalUsed',
                '驱动内存'
            ]

            # 写入第一行：字段名
            writer.writerow(['字段名'] + fields)

            # 写入第二行：内存大小(kB)和对应的值
            values = [self.memview_data.get(field, 0) for field in fields]
            writer.writerow(['内存大小(kB)'] + values)

        print(f"已导出到: {memview_csv}")

    def run(self, export_csv: bool = False):
        """运行解析流程"""
        self.read_file()
        self.parse_all_processes()
        self.parse_memview()
        self.print_process_table()
        self.print_memview_table()

        if export_csv:
            self.export_to_csv()


def main():
    if len(sys.argv) < 2:
        print("用法: python parse_harmonymem.py hidumperx")
        sys.exit(1)

    file_path = sys.argv[1]
    export_csv = '--csv' in sys.argv

    parser = MemoryParser(file_path)
    parser.run(export_csv=export_csv)


if __name__ == "__main__":
    main()
