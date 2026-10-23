import os, re
from openpyxl import Workbook

# 指定vmstat文件所在目录，如果为None则使用当前脚本目录
BASE_DIR = "/Users/clover/Desktop/Result7i/Basic3/mem3"

base = BASE_DIR if BASE_DIR else os.path.dirname(os.path.abspath(__file__))

files = []
for f in os.listdir(base):
    m = re.match(r'^vmstatlog_(\d+)$', f)
    if m:
        files.append((int(m.group(1)), f))
files.sort(key=lambda x: x[0])
print(f"Found {len(files)} vmstat files")

# 先收集所有的字段名（保持文件中的顺序）
all_keys = []
keys_set = set()
data_rows = []

for step, fname in files:
    filepath = os.path.join(base, fname)
    vmstat_data = {'filename': fname, 'step': step, 'timestamp': ''}

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

        # 提取时间戳（通常在文件第一行）
        if lines:
            first_line = lines[0].strip()
            # 匹配时间戳格式: 2026-04-20 09:23:58
            time_match = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', first_line)
            if time_match:
                vmstat_data['timestamp'] = time_match.group(1)

        # 解析每一行数据（按文件顺序）
        for line in lines:
            line = line.strip()
            # 跳过空行和标题行
            if not line or line.startswith('Mach Virtual Memory Statistics'):
                continue

            # 解析格式: "Pages free:                                1207."
            # 或: "\"Translation faults\":                  18003873."
            match = re.match(r'^["\']?([^"\']+?)["\']?\s*:\s+(.+?)\.?$', line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip().rstrip('.')

                # 存储数据
                vmstat_data[key] = value

                # 按顺序添加到列表
                if key not in keys_set:
                    all_keys.append(key)
                    keys_set.add(key)

    data_rows.append(vmstat_data)

    if step % 100 == 0:
        print(f"  Processed step {step}...")

# 创建 Excel 工作簿
wb = Workbook()
ws = wb.active
ws.title = 'vmstat_data'

# 构建表头
headers = ['timestamp', 'filename', 'step'] + all_keys
ws.append(headers)

# 写入数据
for row_data in data_rows:
    row = [row_data.get('timestamp', ''), row_data.get('filename', ''), row_data.get('step', '')]
    for key in all_keys:
        row.append(row_data.get(key, ''))
    ws.append(row)

out = os.path.join(base, 'vmstat.xlsx')
wb.save(out)
print(f"Done! {len(data_rows)} rows -> {out}")
