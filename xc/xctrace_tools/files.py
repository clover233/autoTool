"""扫描结果目录；将 .trace 目录包作为一个文件处理。"""

import os
from pathlib import Path


def walk_files(directory):
    directory = Path(directory).expanduser()
    if not directory.is_dir():
        raise NotADirectoryError(f'结果目录不存在: {directory}')
    if directory.suffix.lower() == '.trace':
        return
    for parent, dirs, files in os.walk(directory):
        dirs[:] = sorted(name for name in dirs if not name.lower().endswith('.trace'))
        for name in sorted(files):
            yield Path(parent) / name


def find_activity_xml(directory):
    return sorted(path for path in walk_files(directory)
                  if path.name.startswith('PerformanceDynamic_')
                  and path.suffix.lower() == '.xml'
                  and not path.stem.endswith('_hitches_summary'))


def find_traces(directory):
    directory = Path(directory).expanduser()
    if not directory.is_dir():
        raise NotADirectoryError(f'结果目录不存在: {directory}')
    if directory.suffix.lower() == '.trace':
        return [directory]
    traces = []
    for parent, dirs, files in os.walk(directory):
        for name in sorted(dirs + files):
            if name.lower().endswith('.trace'):
                traces.append(Path(parent) / name)
        dirs[:] = sorted(name for name in dirs if not name.lower().endswith('.trace'))
    return sorted(traces)


def paired_activity_files(directory):
    """按同目录、同文件名配对，拒绝数量相等但名称不匹配的输入。"""
    pairs = []
    for xml in find_activity_xml(directory):
        log = xml.with_suffix('.log')
        if not log.is_file():
            raise FileNotFoundError(f'XML 缺少同名日志: {log}')
        pairs.append((xml, log))
    if not pairs:
        raise FileNotFoundError(f'没有找到 PerformanceDynamic_*.xml: {directory}')
    return pairs
