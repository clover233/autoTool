#!/usr/bin/env python3
"""Insert proc_type between F and G in the three footprint workbooks.

Uses only Python's standard library and processes worksheet rows incrementally,
so the large source workbooks do not need to fit in memory.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile


LOAD_APPS = {
    "qqchess-mobile": "天天爱象棋", "guandan": "掼蛋", "unityhall": "途游斗地主（比赛版）",
    "goujigame-mobile": "多乐够级", "Passbook": "钱包", "QDReaderAppStore": "起点读书",
    "CNRNet_code": "央广网", "kugou": "酷狗音乐", "SinaNews": "新浪新闻",
    "RedGame": "天天爱消除", "IfengNews": "凤凰新闻", "sohunews": "搜狐新闻",
    "QTTourAppStore": "蜻蜓FM", "lazyaudio": "懒人听书", "YYMobile": "YY",
    "cn": "地铁跑酷",
}

APPS = {
    "AlipayWallet": "支付宝", "AMapiPhone": "高德地图", "BaiduBoxApp": "百度",
    "IphoneCom": "百度地图", "MobileNotes": "备忘录", "bili-universal": "哔哩哔哩",
    "MobilePhone": "电话", "Camera": "相机", "wallet": "云闪付",
    "neteasemusic": "网易云音乐", "DPScope": "大众点评", "DeepSeek Chat": "DeepSeek",
    "AwemeLite": "抖音极速版", "client": "蛋仔派对", "MiHome": "米家",
    "MomoChat": "MOMO陌陌", "TapTap": "TapTap", "AigcBot_iOS": "腾讯元宝",
    "OneTravel": "滴滴出行", "DingTalk": "钉钉", "AutoMobile": "懂车帝",
    "Grace": "豆包", "Aweme": "抖音", "Reading": "番茄免费小说",
    "XSFM": "番茄畅听", "HelloLua": "开心消消乐",
    "ShadowTrackerExtra": "和平精英", "Eggplant": "红果免费短剧",
    "HuaweiWear": "华为运动健康", "Vmall_iOS": "华为商城",
    "JD4iPhone": "京东", "News": "今日头条", "com_kwai_gif": "快手",
    "imeituan": "美团", "MTXX": "美图秀秀", "MobileSMS": "信息",
    "MobileSlideShow": "照片", "pinduoduo": "拼多多", "Qwen": "千问",
    "YYReader": "七猫免费小说", "iQiYiPhoneVideo": "爱奇艺", "QQ": "QQ",
    "mttlite": "QQ浏览器", "QQMusic": "QQ音乐",
    "QunariPhone_Cook_CM": "去哪儿旅行", "Preferences": "设置",
    "SchubertAppStore": "汽水音乐", "Taobao4iPhone": "淘宝",
    "QQNews": "腾讯新闻", "live4iphoneRel": "腾讯视频",
    "IHexin": "同花顺", "MTPotal": "铁路12306", "UCWEB": "UC浏览器",
    "smoba": "王者荣耀", "Weather": "天气", "Weibo": "微博",
    "Spec": "唯品会", "WeChat": "微信", "wpsoffice": "WPS Office",
    "discover": "小红书", "Runner": "闲鱼", "CTRIP_WIRELESS": "携程旅行",
    "Youkui4Phone": "优酷", "osee2unifiedRelease": "知乎", "homework": "作业帮",
}

SHEET_PATH = "xl/worksheets/sheet1.xml"
CELL_RE = re.compile(rb'<c\b[^>]*\br="([A-Z]+)(\d+)"[^>]*>.*?</c>')
VALUE_RE = re.compile(rb'<v>(.*?)</v>')
TYPE_RE = re.compile(rb'\bt="([^"]+)"')
REF_RE = re.compile(rb'(?<=\br=")([A-Z]+)(\d+)(?=")')
ROW_END = b"</row>"


def col_number(name: str) -> int:
    result = 0
    for char in name:
        result = result * 26 + ord(char) - 64
    return result


def col_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def shift_ref(match: re.Match[bytes]) -> bytes:
    name = match.group(1).decode("ascii")
    if col_number(name) < 7:
        return match.group(0)
    return (col_name(col_number(name) + 1) + match.group(2).decode("ascii")).encode("ascii")


def shared_strings(book: ZipFile) -> list[str]:
    result: list[str] = []
    with book.open("xl/sharedStrings.xml") as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag.endswith("}si"):
                result.append("".join(element.itertext()))
                element.clear()
    return result


def cell_text(cell: bytes, strings: list[str]) -> str:
    match = VALUE_RE.search(cell)
    if match is None:
        return ""
    value = match.group(1).decode("utf-8")
    if (kind := TYPE_RE.search(cell.split(b">", 1)[0])) and kind.group(1) == b"s":
        return strings[int(value)]
    return value


def classify(proc_name: str, foreground_app: str) -> str:
    if proc_name in LOAD_APPS:
        return "BackgroudLoad"
    if proc_name in APPS:
        return "ForegroundAPP" if foreground_app == APPS[proc_name] else "BackgroudAPP"
    return "SystemService"


def update_prefix(prefix: bytes) -> bytes:
    if b'<dimension ref="A1:O' not in prefix:
        raise ValueError("Unexpected worksheet dimension")
    prefix = prefix.replace(b'<dimension ref="A1:O', b'<dimension ref="A1:P', 1)

    def shift_col(match: re.Match[bytes]) -> bytes:
        n = int(match.group(1))
        return b'min="' + str(n + (n >= 7)).encode() + b'" max="' + str(n + (n >= 7)).encode() + b'"'

    prefix = re.sub(rb'min="(\d+)" max="\1"', shift_col, prefix)
    if b"</cols>" in prefix:
        new_col = b'<col min="7" max="7" width="18" customWidth="1"/>'
        first_shifted = prefix.find(b'<col min="8"')
        if first_shifted >= 0:
            prefix = prefix[:first_shifted] + new_col + prefix[first_shifted:]
        else:
            prefix = prefix.replace(b"</cols>", new_col + b"</cols>", 1)
    return prefix


def update_row(row: bytes, strings: list[str], counts: Counter[str]) -> bytes:
    row_number_match = re.match(rb'<row\b[^>]*\br="(\d+)"', row)
    if row_number_match is None:
        raise ValueError("Worksheet row has no row number")
    row_number = row_number_match.group(1)
    cells = list(CELL_RE.finditer(row))
    values = {match.group(1): cell_text(match.group(0), strings)
              for match in cells if match.group(1) in (b"D", b"F")}
    if row_number == b"1":
        if values.get(b"D") != "前台应用" or values.get(b"F") != "proc_name":
            raise ValueError("D/F headers differ from expected source layout")
        category = "proc_type"
    else:
        category = classify(values.get(b"F", ""), values.get(b"D", ""))
        counts[category] += 1
    if b"<f" in row:
        raise ValueError(f"Formula found in row {row_number.decode()}; reference shifting needs review")

    # Insert the new cell immediately after F; rename original G:O to H:P.
    new_cell = (b'<c r="G' + row_number + b'" t="inlineStr"><is><t>'
                + category.encode("utf-8") + b'</t></is></c>')
    insertion = next((m.end() for m in cells if m.group(1) == b"F"), None)
    if insertion is None:
        raise ValueError(f"Missing F cell in row {row_number.decode()}")
    before = row[:insertion]
    after = REF_RE.sub(shift_ref, row[insertion:])
    before = re.sub(rb'\bspans="1:15"', b'spans="1:16"', before, count=1)
    return before + new_cell + after


def transform_sheet(source, target, strings: list[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    buffer = b""
    prefix_written = False
    while chunk := source.read(1024 * 1024):
        buffer += chunk
        if not prefix_written:
            start = buffer.find(b"<row ")
            if start < 0:
                continue
            target.write(update_prefix(buffer[:start]))
            buffer = buffer[start:]
            prefix_written = True
        while (end := buffer.find(ROW_END)) >= 0:
            end += len(ROW_END)
            row, buffer = buffer[:end], buffer[end:]
            if not row.startswith(b"<row "):
                raise ValueError("Unexpected worksheet XML between rows")
            target.write(update_row(row, strings, counts))
    if not prefix_written:
        raise ValueError("No worksheet rows found")
    target.write(buffer)
    return counts


def process(source: Path, destination: Path) -> Counter[str]:
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths must differ")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(source) as original, ZipFile(destination, "w") as output:
        strings = shared_strings(original)
        counts: Counter[str] = Counter()
        for member in original.infolist():
            if member.filename == SHEET_PATH:
                with original.open(member) as inp, output.open(member, "w", force_zip64=True) as out:
                    counts = transform_sheet(inp, out, strings)
            else:
                output.writestr(member, original.read(member))
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="Input .xlsx files")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    files = args.files or [
        Path(f"/Users/clover/Desktop/Result7i/Result/basic{i}/footprint_all{i}.xlsx")
        for i in (1, 2, 3)
    ]
    for source in files:
        destination = args.output_dir / f"{source.stem}_proc_type.xlsx"
        counts = process(source, destination)
        print(f"{destination}: {sum(counts.values())} data rows; {dict(counts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
