import json
import os
import re
import bisect
from datetime import datetime
from openpyxl import Workbook

# 修改本目录，此处使用就好了
BASE_DIR = "/Users/clover/Result0420/B5"

# Manual mapping for scripts without iTrace or ambiguous
MANUAL_MAP = {
    # "": "",
    "58city": "58同城",
    "Alipay": "支付宝",
    "AutoNavi": "高德地图",
    "Baidu": "百度",
    "Baidumap": "百度地图",
    "Bilibili": "哔哩哔哩",
    "Camera": "相机",
    "CloudFlashPay": "云闪付",
    "dazhongdianping": "大众点评",
    "didichuxing": "滴滴出行",
    "Dingding": "钉钉",
    "Dongchedi": "懂车帝",
    "Douyin": "抖音",
    "fanqie": "番茄小说",
    "hanglvzongheng": "航旅纵横",
    "hepingjingying": "和平精英",
    "jingdong": "京东",
    "jrtt": "今日头条",
    "kiwi": "虎牙直播",
    "Kuaishou": "快手",
    "mangguoTV": "芒果tv",
    "meituan": "美团",
    "meituxiuxiu": "美图秀秀",
    "pinduoduo": "拼多多",
    "qimao": "七猫小说",
    "qiyi": "爱奇艺",
    "qq": "QQ",
    "qqliulanqi": "QQ浏览器",
    "qqm": "QQ音乐",
    "qunaer": "去哪儿",
    "sodamusic": "汽水音乐",
    "tencentnews": "腾讯新闻",
    "TencentVideo": "腾讯视频",
    "ths": "同花顺",
    "tielu12306": "铁路12306",
    "UC": "UC浏览器",
    "wangzherongyao": "王者荣耀",
    "Weibo": "微博",
    "weipinhui": "唯品会",
    "weixin": "微信",
    "wpsoffice": "wpsoffice",
    "xhs": "小红书",
    "xianyu": "闲鱼",
    "xiechengTrip": "携程",
    "ximalaya": "喜马拉雅",
    "xuexiqiangguo": "学习强国",
    "zhihu": "知乎",
    "zhongzai": "重载",
    "zuoyebang": "作业帮"
}

# 1. Parse all_log.txt
itrace_pattern = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*iTrace\.py.*trace 同步日志内容 \[(.+?)\]\[(.+?)\]"
)
perf_pattern = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*PerformanceDynamic_(\w+)_\d+\.py.*INFO: (.+)"
)
setup_pattern = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*PerformanceDynamic_(\w+)_\d+\.py.*INFO: 测试环境开始准备"
)

itrace_events = []
perf_events = []
setups = []

with open(os.path.join(BASE_DIR, "all_log.txt"), "r", encoding="utf-8") as f:
    for line in f:
        m = itrace_pattern.match(line)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S,%f")
            itrace_events.append((ts, m.group(2), m.group(3)))
            continue

        m = setup_pattern.match(line)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S,%f")
            setups.append((ts, m.group(2)))
            continue

        m = perf_pattern.match(line)
        if m:
            step_info = m.group(3)
            if step_info in ("测试环境开始准备", "用例开始执行", "用例执行结束"):
                continue
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S,%f")
            perf_events.append((ts, m.group(2), step_info))

# 2. Build script_name -> app_name: use iTrace within test case window, fallback to MANUAL_MAP
script_to_app_by_window = {}
for i, (ts, name) in enumerate(setups):
    next_ts = setups[i + 1][0] if i + 1 < len(setups) else datetime.max
    for it_ts, it_app, _ in itrace_events:
        if ts <= it_ts < next_ts:
            script_to_app_by_window[(i, name)] = it_app
            break

# For each perf_event, find which setup window it belongs to, then get APP name
def get_app_for_perf(ts, script_name):
    # Find the setup window this perf event belongs to
    best_idx = -1
    for i, (setup_ts, sname) in enumerate(setups):
        if setup_ts <= ts:
            best_idx = i
        else:
            break
    if best_idx >= 0:
        key = (best_idx, setups[best_idx][1])
        if key in script_to_app_by_window:
            return script_to_app_by_window[key]
    return MANUAL_MAP.get(script_name, script_name)

# 3. Build unified step list
itrace_ts_set = {ts for ts, _, _ in itrace_events}

log_steps = list(itrace_events)
for ts, script_name, step_info in perf_events:
    has_itrace = any(abs((ts - it).total_seconds()) < 0.05 for it in itrace_ts_set)
    if not has_itrace:
        app_name = get_app_for_perf(ts, script_name)
        log_steps.append((ts, app_name, step_info))

log_steps.sort(key=lambda x: x[0])
print(f"Total step events: {len(log_steps)}")

# 4. Read all footprint files
footprints = []
import glob
footprint_files = glob.glob(os.path.join(BASE_DIR, "footprint_*.json"))
for fp_path in footprint_files:
    filename = os.path.basename(fp_path)
    match = re.match(r"footprint_(\d+)\.json", filename)
    if not match:
        continue
    i = int(match.group(1))
    try:
        with open(fp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        date_str = data["start_time"]["date"]
        dt = datetime.fromisoformat(date_str).replace(tzinfo=None)
        footprints.append((i, dt))
    except Exception as e:
        print(f"Error reading {filename}: {e}")

footprints.sort(key=lambda x: x[1])
print(f"Parsed {len(footprints)} footprint files")

# 5. Match each footprint to the most recent step
step_times = [s[0] for s in log_steps]

wb = Workbook()
ws = wb.active
ws.title = "Footprint步骤对应"
ws.append(["Footprint编号", "APP", "步骤", "Footprint时间", "步骤时间"])

for fp_num, fp_time in footprints:
    idx = bisect.bisect_right(step_times, fp_time) - 1
    if idx >= 0:
        step_ts, app, step = log_steps[idx]
        ws.append([fp_num, app, step,
                   fp_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                   step_ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]])
    else:
        ws.append([fp_num, "", "（无对应步骤）",
                   fp_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], ""])

output_path = os.path.join(BASE_DIR, "footprint_step.xlsx")
wb.save(output_path)
print(f"Excel saved to: {output_path}")
