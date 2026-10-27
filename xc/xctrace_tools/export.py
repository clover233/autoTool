"""安全调用 xctrace，验证输出后原子替换，失败时保留原结果。"""

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class ExportStats:
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0


def valid_xml(path):
    try:
        ET.parse(path)
        return True
    except (OSError, ET.ParseError):
        return False


def export_trace(trace, output, schema, *, force=False, developer_dir=None, attempts=3):
    """返回是否重新导出；已有有效 XML 时返回 False。"""
    trace, output = Path(trace).expanduser(), Path(output).expanduser()
    if not trace.exists():
        raise FileNotFoundError(f'trace 不存在: {trace}')
    if trace.resolve() == output.resolve():
        raise ValueError('输出不能覆盖源 trace')
    if attempts < 1:
        raise ValueError('重试次数必须至少为 1')
    if not force and valid_xml(output):
        logger.info('已存在，跳过: %s', output)
        return False
    env = os.environ.copy()
    if developer_dir is not None:
        developer_dir = Path(developer_dir).expanduser()
        if not developer_dir.is_dir():
            raise NotADirectoryError(f'Xcode Developer 目录不存在: {developer_dir}')
        env['DEVELOPER_DIR'] = str(developer_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    xpath = f'/trace-toc/run[@number="1"]/data/table[@schema="{schema}"]'
    last_error = None
    for attempt in range(1, attempts + 1):
        # xctrace 要求输出文件尚不存在。临时目录与目标同盘，可原子替换。
        with TemporaryDirectory(prefix='.xctrace-', dir=output.parent) as temporary:
            temporary_output = Path(temporary) / output.name
            command = ['/usr/bin/xcrun', 'xctrace', 'export', '--input', str(trace),
                       '--xpath', xpath, '--output', str(temporary_output)]
            logger.info('导出 (%s/%s): %s', attempt, attempts, shlex.join(command))
            try:
                subprocess.run(command, check=True, env=env)
                if not valid_xml(temporary_output):
                    raise ValueError('xctrace 未生成有效 XML')
                temporary_output.replace(output)
                return True
            except (OSError, subprocess.CalledProcessError, ValueError) as exc:
                last_error = exc
                logger.warning('导出失败: %s', exc)
    raise RuntimeError(f'导出 {trace} 失败（{attempts} 次）: {last_error}') from last_error


def export_traces(traces, schema, *, suffix='', force=False, developer_dir=None):
    stats = ExportStats()
    traces = list(traces)
    for index, trace in enumerate(traces, 1):
        trace = Path(trace)
        output = trace.with_name(f'{trace.stem}{suffix}.xml')
        logger.info('[%s/%s] %s', index, len(traces), trace)
        try:
            changed = export_trace(trace, output, schema, force=force, developer_dir=developer_dir)
        except (OSError, ValueError, RuntimeError) as exc:
            stats.failed += 1
            logger.error('%s', exc)
        else:
            if changed:
                stats.succeeded += 1
            else:
                stats.skipped += 1
    logger.info('处理结束：成功 %s，跳过 %s，失败 %s',
                stats.succeeded, stats.skipped, stats.failed)
    return stats
