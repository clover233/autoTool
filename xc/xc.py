import math
import os
import re
import bisect
from datetime import datetime, timedelta
import pandas as pd
import xml.etree.ElementTree as ET

IOS_PACKAGES_MAP = {
    'QunariPhone_Cook_CM': '去哪儿',
    'Taobao4iPhone': '淘宝',
    'zhaopin': '智联招聘',
    'WeChat': '微信',
    'rls.com.eastmoney.iphone': '东方财富',
    'Zhixing': '智行火车票',
    'QTTourAppStore': '蜻蜓FM',
    'AMapiPhone': '高德地图',
    'AMapiPhoneHomeWidgetExtension': '高德地图',
    'BitAutoPlusStore': '易车',
    'CTRIP_WIRELESS': '携程旅行',
    'kugou': '酷狗',
    'CMBCPersonBank': '民生银行',
    'CNRNet_code': '央广网',
    'IHexin': '同花顺',
    'Anjuke': '安居客',
    'jiaxiaozhijia-ios': '驾校一点通',
    '央视影音': '央视影音',
    'sohunews': '搜狐新闻',
    'MPBBank': '招商',
    'Frodo': '豆瓣',
    'AlipayWallet': '支付宝',
    'lazyaudio': '懒人听书',
    'ThePaperBase': '澎湃新闻',
    'tztMobileApp_zxsc2.0': '中信证券',
    'imeituan': '美团',
    'rls.com.eastmoney.qihuokaihu': '东方财富期货',
    'DPScope': '大众点评',
    'JD4iPhone': '京东',
    'MGTV-iPhone-appstore': '芒果',
    'QQ': 'qq',
    'Weibo': '新浪微博',
    'QQMusic': 'qq音乐',
    'com.apple.Safari.SafeBrowsing.Service': '浏览器',
    'peopled': '人民网+',
    'AppStore': '应用商城',
    'MobileCal': '拨号',
    'MobileSMS': '短信',
    'GTGJ2': '高铁管家',
    'iQiYiPhoneVideo': '爱奇艺',
    'MTXX': '美图',
    'live4iphoneRel': '腾讯视频',
    'bili-universal': '哔哩哔哩',
    'discover': '小红书',
    'Aweme': '抖音',
    'akd': '支付宝',
    'neteasemusic': '网易云音乐',
    'Spec': '唯品会',
    'tingWidgetExtension': '喜马拉雅',
    'WeChatNotificationServiceExtension': '微信',
    'Baby_Recommend': '宝宝巴士',
    'com_kwai_gif': '快手',
    'HelloLua': '开心消消乐',
    'imeituanLiveActivity': '美团',
    'News': '今日头条',
    'OneTravel': '滴滴出行',
    'osee2unifiedRelease': '知乎',
    'smoba': '王者荣耀',
    'ting': '喜马拉雅',
    'YoukuDynamicIslandExtension': '优酷',
    'Youkui4Phone': '优酷',
    'zhuanzhuan': '转转',
    'TMT80': '钛媒体',
    'recipe': '下厨房',
    'AutoMobile': '懂车帝',
    'SinaNews': '新浪新闻'}

GRAPH_PROCESS = ['backboardd']
DESK_PROCESS = ['SpringBoard']
INPUT_PROCESS = ['InputUI', 'inputanalyticsd']
SERVICE_IGNORED = ['WebDriverAgentRunner-Runner', 'DTServiceHub']


def bytes_to_mb(mem):
    return round(mem / 1024 / 1024, 1)


