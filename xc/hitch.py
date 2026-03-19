import re
import xml.etree.ElementTree as ET
import os
import logging
import csv
import time
import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logging.getLogger("matplotlib.font_manager").disabled = True
formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(sh)


def parse_hitches_summary(hitches_summary_xml_path):
    all_result = []
    if os.path.exists(hitches_summary_xml_path):
        dom = ET.parse(hitches_summary_xml_path)
        root = dom.getroot()
        id_map = {}
        all_id = root.findall(".//*[@id]")
        for per_id in all_id:
            id_map[per_id.get("id")] = per_id
        row = root.findall(".//row")

        for per_row in row:
            if per_row.findall("process"):
                result = {"start-time": -1, "process": "None", "process_name": "None", "hitches_timeduration": -1}

                duration_obj = per_row.findall("duration")[0] if "id" in per_row.findall("duration")[
                    0].attrib.keys() else \
                    id_map[per_row.findall("duration")[0].attrib["ref"]]

                process_obj = per_row.findall("process")[0] if "id" in per_row.findall("process")[0].attrib.keys() else \
                    id_map[per_row.findall("process")[0].attrib["ref"]]

                start_time_obj = per_row.findall("start-time")[0] if "id" in per_row.findall("start-time")[
                    0].attrib.keys() else \
                    id_map[per_row.findall("start-time")[0].attrib["ref"]]

                result["hitches_timeduration"] = duration_obj.attrib["fmt"]
                result["start-time"] = start_time_obj.attrib["fmt"]
                result["process"] = process_obj.attrib["fmt"]
                result["process_name"] = process_obj.attrib["fmt"].split("(")[0]

                all_result.append(result)
    else:
        logging.error("Trace有问题,{}未生成".format(hitches_summary_xml_path))
    return all_result


def parse_all_xml(hitches_summary_file_path):
    all_summary_result = parse_hitches_summary(hitches_summary_file_path)
    return all_summary_result


def gen_xml(trace_file, is_regen_xml=True):
    dir_name, full_file_name = os.path.split(trace_file)
    file_base_name, file_ext = os.path.splitext(full_file_name)

    input_file_path = trace_file
    xpath_str = "'/trace-toc/run[@number=\"1\"]/data/table[@schema=\"hitches\"]'"
    hitches_summary_file_path = os.path.join(dir_name, file_base_name) + "_hitches_summary.xml"

    if os.path.exists(hitches_summary_file_path):
        logging.debug("xml文件已存在：{}".format(hitches_summary_file_path))

    for i in range(0, 3):
        if not os.path.exists(hitches_summary_file_path) or os.path.getsize(hitches_summary_file_path) < 100:
            if os.path.exists(hitches_summary_file_path):
                print("hitches_summary_file_path:", hitches_summary_file_path, " size:",
                      os.path.getsize(hitches_summary_file_path))
            xctrace_cmd = r"xctrace export --input {} --xpath {} --output {}".format(input_file_path, xpath_str,
                                                                                     hitches_summary_file_path)
            xctrace_cmd = xctrace_cmd.replace("(", "\\(")
            xctrace_cmd = xctrace_cmd.replace(")", "\\)")
            logging.info("生成xml中...\n{}".format(xctrace_cmd))
            os.system(xctrace_cmd)
        else:
            break

    return hitches_summary_file_path


def gen_result(all_trace_file, is_just_genxml=False):
    success_trace_count = 0
    all_summary = []

    for per_trace_file in all_trace_file:
        hitches_summary_file_path = gen_xml(per_trace_file)
        summary_result = parse_all_xml(hitches_summary_file_path)

        for i in summary_result:
            all_summary.append(i)

    df = pd.DataFrame(all_summary)
    df.to_csv('summary.csv', index=False, encoding='utf-8')

def run(result_dir_path):
    all_trace_file = []
    for main_dir, dirs, file_name_list in os.walk(result_dir_path):
        if main_dir[-6:] == ".trace":
            all_trace_file.append(main_dir)
    all_trace_file.sort()
    gen_result(all_trace_file, False)


if __name__ == "__main__":
    run("/Users/clover/Desktop/Basic1")