import os, re
from openpyxl import Workbook
from openpyxl.styles import Alignment

# 指定sysctl文件所在目录，如果为None则使用当前脚本目录
BASE_DIR = "/Users/clover/Desktop/Result7i/Basic1/mem1"

base = BASE_DIR if BASE_DIR else os.path.dirname(os.path.abspath(__file__))

files = []
for f in os.listdir(base):
    m = re.match(r'^sysctl_(\d+)$', f)
    if m:
        files.append((int(m.group(1)), f))
files.sort(key=lambda x: x[0])
print(f"Found {len(files)} sysctl files")

# 先收集所有的vm.*字段名（保持文件中的顺序）
all_vm_keys = []
vm_keys_set = set()
data_rows = []

for step, fname in files:
    filepath = os.path.join(base, fname)
    vm_data = {'filename': fname, 'step': step, 'timestamp': ''}

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

        # 提取时间戳（通常在文件开头）
        for line in lines[:5]:
            line = line.strip()
            # 匹配时间戳格式: 2026-04-20 09:23:58
            time_match = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
            if time_match:
                vm_data['timestamp'] = time_match.group(1)
                break

        # 解析 vm.* 行（按文件顺序）
        for line in lines:
            line = line.strip()
            if line.startswith('vm.'):
                # 解析 vm.* 行
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    # 特殊处理 vm.loadavg
                    if key == 'vm.loadavg':
                        # 格式: { 3.34 18.81 15.01 }
                        match = re.findall(r'[\d.]+', value)
                        if len(match) >= 3:
                            vm_data['vm.loadavg_1'] = float(match[0])
                            vm_data['vm.loadavg_2'] = float(match[1])
                            vm_data['vm.loadavg_3'] = float(match[2])
                            # 按顺序添加到列表
                            for k in ['vm.loadavg_1', 'vm.loadavg_2', 'vm.loadavg_3']:
                                if k not in vm_keys_set:
                                    all_vm_keys.append(k)
                                    vm_keys_set.add(k)

                    # 特殊处理 vm.swapusage
                    elif key == 'vm.swapusage':
                        # 格式: total = 256.00M  used = 80.75M  free = 175.25M
                        total_match = re.search(r'total\s*=\s*([\d.]+)([KMG])', value)
                        used_match = re.search(r'used\s*=\s*([\d.]+)([KMG])', value)
                        free_match = re.search(r'free\s*=\s*([\d.]+)([KMG])', value)

                        if total_match:
                            vm_data['vm.swapusage_total'] = f"{total_match.group(1)}{total_match.group(2)}"
                        if used_match:
                            vm_data['vm.swapusage_used'] = f"{used_match.group(1)}{used_match.group(2)}"
                        if free_match:
                            vm_data['vm.swapusage_free'] = f"{free_match.group(1)}{free_match.group(2)}"

                        # 按顺序添加到列表
                        for k in ['vm.swapusage_total', 'vm.swapusage_used', 'vm.swapusage_free']:
                            if k not in vm_keys_set:
                                all_vm_keys.append(k)
                                vm_keys_set.add(k)

                    # 其他 vm.* 字段
                    else:
                        vm_data[key] = value
                        if key not in vm_keys_set:
                            all_vm_keys.append(key)
                            vm_keys_set.add(key)

    data_rows.append(vm_data)

    if step % 100 == 0:
        print(f"  Processed step {step}...")

# 创建 Excel 工作簿
wb = Workbook()
ws = wb.active
ws.title = 'vm_sysctl_data'

# 构建两行表头
# 第一行：合并单元格的表头
# 第二行：具体的列名

# 计算列位置
col_idx = 1
header_row1 = [''] * (3 + len(all_vm_keys))  # timestamp, filename, step + vm keys
header_row2 = ['timestamp', 'filename', 'step']

# 记录需要合并的单元格位置
merge_cells = []

col_idx = 4  # 从第4列开始（前3列是 timestamp, filename, step）

for key in all_vm_keys:
    if key.startswith('vm.loadavg_'):
        if key == 'vm.loadavg_1':
            # 记录 vm.loadavg 的起始列
            loadavg_start = col_idx
        if key == 'vm.loadavg_3':
            # 记录 vm.loadavg 的结束列，并添加合并信息
            merge_cells.append(('vm.loadavg', loadavg_start, col_idx))

        # 第二行表头
        if key == 'vm.loadavg_1':
            header_row2.append('1')
        elif key == 'vm.loadavg_2':
            header_row2.append('2')
        elif key == 'vm.loadavg_3':
            header_row2.append('3')

    elif key.startswith('vm.swapusage_'):
        if key == 'vm.swapusage_total':
            # 记录 vm.swapusage 的起始列
            swapusage_start = col_idx
        if key == 'vm.swapusage_free':
            # 记录 vm.swapusage 的结束列，并添加合并信息
            merge_cells.append(('vm.swapusage', swapusage_start, col_idx))

        # 第二行表头
        if key == 'vm.swapusage_total':
            header_row2.append('total')
        elif key == 'vm.swapusage_used':
            header_row2.append('used')
        elif key == 'vm.swapusage_free':
            header_row2.append('free')

    else:
        # 普通字段，两行都显示相同内容
        header_row2.append(key)

    col_idx += 1

# 写入第一行表头（带合并单元格）
ws.append(header_row1)
ws.append(header_row2)

# 合并单元格
for label, start_col, end_col in merge_cells:
    ws.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
    cell = ws.cell(row=1, column=start_col)
    cell.value = label
    cell.alignment = Alignment(horizontal='center', vertical='center')

# 写入数据
for row_data in data_rows:
    row = [row_data.get('timestamp', ''), row_data.get('filename', ''), row_data.get('step', '')]
    for key in all_vm_keys:
        row.append(row_data.get(key, ''))
    ws.append(row)

out = os.path.join(base, 'sysctl.xlsx')
wb.save(out)
print(f"Done! {len(data_rows)} rows -> {out}")