class XCTraceXMLParser:
    def __init__(self, xml_path, schema_columns=[]):
        self.xml_path = xml_path
        self.schema_columns = schema_columns
        self.tree = None
        self.root = None
        self.records = []
        self.id_map = {}
        self.schema = {}

    def parse(self):
        try:
            self.tree = ET.parse(self.xml_path)
            self.root = self.tree.getroot()
            table_node = self.root.find('.//node')
            if table_node is None:
                print("未找到node节点")
                return
            schema_node = table_node.find('.//schema')
            if schema_node is not None:
                self.parse_schema(schema_node)

            rows = table_node.findall('.//row')
            if not rows:
                print("未找到行数据")
                return

            # 先构建ID引用映射
            self.build_id_map(rows)

            # 解析每一行
            for row in rows:
                record = self.parse_row(row)
                if record:
                    self.records.append(record)

            with pd.ExcelWriter(self.xml_path.replace('.xml', '_res.xlsx')) as xlsx:
                pd.DataFrame(self.records).to_excel(xlsx, sheet_name='xctrace数据')

        except Exception as e:
            print(e)

    def parse_schema(self, schema_node: ET.Element):
        """解析表格schema"""
        columns = schema_node.findall('.//col')
        for col in columns:
            mnemonic = col.find('mnemonic').text
            name = col.find('name').text
            eng_type = col.find('engineering-type').text
            self.schema[mnemonic] = {'name': name, 'type': eng_type}

        print(f"解析了 {len(self.schema)} 个数据列")

    def build_id_map(self, rows: list[ET.Element]):
        """构建ID引用映射，处理ref引用"""
        id_map = {}

        for row in rows:
            # 查找所有有id属性的元素
            for elem in row.iter():
                elem_id = elem.get('id')
                if elem_id:
                    # 存储元素的文本值和fmt属性
                    id_map[elem_id] = {
                        'text': elem.text or '',
                        'fmt': elem.get('fmt', ''),
                        'tag': elem.tag
                    }
        self.id_map = id_map

    def parse_row(self, row: ET.Element):
        """解析单行数据"""
        try:
            # 获取所有子元素，按顺序对应schema中的列
            children = list(row)

            # 初始化数据字典
            row_data = {}

            # 处理每一列
            for i, child in enumerate(children):
                # 根据schema确定列名
                if i < len(self.schema):
                    col_name = list(self.schema.keys())[i]
                    if len(self.schema_columns) > 0 and col_name not in self.schema_columns:
                        continue
                    value = self.parse_element(child)
                    row_data[col_name] = value

            return row_data

        except Exception as e:
            print(f"解析行数据时出错: {e}")
            return {}

    def parse_element(self, elem: ET.Element):
        """解析单个XML元素"""
        # 处理引用
        ref_id = elem.get('ref')
        if ref_id:
            if ref_id in self.id_map:
                ref_data = self.id_map[ref_id]
                if elem.tag in ['start-time', 'size-in-bytes']:
                    return int(ref_data['text'])
                elif elem.tag in ['process']:
                    return ref_data['fmt'].split(' (')[0]
                else:
                    return ref_data['text']
            return None

        # 处理id引用
        elem_id = elem.get('id')
        if elem_id:
            self.id_map[elem_id] = {
                'text': elem.text or '',
                'fmt': elem.get('fmt', ''),
                'tag': elem.tag
            }

        # 转换值
        text = elem.text or ''
        fmt = elem.get('fmt', '')

        if elem.tag in ['start-time', 'size-in-bytes']:
            return int(text)
        elif elem.tag in ['process']:
            return fmt.split(' (')[0]
        else:
            return text


