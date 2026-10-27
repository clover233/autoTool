"""共享默认路径、进程清单及内存分类规则。"""

from pathlib import Path

DEFAULT_RESULT_DIR = Path('/Users/clover/Desktop/SeaOfStars7i/Result/result1')
DEFAULT_VMSTATS_INPUT = DEFAULT_RESULT_DIR / 'vmstats.log'
MIB = 1024 * 1024
ACTIVITY_SCHEMA = 'activity-monitor-process-live'
HITCH_SCHEMA = 'hitches'

APPS = {
    'AlipayWallet': '支付宝', 'AMapiPhone': '高德地图', 'BaiduBoxApp': '百度',
    'IphoneCom': '百度地图', 'MobileNotes': '备忘录', 'bili-universal': '哔哩哔哩',
    'MobilePhone': '电话', 'Camera': '相机', 'wallet': '云闪付',
    'neteasemusic': '网易云音乐', 'DPScope': '大众点评', 'DeepSeek Chat': 'DeepSeek',
    'AwemeLite': '抖音极速版', 'client': '蛋仔派对', 'MiHome': '米家',
    'MomoChat': 'MOMO陌陌', 'TapTap': 'TapTap', 'AigcBot_iOS': '腾讯元宝',
    'OneTravel': '滴滴出行', 'DingTalk': '钉钉', 'AutoMobile': '懂车帝',
    'Grace': '豆包', 'Aweme': '抖音', 'Reading': '番茄免费小说', 'XSFM': '番茄畅听',
    'HelloLua': '开心消消乐', 'ShadowTrackerExtra': '和平精英', 'Eggplant': '红果免费短剧',
    'HuaweiWear': '华为运动健康', 'Vmall_iOS': '华为商城', 'JD4iPhone': '京东',
    'News': '今日头条', 'com_kwai_gif': '快手', 'imeituan': '美团',
    'MTXX': '美图秀秀', 'MobileSMS': '信息', 'MobileSlideShow': '照片',
    'pinduoduo': '拼多多', 'Qwen': '千问', 'YYReader': '七猫免费小说',
    'iQiYiPhoneVideo': '爱奇艺', 'QQ': 'QQ', 'mttlite': 'QQ浏览器',
    'QQMusic': 'QQ音乐', 'QunariPhone_Cook_CM': '去哪儿旅行', 'Preferences': '设置',
    'SchubertAppStore': '汽水音乐', 'Taobao4iPhone': '淘宝', 'QQNews': '腾讯新闻',
    'live4iphoneRel': '腾讯视频', 'IHexin': '同花顺', 'MTPotal': '铁路12306',
    'UCWEB': 'UC浏览器', 'smoba': '王者荣耀', 'Weather': '天气',
    'Weibo': '微博', 'Spec': '唯品会', 'WeChat': '微信', 'wpsoffice': 'WPS Office',
    'discover': '小红书', 'Runner': '闲鱼', 'CTRIP_WIRELESS': '携程旅行',
    'Youkui4Phone': '优酷', 'osee2unifiedRelease': '知乎', 'homework': '作业帮',
}
LOAD_APPS = {
    'qqchess-mobile': '天天爱象棋', 'guandan': '掼蛋', 'unityhall': '途游斗地主（比赛版）',
    'goujigame-mobile': '多乐够级', 'Passbook': '钱包', 'QDReaderAppStore': '起点读书',
    'CNRNet_code': '央广网', 'kugou': '酷狗音乐', 'SinaNews': '新浪新闻',
    'RedGame': '天天爱消除', 'IfengNews': '凤凰新闻', 'sohunews': '搜狐新闻',
    'QTTourAppStore': '蜻蜓FM', 'lazyaudio': '懒人听书', 'YYMobile': 'YY', 'cn': '地铁跑酷',
}
CATEGORIES = ['ForegroundAPP', 'BackgroudAPP', 'BackgroudLoad', 'SystemService']

IOS_PACKAGES_MAP = {**APPS, **LOAD_APPS}
GRAPH_PROCESS = ['backboardd']
DESK_PROCESS = ['SpringBoard']
INPUT_PROCESS = ['InputUI', 'inputanalyticsd']
SERVICE_IGNORED = ['WebDriverAgentRunner-Runner', 'DTServiceHub']


def app_for_process(process):
    return LOAD_APPS.get(process, APPS.get(process))


def classify_process(process, foreground):
    # 保留历史报表中的 Backgroud 拼写，避免影响下游字段匹配。
    if process in LOAD_APPS:
        return 'BackgroudLoad'
    if process in APPS:
        return 'ForegroundAPP' if APPS[process] == foreground else 'BackgroudAPP'
    return 'SystemService'


def bytes_to_mb(memory):
    return round(memory / MIB, 1)
