import pandas as pd
import os
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# 修改本目录，此处使用就好了
BASE_DIR = "/Users/clover/Result0421/B5"

# 定义BackgroudLoad进程名映射
BACKGROUND_LOAD_PROCESSES = {
    "QQChess-mobile": "天天爱象棋",
    "guandan": "掼蛋",
    "3d": "途游斗地主（比赛版）",
    "goujigame-mobile": "多乐够级",
    "Passbook": "钱包",
    "QDReaderAppStore": "起点读书",
    "CNRNet_code": "央广网",
    "kugou": "酷狗音乐",
    "SinaNews": "新浪新闻",
    "RedGame": "天天爱消除",
    "IfengNews": "凤凰新闻",
    "sohunews": "搜狐新闻",
    "QTTourAppstore": "蜻蜓FM",
    "lazyaudio": "懒人听书",
    "YYMobile": "YY",
    "cn": "地铁跑酷"
}

# 定义ForegroundAPP/BackgroudAPP进程名映射
FOREGROUND_BACKGROUND_PROCESSES = {
    "58tongcheng": "58同城",
    "AlipayWallet": "支付宝",
    "AMapiPhone": "高德地图",
    "AutoMobile": "懂车帝",
    "Aweme": "抖音",
    "BaiduBoxApp": "百度",
    "bili-universe": "哔哩哔哩",
    "Camera": "相机",
    "com_kwai_gif": "快手",
    "CTRIP_WIRELESS": "携程",
    "DingTalk": "钉钉",
    "discover": "小红书",
    "DPScope": "大众点评",
    "HelloLua": "开心消消乐",
    "homework": "作业帮",
    "IHexin": "同花顺",
    "imeituan": "美团",
    "IphoneCom": "百度地图",
    "iQiYiPhoneVideo": "爱奇艺",
    "JD4iPhone": "京东",
    "kiwi": "虎牙直播",
    "live4iphoneRel": "腾讯视频",
    "MGTV-iPhone-appstore": "芒果tv",
    "MTPotal": "铁路12306",
    "mttlite": "QQ浏览器",
    "MTXX": "美图秀秀",
    "News": "今日头条",
    "OneTravel": "滴滴出行",
    "osee2unifiedRelease": "知乎",
    "pinduoduo": "拼多多",
    "QQ": "QQ",
    "QQMusic": "QQ音乐",
    "QQNews": "腾讯新闻",
    "QunariPhone_Cook_CM": "去哪儿旅行",
    "Reading": "番茄小说",
    "Runner": "闲鱼",
    "SchubertAppStore": "汽水音乐",
    "ShadowTrackerExtra": "和平精英",
    "Sileo": "Sileo",
    "smoba": "王者荣耀",
    "Spec": "唯品会",
    "Study": "学习强国",
    "Taobao4iPhone": "淘宝",
    "ting": "喜马拉雅",
    "UCWEB": "UC浏览器",
    "UmetripFree": "航旅纵横",
    "wallet": "云闪付",
    "WebDriverAgentRunner-Runner": "WDA",
    "WeChat": "微信",
    "Weibo": "微博",
    "wpsoffice": "wpsoffice",
    "Youkui4Phone": "优酷",
    "YYReader": "七猫"
}

def classify_process(process_name, app_name):
    # 首先检查是否是BackgroudLoad
    if process_name == "kernel_task":
        return "KernelTask"

    if process_name in BACKGROUND_LOAD_PROCESSES:
        return "BackgroudLoad"

    # 检查是否在ForegroundAPP/BackgroudAPP列表中
    if process_name in FOREGROUND_BACKGROUND_PROCESSES:
        if FOREGROUND_BACKGROUND_PROCESSES[process_name] == app_name:
            return "ForegroundAPP"
        else:
            return "BackgroudAPP"

    # 其余的都是SystemService
    return "SystemService"

# 读取两个Excel文件
mapping_file = os.path.join(BASE_DIR, "footprint_step.xlsx")
all_file = os.path.join(BASE_DIR, "footprint_all.xlsx")

# 读取footprint_step.xlsx，获取Footprint编号的映射关系
df_mapping = pd.read_excel(mapping_file)
# 创建字典：Footprint编号 -> APP 和 Footprint编号 -> 步骤
footprint_to_app = dict(zip(df_mapping['Footprint编号'], df_mapping['APP']))
footprint_to_step = dict(zip(df_mapping['Footprint编号'], df_mapping['步骤']))

# 读取footprint_all.xlsx
df_all = pd.read_excel(all_file)

# 根据steps列（即Footprint编号）获取对应的APP和步骤
df_all['前台APP'] = df_all['steps'].map(footprint_to_app)
df_all['步骤'] = df_all['steps'].map(footprint_to_step)

# 获取进程名列（原始D列，索引3）
process_col = df_all.columns[3]
app_col = '前台APP'

df_all['proc_typ'] = df_all.apply(
    lambda row: classify_process(row[process_col], row[app_col]),
    axis=1
)

# 调整列顺序：前台APP在B列（索引1），步骤在C列（索引2），proc_typ在proc_name之后
cols = df_all.columns.tolist()

# 移除要调整位置的列
cols.remove('前台APP')
cols.remove('步骤')
cols.remove('proc_typ')

# 找到proc_name的位置
proc_name_idx = cols.index('proc_name')

# 插入到指定位置
cols.insert(1, '前台APP')  # B列
cols.insert(2, '步骤')      # C列
cols.insert(proc_name_idx + 3, 'proc_typ')
df_all = df_all[cols]

# 保存结果
output_file = os.path.join(BASE_DIR, "footprint.xlsx")
df_all.to_excel(output_file, index=False)

# 调整列宽自适应
wb = load_workbook(output_file)
ws = wb.active
for column in ws.columns:
    max_length = 0
    column_letter = get_column_letter(column[0].column)
    for cell in column:
        try:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        except:
            pass
    adjusted_width = min(max_length + 2, 50)  # 最大宽度限制为50
    ws.column_dimensions[column_letter].width = adjusted_width
wb.save(output_file)

print(f"已保存到: {output_file}")
print(f"共处理 {len(df_all)} 行数据")
print(f"分类统计:")
print(df_all['proc_typ'].value_counts())