class MemoryAnalyse:
    def __init__(self, case_log_folder, time_field='start'):
        self.case_log_folder = case_log_folder
        self.case_records, self.log_path, self.case_name = self.get_xml_and_log()
        self.time_field = time_field
        self.record_ts_list = self.get_ts_list()
        self.case_steps = self.parse_log()

    def get_xml_and_log(self):
        xml_path = ''
        log_path = ''
        case_name = ''
        for main_dir, dirs, file_name_list in os.walk(self.case_log_folder):
            for file in file_name_list:
                file_path = os.path.join(main_dir, file)
                if file.startswith('PerformanceDynamic_') and file.endswith('.log'):
                    log_path = file_path
                    case_name = file.split('-')[0]
                if file.startswith('PerformanceDynamic_') and file.endswith('.xml'):
                    xml_path = file_path
        if log_path == '' or xml_path == '':
            raise FileNotFoundError(f'xml or log file not found in case folder: {self.case_log_folder}')
        xml_parser = XCTraceXMLParser(xml_path)
        xml_parser.parse()

        return xml_parser.records, log_path, case_name

    def get_ts_list(self):
        time_list = list(set([item.get(self.time_field) for item in self.case_records]))
        time_list.sort()
        return time_list

    def parse_log(self):
        result = []
        file_name = self.log_path.split(os.sep)[-1]
        case_name = file_name.split('-')[0]
        with open(self.log_path, encoding='utf-8', errors='ignore') as log_file:
            for line in log_file:
                pattern = r'(\d+\.\d+)\s*:\s*\[([^\]]+)\]\[([^\]]+)\]'
                # 查找所有匹配项
                matches = re.findall(pattern, line)
                # 将匹配结果转换为字典列表
                result = []
                for match in matches:
                    time_str, app, description = match
                    result.append({
                        'case_name': case_name,
                        'step_ts': int(float(time_str) * 1e9),
                        'app_name': app,
                        'step': description
                    })
        result.sort(key=lambda x: x['step_ts'])
        return result

    def get_trace_records_by_time(self, cur_time):
        pos = bisect.bisect_left(self.record_ts_list, cur_time)
        if pos == len(self.record_ts_list):
            ts = self.record_ts_list[-1]
        else:
            ts = self.record_ts_list[pos-1] if pos > 0 else self.record_ts_list[pos]
        return [item for item in self.case_records if item[self.time_field] == ts]

    def get_case_step_memory(self, step_idx):
        app = self.case_steps[step_idx]['app_name']
        step_name = self.case_steps[step_idx]['step']
        next_step_ts = self.case_steps[step_idx+1]['step_ts'] - 1e9 if step_idx + 1 < len(self.case_steps) \
            else self.case_steps[step_idx]['step_ts'] + 5e9
        step_records = self.get_trace_records_by_time(next_step_ts)
        foreground_apps = [p_name for p_name, app_name in IOS_PACKAGES_MAP.items() if app_name == app]
        all_app_footprint = 0
        all_app_compressed = 0
        app_footprint = 0
        app_compressed = 0
        service_footprint = 0
        service_compressed = 0
        graph_footprint = 0
        graph_compressed = 0
        board_footprint = 0
        board_compressed = 0
        input_footprint = 0
        input_compressed = 0
        kernel = None
        reserved = None
        for step_record in step_records:
            p_name = step_record['process']
            footprint = step_record['memory-physical-footprint']
            compressed = step_record['memory-compressed']
            if p_name in IOS_PACKAGES_MAP:
                all_app_footprint += footprint
                all_app_compressed += compressed
                if p_name in foreground_apps:
                    app_footprint += footprint
                    app_compressed += compressed
            elif p_name in SERVICE_IGNORED:
                continue
            else:
                service_footprint += footprint
                service_compressed += compressed
                if p_name in GRAPH_PROCESS:
                    graph_footprint += footprint
                    graph_compressed += compressed
                if p_name in DESK_PROCESS:
                    board_footprint += footprint
                    board_compressed += compressed
                if p_name in INPUT_PROCESS:
                    input_footprint += footprint
                    input_compressed += compressed
        return {
            '用例': self.case_name,
            '应用': app,
            '步骤id': step_idx + 1,
            '操作步骤': step_name,
            '前台应用内存': bytes_to_mb(app_footprint),
            '前台应用内存(压缩)': bytes_to_mb(app_compressed),
            '应用内存': bytes_to_mb(all_app_footprint),
            '应用内存(压缩)': bytes_to_mb(all_app_compressed),
            '系统服务内存': bytes_to_mb(service_footprint),
            '系统服务内存(压缩)': bytes_to_mb(service_compressed),
            '图形内存': bytes_to_mb(graph_footprint),
            '图形内存(压缩)': bytes_to_mb(graph_compressed),
            '大桌面': bytes_to_mb(board_footprint),
            '大桌面(压缩)': bytes_to_mb(board_compressed),
            '输入法': bytes_to_mb(input_footprint),
            '输入法(压缩)': bytes_to_mb(input_compressed),
            '内核+驱动': kernel,
            '预留': reserved
        }

    def get_case_mem(self):
        mem_infos = []
        for idx, _ in enumerate(self.case_steps):
            step_mem = self.get_case_step_memory(idx)
            mem_infos.append(step_mem)

        with pd.ExcelWriter(os.path.join(self.case_log_folder, f'{self.case_name}.xlsx')) as xlsx:
            pd.DataFrame(mem_infos).to_excel(xlsx, sheet_name='用例内存数据', index=False)
        return mem_infos


