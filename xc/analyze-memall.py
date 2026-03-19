import os
import logging
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger("matplotlib.font_manager").disabled = True
formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)

# 定义基础路径 /Users/clover/Documents/111/Traces
BASE_PATH = "/Users/clover/Documents/111"
TRACE_DIR = os.path.join(BASE_PATH, "Traces")
OUTPUT_DIR = os.path.join(BASE_PATH, "Traces")


def gen_activitymonitor_all_traces():
    # xctrace export 命令的 XPath 字符串
    xpath_str = "'/trace-toc/run[@number=\"1\"]/data/table[@schema=\"activity-monitor-process-live\"]'"

    # 检查 trace 目录是否存在
    if not os.path.isdir(TRACE_DIR):
        logging.error(f"Trace 目录不存在: {TRACE_DIR}")
        return

    # 遍历 Trace 目录下的所有文件
    for filename in os.listdir(TRACE_DIR):
        # 筛选出所有以 .trace 结尾的文件
        if filename.endswith(".trace"):
            # 1. 构造完整的输入文件路径
            input_file_path = os.path.join(TRACE_DIR, filename)

            # 2. 构造输出文件路径，获取不包含扩展名的文件名部分
            base_filename = os.path.splitext(filename)[0]

            # 构造 XML 输出文件名
            output_xml_filename = f"{base_filename}.xml"
            output_ca_commit_file_path = os.path.join(OUTPUT_DIR, output_xml_filename)
            logging.info(f"正在处理文件: {filename}")

            # 3. 构造 xctrace 命令
            # 原始路径字符串
            raw_input_path = input_file_path
            raw_output_path = output_ca_commit_file_path

            # 对路径中的括号进行转义，以适应 xctrace shell 命令的格式
            escaped_input_path = raw_input_path.replace("(", "\\(").replace(")", "\\)")
            escaped_output_path = raw_output_path.replace("(", "\\(").replace(")", "\\)")

            xctrace_cmd = (
                f"xctrace export --input {escaped_input_path} "
                f"--xpath {xpath_str} "
                f"--output {escaped_output_path}"
            )

            logging.info(f"生成xml中...\n{xctrace_cmd}")

            # 4. 执行命令
            os.system(xctrace_cmd)
            logging.info(f"文件 {output_xml_filename} 生成完成。\n---")


if __name__ == "__main__":
    gen_activitymonitor_all_traces()