import os
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Border, Side
from datetime import datetime, timedelta

# 文件路径
BASE_DIR = "/Users/clover/Result0420/B5"
footprint_file = os.path.join(BASE_DIR, "footprint_step.xlsx")
sysctl_file = os.path.join(BASE_DIR, "sysctl", "sysctl.xlsx")
vmstat_file = os.path.join(BASE_DIR, "vmstat", "vmstat.xlsx")

# 输出文件路径
sysctl_output = os.path.join(BASE_DIR, "sysctl", "sysctl_step.xlsx")
vmstat_output = os.path.join(BASE_DIR, "vmstat", "vmstat_step.xlsx")

def normalize_timestamp(ts):
    """标准化时间戳，只保留到秒级别"""
    if isinstance(ts, datetime):
        return ts.strftime('%Y-%m-%d %H:%M:%S')
    else:
        ts_str = str(ts).strip()
        # 去掉毫秒部分（如果有）
        if '.' in ts_str:
            ts_str = ts_str.split('.')[0]
        return ts_str

def parse_timestamp(ts_str):
    """将时间戳字符串转换为 datetime 对象"""
    try:
        return datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
    except:
        return None

def find_closest_match(target_ts, timestamp_map, max_diff_seconds=10):
    """找到最接近的时间戳匹配（允许最大时间差）"""
    target_dt = parse_timestamp(target_ts)
    if not target_dt:
        return None

    closest_key = None
    min_diff = timedelta(seconds=max_diff_seconds + 1)

    for ts_key in timestamp_map.keys():
        ts_dt = parse_timestamp(ts_key)
        if ts_dt:
            diff = abs(target_dt - ts_dt)
            if diff < min_diff:
                min_diff = diff
                closest_key = ts_key

    # 如果时间差在允许范围内，返回匹配的key
    if closest_key and min_diff <= timedelta(seconds=max_diff_seconds):
        return closest_key
    return None

print("Loading footprint_step.xlsx...")
# 读取 footprint_step.xlsx，提取 B列（负载）、C列（步骤）、E列（步骤时间）
wb_footprint = load_workbook(footprint_file)
ws_footprint = wb_footprint.active

# 构建时间戳到负载和步骤的映射
timestamp_map = {}
for row_idx in range(2, ws_footprint.max_row + 1):  # 从第2行开始（跳过表头）
    load_value = ws_footprint.cell(row=row_idx, column=2).value  # B列：负载
    step_value = ws_footprint.cell(row=row_idx, column=3).value  # C列：步骤
    timestamp_value = ws_footprint.cell(row=row_idx, column=5).value  # E列：步骤时间

    if timestamp_value:
        # 标准化时间戳格式（去掉毫秒）
        timestamp_str = normalize_timestamp(timestamp_value)

        timestamp_map[timestamp_str] = {
            'load': load_value if load_value else '',
            'step': step_value if step_value else ''
        }

print(f"Found {len(timestamp_map)} timestamp mappings")

def adjust_column_width(ws):
    """自动调整列宽"""
    from openpyxl.utils import get_column_letter

    for col_idx in range(1, ws.max_column + 1):
        max_length = 0
        column_letter = get_column_letter(col_idx)

        for row_idx in range(1, ws.max_row + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            try:
                if cell.value:
                    cell_length = len(str(cell.value))
                    if cell_length > max_length:
                        max_length = cell_length
            except:
                pass

        adjusted_width = min(max_length + 2, 50)  # 最大宽度50
        ws.column_dimensions[column_letter].width = adjusted_width

def add_borders(ws):
    """为所有单元格添加网格线"""
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.border = thin_border

def process_file(input_file, output_file, file_type):
    print(f"\nProcessing {file_type}...")
    wb = load_workbook(input_file)
    ws = wb.active

    # 插入新列：在B列和C列位置插入"前台APP"和"步骤"
    ws.insert_cols(2, 2)  # 在第2列位置插入2列

    # 更新表头（检查第1行或第2行）
    header_row = 1
    if ws.cell(row=1, column=1).value == 'timestamp':
        header_row = 1
    elif ws.cell(row=2, column=1).value == 'timestamp':
        header_row = 2

    if header_row:
        ws.cell(row=header_row, column=2, value='前台APP')
        ws.cell(row=header_row, column=3, value='步骤')

    # 遍历数据行，根据时间戳匹配
    matched_count = 0
    start_row = header_row + 1 if header_row else 2

    for row_idx in range(start_row, ws.max_row + 1):
        timestamp_cell = ws.cell(row=row_idx, column=1).value  # A列：时间戳

        if timestamp_cell and timestamp_cell != 'timestamp':
            # 标准化时间戳格式（去掉毫秒）
            timestamp_str = normalize_timestamp(timestamp_cell)

            # 查找最接近的时间戳匹配（允许10秒内的时间差）
            matched_key = find_closest_match(timestamp_str, timestamp_map, max_diff_seconds=5)

            if matched_key:
                ws.cell(row=row_idx, column=2, value=timestamp_map[matched_key]['load'])
                ws.cell(row=row_idx, column=3, value=timestamp_map[matched_key]['step'])
                matched_count += 1

    # 向下填充空白的 B 列和 C 列
    print(f"  Filling empty cells...")
    last_app = None
    last_step = None
    filled_count = 0

    for row_idx in range(start_row, ws.max_row + 1):
        b_val = ws.cell(row=row_idx, column=2).value
        c_val = ws.cell(row=row_idx, column=3).value

        # 如果 B 列为空且有上一个值，填充
        if not b_val and last_app:
            ws.cell(row=row_idx, column=2, value=last_app)
            filled_count += 1
        elif b_val:
            last_app = b_val

        # 如果 C 列为空且有上一个值，填充
        if not c_val and last_step:
            ws.cell(row=row_idx, column=3, value=last_step)
        elif c_val:
            last_step = c_val

    # 添加网格线
    add_borders(ws)

    # 自动调整列宽
    adjust_column_width(ws)

    # 保存新文件
    wb.save(output_file)
    print(f"  Matched {matched_count} rows, filled {filled_count} empty cells")
    print(f"  Saved to {output_file}")

# 处理 sysctl.xlsx
process_file(sysctl_file, sysctl_output, "sysctl.xlsx")

# 处理 vmstat.xlsx
process_file(vmstat_file, vmstat_output, "vmstat.xlsx")

print("\nDone! Generated files:")
print(f"  - {sysctl_output}")
print(f"  - {vmstat_output}")