class MemoryAnalyseNew:
    def __init__(self, case_log_folder, time_field='start'):
        self.case_log_folder = case_log_folder
        self.time_field = time_field
        self.xml_path_list, self.log_path_list, self.case_name = self.get_xml_and_log()

    def get_xml_and_log(self):
        xml_path_list = []
        log_path_list = []
        case_name = ''
        for main_dir, dirs, file_name_list in os.walk(self.case_log_folder):
            for file in file_name_list:
                file_path = os.path.join(main_dir, file)
                if file.startswith('PerformanceDynamic_') and file.endswith('.log'):
                    log_path_list.append(file_path)
                    case_name = file.split('-')[0]
                if file.startswith('PerformanceDynamic_') and file.endswith('.xml'):
                    xml_path_list.append(file_path)
        if len(xml_path_list) != len(log_path_list) or len(xml_path_list) == 0:
            raise FileNotFoundError(f'xml or log file counts not correct in case folder: {self.case_log_folder}')

        return xml_path_list, log_path_list, case_name

    def get_case_mem(self):
        step_2_xml = {}
        step_2_log = {}

        for item in self.xml_path_list:
            if 'step_' in item:
                step_num = int(item.split('step_')[1].split('-')[0])
                step_2_xml[step_num] = item

        for item in self.log_path_list:
            if 'step_' in item:
                step_num = int(item.split('step_')[1].split('-')[0])
                step_2_log[step_num] = item

        if not step_2_xml or not step_2_log:
            raise ValueError(f"No files with 'step_' pattern found. XML files: {self.xml_path_list}, Log files: {self.log_path_list}")

        step_list = sorted(list(step_2_xml.keys()))

        step_mem_infos = []
        for step_idx in step_list:
            step_info, sample_records = self.parse_xml_and_log(step_2_xml[step_idx], step_2_log[step_idx])
            step_mem = self.get_case_step_memory(step_info['app_name'], step_idx, step_info['step'], sample_records)
            step_mem_infos.append(step_mem)

        with pd.ExcelWriter(os.path.join(self.case_log_folder, f'{self.case_name}.xlsx')) as xlsx:
            pd.DataFrame(step_mem_infos).to_excel(xlsx, sheet_name='用例内存数据', index=False)
        return step_mem_infos

    def parse_xml_and_log(self, xml_path, log_path):
        xml_parser = XCTraceXMLParser(xml_path)
        xml_parser.parse()
        records = xml_parser.records
        record_ts_list = self.get_ts_list(records)
        if len(record_ts_list) < 2:
            raise Exception(f'xctrace: {xml_path} sample less than 2 records, check plz.')
        sample_records = [item for item in records if item[self.time_field] == record_ts_list[1]]

        step_infos = self.parse_log(log_path)
        if len(step_infos) != 1:
            raise Exception(f'step log: {log_path} error, need contain only one step info.')
        step_info = step_infos[0]
        return step_info, sample_records

    def get_ts_list(self, case_records):
        time_list = list(set([item.get(self.time_field) for item in case_records]))
        time_list.sort()
        return time_list

    def parse_log(self, log_path):
        result = []
        file_name = log_path.split(os.sep)[-1]
        case_name = file_name.split('-')[0]
        with open(log_path, encoding='utf-8', errors='ignore') as log_file:
            for line in log_file:
                pattern = r'(\d+\.\d+)\s*:\s*\[([^\]]+)\]\[([^\]]+)\]'
                # 查找所有匹配项
                matches = re.findall(pattern, line)
                # 将匹配结果转换为字典列表
                result = []
                for match in matches:
                    time_str, app, description = match
                    result.append({
                        'case_name': case_name,
                        'step_ts': int(float(time_str) * 1e9),
                        'app_name': app,
                        'step': description
                    })
        result.sort(key=lambda x: x['step_ts'])
        return result

    def get_case_step_memory(self, app, step_idx, step_name, step_records):
        foreground_apps = [p_name for p_name, app_name in IOS_PACKAGES_MAP.items() if app_name == app]
        all_app_footprint = 0
        all_app_compressed = 0
        app_footprint = 0
        app_compressed = 0
        service_footprint = 0
        service_compressed = 0
        graph_footprint = 0
        graph_compressed = 0
        board_footprint = 0
        board_compressed = 0
        input_footprint = 0
        input_compressed = 0
        kernel = None
        reserved = None
        for step_record in step_records:
            p_name = step_record['process']
            footprint = step_record['memory-physical-footprint']
            compressed = step_record['memory-compressed']
            if p_name in IOS_PACKAGES_MAP:
                all_app_footprint += footprint
                all_app_compressed += compressed
                if p_name in foreground_apps:
                    app_footprint += footprint
                    app_compressed += compressed
            elif p_name in SERVICE_IGNORED:
                continue
            else:
                service_footprint += footprint
                service_compressed += compressed
                if p_name in GRAPH_PROCESS:
                    graph_footprint += footprint
                    graph_compressed += compressed
                if p_name in DESK_PROCESS:
                    board_footprint += footprint
                    board_compressed += compressed
                if p_name in INPUT_PROCESS:
                    input_footprint += footprint
                    input_compressed += compressed
        return {
            '用例': self.case_name,
            '应用': app,
            '步骤id': step_idx + 1,
            '操作步骤': step_name,
            '前台应用内存': bytes_to_mb(app_footprint),
            '前台应用内存(压缩)': bytes_to_mb(app_compressed),
            '应用内存': bytes_to_mb(all_app_footprint),
            '应用内存(压缩)': bytes_to_mb(all_app_compressed),
            '系统服务内存': bytes_to_mb(service_footprint),
            '系统服务内存(压缩)': bytes_to_mb(service_compressed),
            '图形内存': bytes_to_mb(graph_footprint),
            '图形内存(压缩)': bytes_to_mb(graph_compressed),
            '大桌面': bytes_to_mb(board_footprint),
            '大桌面(压缩)': bytes_to_mb(board_compressed),
            '输入法': bytes_to_mb(input_footprint),
            '输入法(压缩)': bytes_to_mb(input_compressed),
            '内核+驱动': kernel,
            '预留': reserved
        }



if __name__ == '__main__':
    case_folder = (r'/Users/clover/Documents/111/')
    # 使用 MemoryAnalyse 处理单个 XML/log 文件对
    MemoryAnalyse(case_folder).get_case_mem()