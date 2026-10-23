import os
import logging
import shlex
import subprocess
from pathlib import Path

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger("matplotlib.font_manager").disabled = True
formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)

# result1 下每个 PerformanceDynamic_* 目录都有自己的 Traces 子目录。
BASE_PATH = Path("/Users/clover/Desktop/SeaOfStars7i/Result/result1")
XCODE_DEVELOPER_DIR = Path("/Applications/Xcode.app/Contents/Developer")


def find_trace_files():
    """查找各 PerformanceDynamic_* / Traces 目录中的所有 .trace 包。"""
    trace_files = []
    for case_dir in sorted(BASE_PATH.glob("PerformanceDynamic_*")):
        traces_dir = case_dir / "Traces"
        if not traces_dir.is_dir():
            logging.warning(f"跳过：未找到 Traces 目录: {traces_dir}")
            continue

        trace_files.extend(
            path for path in traces_dir.iterdir()
            if path.suffix.lower() == ".trace"
        )
    return sorted(trace_files)


def gen_activitymonitor_all_traces():
    # xctrace export 命令的 XPath 字符串
    xpath_str = '/trace-toc/run[@number="1"]/data/table[@schema="activity-monitor-process-live"]'

    if not BASE_PATH.is_dir():
        logging.error(f"结果目录不存在: {BASE_PATH}")
        return

    # 使用指定 Xcode 提供的 xctrace，不依赖 xcode-select 的当前设置。
    if not XCODE_DEVELOPER_DIR.is_dir():
        logging.error(f"Xcode Developer 目录不存在: {XCODE_DEVELOPER_DIR}")
        return

    command_env = os.environ.copy()
    command_env["DEVELOPER_DIR"] = str(XCODE_DEVELOPER_DIR)

    trace_files = find_trace_files()
    if not trace_files:
        logging.warning(f"没有找到 .trace 文件: {BASE_PATH}/PerformanceDynamic_*/Traces")
        return

    logging.info(f"共找到 {len(trace_files)} 个 .trace 文件")
    succeeded = 0
    skipped = 0
    failed = 0

    for index, input_file_path in enumerate(trace_files, start=1):
        # XML 与 trace 保存在同一个 Traces 目录中，并使用相同的文件名。
        output_xml_path = input_file_path.with_suffix(".xml")
        if output_xml_path.is_file() and output_xml_path.stat().st_size > 0:
            logging.info(f"[{index}/{len(trace_files)}] 已存在，跳过: {output_xml_path}")
            skipped += 1
            continue

        xctrace_cmd = [
            "/usr/bin/xcrun",
            "xctrace",
            "export",
            "--input",
            str(input_file_path),
            "--xpath",
            xpath_str,
            "--output",
            str(output_xml_path),
        ]
        logging.info(
            f"[{index}/{len(trace_files)}] 正在生成 XML: {input_file_path}\n"
            f"{shlex.join(xctrace_cmd)}"
        )

        try:
            subprocess.run(xctrace_cmd, check=True, env=command_env)
        except subprocess.CalledProcessError as exc:
            failed += 1
            logging.error(
                f"生成失败: {output_xml_path}，xctrace 退出码: {exc.returncode}"
            )
            continue

        if not output_xml_path.is_file() or output_xml_path.stat().st_size == 0:
            failed += 1
            logging.error(f"xctrace 执行完成，但没有生成有效文件: {output_xml_path}")
            continue

        succeeded += 1
        logging.info(f"生成完成: {output_xml_path}")

    logging.info(
        f"处理结束：成功 {succeeded}，跳过 {skipped}，失败 {failed}，"
        f"总计 {len(trace_files)}"
    )


if __name__ == "__main__":
    gen_activitymonitor_all_traces()
