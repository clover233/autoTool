import glob
import re
import sys

from openpyxl import Workbook

# 指定文件所在目录，如果为None则使用命令行参数或当前目录
BASE_DIR = "/Users/clover/Result0420/B5/vmstat"


def parse_vmstatlog(filepath):
    stored = None
    occupied = None
    with open(filepath) as f:
        for line in f:
            if "Pages stored in compressor:" in line:
                stored = int(re.search(r"(\d+)", line.split(":")[-1]).group(1))
            elif "Pages occupied by compressor:" in line:
                occupied = int(re.search(r"(\d+)", line.split(":")[-1]).group(1))
    return stored, occupied


def main():
    directory = BASE_DIR if BASE_DIR else (sys.argv[1] if len(sys.argv) > 1 else ".")
    files = sorted(glob.glob(f"{directory}/vmstatlog_*"),
                   key=lambda f: int(f.rsplit("_", 1)[1]))

    wb = Workbook()
    ws = wb.active
    ws.title = "ComRatio"
    ws.append(["File", "Stored", "Occupied", "Ratio"])

    ratios = []

    for filepath in files:
        stored, occupied = parse_vmstatlog(filepath)
        name = filepath.rsplit("/", 1)[-1]
        if stored is not None and occupied is not None and occupied > 0:
            ratio = stored / occupied
            ratios.append(ratio)
            ws.append([name, stored, occupied, ratio])
        else:
            ws.append([name, "N/A", "N/A", "N/A"])

    # Append average row
    if ratios:
        avg_ratio = sum(ratios) / len(ratios)
        ws.append([])
        ws.append(["Average", "", "", avg_ratio])

    output_path = f"{directory}/comratio.xlsx"
    wb.save(output_path)
    print(f"Saved to {output_path} ({len(files)} files, avg ratio: {avg_ratio:.4f})" if ratios else f"Saved to {output_path} ({len(files)} files, no valid data)")


if __name__ == "__main__":
    main()
