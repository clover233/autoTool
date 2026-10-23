import json, os, re
from openpyxl import Workbook
from datetime import datetime

# 指定footprint文件所在目录，如果为None则使用当前脚本目录
BASE_DIR = "/Users/clover/Desktop/paizhao"

base = BASE_DIR if BASE_DIR else os.path.dirname(os.path.abspath(__file__))

files = []
for f in os.listdir(base):
    m = re.match(r'^footprint_(\d+)\.json$', f)
    if m:
        files.append((int(m.group(1)), f))
files.sort(key=lambda x: x[0])
print(f"Found {len(files)} JSON files")

wb = Workbook()
ws = wb.active
ws.title = '全量原始数据'
headers = ['timestamp', 'filename', 'steps', 'proc_name', 'pid',
           'footprint（MB）', 'Dirty(MB)', 'Swapped(MB)',
           'Clean(MB)', 'Reclaimable(MB)', 'wired（MB）',
           'Clean（MB）+ footprint(MB)', 'Clean（MB）+ footprint(MB) - wired（MB）']
ws.append(headers)

MB = 1024 * 1024
row_count = 0

for step, fname in files:
    with open(os.path.join(base, fname)) as f:
        data = json.load(f)

    basename = fname.replace('.json', '')
    # 提取时间戳并格式化为 hh:mm:ss.xxx 原格式: "2026-04-20T09:24:00.058+08:00"
    timestamp = ''
    if 'start_time' in data and 'date' in data['start_time']:
        try:
            date_str = data['start_time']['date']
            if 'T' in date_str:
                time_part = date_str.split('T')[1]
                if '+' in time_part:
                    timestamp = time_part.split('+')[0]
                elif '-' in time_part and time_part.count('-') == 1:
                    timestamp = time_part.split('-')[0]
                else:
                    timestamp = time_part
        except Exception as e:
            print(f"Warning: Failed to parse date from start_time: {e}")
            timestamp = ''

    for proc in data.get('processes', []):
        cats = proc.get('categories', {})
        footprint = round(proc.get('footprint', 0) / MB, 2)
        dirty = round(sum(c.get('dirty', 0) for c in cats.values()) / MB, 2)
        swapped = round(sum(c.get('swapped', 0) for c in cats.values()) / MB, 2)
        clean = round(sum(c.get('clean', 0) for c in cats.values()) / MB, 2)
        reclaimable = round(sum(c.get('reclaimable', 0) for c in cats.values()) / MB, 6)
        wired = round(sum(c.get('wired', 0) for c in cats.values()) / MB, 2)

        clean_plus_fp = round(clean + footprint, 2)
        clean_plus_fp_minus_wired = round(clean + footprint - wired, 2)

        ws.append([timestamp, basename, str(step), proc.get('name', ''), str(proc.get('pid', '')),
                   footprint, dirty, swapped, clean, reclaimable, wired,
                   clean_plus_fp, clean_plus_fp_minus_wired])
        row_count += 1

    if step % 100 == 0:
        print(f"  Processed step {step}...")

out = os.path.join(base, 'footprint_all.xlsx')
wb.save(out)
print(f"Done! {row_count} rows -> {out}")
