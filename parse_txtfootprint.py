import time

import pandas as pd
import os, re
from datetime import datetime

ios_app_porc_dict = {
    'AlipayWallet': '支付宝',
    'AMapiPhone': '高德地图',
    'AMapiPhoneHomeWidgetExtension': '高德地图',
    'Anjuke': '安居客',
    'AppStore': '应用商城',
    'AutoMobile': '懂车帝',
    'Aweme': '抖音',
    'Baby_Recommend': '宝宝巴士',
    'bili-universal': '哔哩哔哩',
    'BitAutoPlusStore': '易车',
    'Browser': '悟空浏览器',
    'CMBCPersonBank': '民生银行',
    'CNRNet_code': '央广网',
    'com.apple.Safari.SafeBrowsing.Service': '浏览器',
    'com_kwai_gif': '快手',
    'CTRIP_WIRELESS': '携程旅行',
    'Dopamine': 'dopamine',
    'douyinecommerce': '抖音商城',
    'Driver': '驾校一点通',
    'discover': '小红书',
    'DPScope': '大众点评',
    'DYZB': '斗鱼直播',
    'Filza': 'Filza',
    'Frodo': '豆瓣',
    'GTGJ2': '高铁管家',
    'HuaweiWear': '华为穿戴',
    'HelloLua': '开心消消乐',
    'IHexin': '同花顺',
    'imeituan': '美团',
    'imeituanLiveActivity': '美团',
    'iQiYiPhoneVideo': '爱奇艺',
    'JD4iPhone': '京东',
    'jiaxiaozhijia-ios': '驾考宝典',
    'kiwi': '虎牙直播',
    'kugou': '酷狗',
    'lazyaudio': '懒人听书',
    'live4iphoneRel': '腾讯视频',
    'MGTV-iPhone-appstore': '芒果',
    'MobileCal': '拨号',
    'MobileSafari':'Safari',
    'MobileSMS': '短信',
    'Music': '音乐',
    'MPBBank': '招商',
    'MTXX': '美图',
    'neteasemusic': '网易云音乐',
    'News': '今日头条',
    'OneTravel': '滴滴出行',
    'osee2unifiedRelease': '知乎',
    'peopled': '人民网+',
    'QQ': 'qq',
    'QQMusic': 'qq音乐',
    'QTTourAppStore': '蜻蜓FM',
    'QunariPhone_Cook_CM': '去哪儿',
    'recipe': '下厨房',
    'rls.com.eastmoney.iphone': '东方财富',
    'rls.com.eastmoney.qihuokaihu': '东方财富期货',
    'Sileo': 'Sileo',
    'SinaNews': '新浪新闻',
    'smoba': '王者荣耀',
    'sohunews': '搜狐新闻',
    'Spec': '唯品会',
    'Taobao4iPhone': '淘宝',
    'ThePaperBase': '澎湃新闻',
    'ting': '喜马拉雅',
    'tingWidgetExtension': '喜马拉雅',
    'TMT80': '钛媒体',
    'tztMobileApp_zxsc2.0': '中信证券',
    'WeChat': '微信',
    'Weibo': '新浪微博',
    'YoukuDynamicIslandExtension': '优酷',
    'Youkui4Phone': '优酷',
    'zhaopin': '智联招聘',
    'Zhixing': '智行火车票',
    'zhuanzhuan': '转转',
    '央视影音': '央视影音'}

def get_ios_mem_data(folder_path):
    """
    获取ios 非应用进程数据

    :param folder_path:
    :return: ios_steps_proc = {{}，{}，{}} 以字典嵌套字典的形式存储数据
    """
    total_proc_info = []
    ios_mem_data = []
    ios_app_mem_data = []
    ios_steps_proc = {}
    ios_total_data = []
    file_number = 0
    file = os.listdir(folder_path)
    files_name = sorted(os.listdir(folder_path), key=lambda x: int(re.search(r'\d+', x).group()))
    for filename in files_name:
        if 'footprint' in filename:
            file_path = os.path.join(folder_path, filename)
            ios_steps_proc[steps[file_number]] = {}
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            lines_info = content.split('\n')

            #  用于存储后续数据 进入footprint的判断的标志位
            tmp_index = 0

            for index, line in enumerate(lines_info):
                # 找到AlipayWallet [638]: 64-bit    Footprint: 200 MB (16384 bytes per page)
                if line == '==========================================================================================' and \
                        lines_info[
                            index + 2] == '==========================================================================================':
                    tmp_index += 1

                    parts = lines_info[index + 1].split(' ')
                    # ios_app_porc_dict 为ios中应用的名字
                    if parts[0] not in ios_app_porc_dict.keys():
                        dict_temp = {}
                        dict_temp['filename'] = filename
                        dict_temp['steps'] = steps[file_number]
                        dict_temp['proc_name'] = parts[0]
                        dict_temp['pid'] = parts[1][1:-2]
                        for i, j in enumerate(parts):
                            if j == 'Footprint:':
                                if parts[i + 2] == 'KB':
                                    dict_temp['total_mem'] = float(parts[i + 1]) / 1024
                                    dict_temp['unit'] = 'MB'
                                elif parts[i + 2] == 'GB':
                                    dict_temp['total_mem'] = float(parts[i + 1]) * 1024
                                    dict_temp['unit'] = 'MB'
                                else:
                                    dict_temp['total_mem'] = float(parts[i + 1])
                                    dict_temp['unit'] = 'MB'
                        ios_steps_proc[steps[file_number]][parts[0] + '-' + parts[1][1:-2]] = dict_temp['total_mem']
                        ios_mem_data.append(dict_temp)
                        total_proc_info.append(dict_temp)
                    elif parts[0] in ios_app_porc_dict.keys():
                        dict_temp_app = {}
                        dict_temp_app['filename'] = filename
                        dict_temp_app['steps'] = steps[file_number]
                        dict_temp_app['proc_name'] = parts[0]
                        dict_temp_app['pid'] = parts[1][1:-2]
                        for i, j in enumerate(parts):
                            if j == 'Footprint:':
                                if parts[i + 2] == 'KB':
                                    dict_temp_app['total_mem'] = float(parts[i + 1]) / 1024
                                    dict_temp_app['unit'] = 'MB'
                                else:
                                    dict_temp_app['total_mem'] = float(parts[i + 1])
                                    dict_temp_app['unit'] = 'MB'
                        ios_steps_proc[steps[file_number]][parts[0] + '-' + parts[1][1:-2]] = dict_temp_app['total_mem']
                        ios_app_mem_data.append(dict_temp_app)
                        total_proc_info.append(dict_temp_app)
                if line == '  Dirty  (Swapped)      Clean  Reclaimable    (Wired)    Regions    Category' and \
                        lines_info[
                            index + 1] == '    ---        ---        ---          ---        ---        ---    ---':
                    if tmp_index == 1:
                        tmp_index += 1
                # 用于获取某个进程的clean 、 wired 等的总计内存
                if tmp_index == 2 and 'TOTAL' in line and lines_info[
                    index - 1] == '    ---        ---        ---          ---        ---        ---    ---':

                    uss_tmp_dict = {}
                    if total_proc_info[-1]['proc_name'] == "Summary":
                        break
                    uss_tmp_dict['filename'] = total_proc_info[-1]['filename']
                    uss_tmp_dict['steps'] = total_proc_info[-1]['steps']
                    uss_tmp_dict['proc_name'] = total_proc_info[-1]['proc_name']
                    uss_tmp_dict['pid'] = total_proc_info[-1]['pid']
                    uss_tmp_dict['footprint（MB）'] = total_proc_info[-1]['total_mem']

                    line_tmp = line.split(' ')
                    line_data = []
                    for data_index, data, in enumerate(line_tmp):
                        if data:
                            if data == 'MB':
                                line_data.append(float(line_tmp[data_index - 1]))
                            elif data == 'KB':
                                line_data.append(float(line_tmp[data_index - 1]) / 1024)
                            elif data == 'B':
                                line_data.append(float(line_tmp[data_index - 1]) / 1024 / 1024)

                    uss_tmp_dict['Dirty(MB)'] = line_data[0]
                    uss_tmp_dict['Swapped(MB)'] = line_data[1]
                    uss_tmp_dict['Clean(MB)'] = line_data[2]
                    uss_tmp_dict['Reclaimable(MB)'] = line_data[3]
                    uss_tmp_dict['wired（MB）'] = line_data[4]

                    uss_tmp_dict['Clean（MB） + footprint(MB)'] = total_proc_info[-1]['total_mem'] + line_data[2]

                    uss_tmp_dict['Clean（MB） + footprint(MB) - wired（MB）'] = total_proc_info[-1]['total_mem'] + \
                                                                            line_data[2] - \
                                                                            line_data[4]
                    ios_total_data.append(uss_tmp_dict)
                    tmp_index = 0

            file_number += 1
    return ios_mem_data, ios_steps_proc, ios_app_mem_data, ios_total_data


def get_vmstat_data(folder_path):
    """
    获取ios 非应用进程数据

    :param folder_path:
    :return: ios_steps_proc = {{}，{}，{}} 以字典嵌套字典的形式存储数据
    """
    vmstat_data = []
    steps_number = 0
    file = os.listdir(folder_path)
    files_name = sorted(os.listdir(folder_path), key=lambda x: int(re.search(r'\d+', x).group()))
    for filename in files_name:
        if 'vmstatlog' in filename:
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r') as file:
                    content = file.read()
            lines_info = content.split('\n')

            data_tmp = {}
            steps_number += 1
            data_tmp["steps"] = steps[steps_number - 1]

            for line in lines_info:
                if "Pages wired down:" in line:
                    value = line.split()[-1].strip('.')
                    data_tmp["Pages wired down(MB)"] = (int(value) * 16) / 1024

                elif "Pages free:" in line:
                    value = line.split()[-1].strip('.')
                    data_tmp["Pages free(MB)"] = (int(value) * 16) / 1024

                elif "Pages active:" in line:
                    value = line.split()[-1].strip('.')
                    data_tmp["Pages active(MB)"] = (int(value) * 16) / 1024

                elif "Pages inactive:" in line:
                    value = line.split()[-1].strip('.')
                    data_tmp["Pages inactive(MB)"] = (int(value) * 16) / 1024

                elif "Pages speculative:" in line:
                    value = line.split()[-1].strip('.')
                    data_tmp["Pages speculative(MB)"] = (int(value) * 16) / 1024

                elif "Pages throttled:" in line:
                    value = line.split()[-1].strip('.')
                    data_tmp["Pages throttled(MB)"] = (int(value) * 16) / 1024

                elif "Pages purgeable:" in line:
                    value = line.split()[-1].strip('.')
                    data_tmp["Pages purgeable(MB)"] = (int(value) * 16) / 1024

                elif "Pages occupied by compressor:" in line:
                    value = line.split()[-1].strip('.')
                    data_tmp["Pages occupied by compressor(MB)"] = (int(value) * 16) / 1024


            try:
                data_tmp["内核+驱动(MB)"] = 6 * 1024 - (
                        data_tmp["Pages wired down(MB)"])
                vmstat_data.append(data_tmp)
            except:
                print(files_name)


    return vmstat_data



def output_data(origin_data, system_proc_compare_by_steps, system_type):
    # 输出成excel表格的形式，存在4标签 1、步骤 2、kill或者start 3、进程名字 4、进程的内存情况（不减去swapped部分）
    df_ios_kill_start = None
    df_single_kill_start = None
    if system_type == 'single':
        #  dataframe以[{}，{}]的形式
        single_kill_start_output_data = []
        for value in system_proc_compare_by_steps:
            if value['start']:
                for proc_nema, mem_value in value['start'].items():
                    single_kill_start_output_data.append(
                        {'step_name': value['step_name'], 'type': 'start', 'proc_name': proc_nema,
                         'mem_value(MB)': float(mem_value) / 1024})
            if value['kill']:
                for proc_nema, mem_value in value['kill'].items():
                    single_kill_start_output_data.append(
                        {'step_name': value['step_name'], 'type': 'kill', 'proc_name': proc_nema,
                         'mem_value(MB)': float(mem_value) / 1024})
        df_single_kill_start = pd.DataFrame(single_kill_start_output_data)
    elif system_type == 'ios':
        #  dataframe以[{}，{}]的形式
        ios_kill_start_output_data = []
        for value in system_proc_compare_by_steps:
            if value['start']:
                for proc_nema, mem_value in value['start'].items():
                    ios_kill_start_output_data.append(
                        {'step_name': value['step_name'], 'type': 'start', 'proc_name': proc_nema,
                         'mem_value(MB)': mem_value})
            if value['kill']:
                for proc_nema, mem_value in value['kill'].items():
                    ios_kill_start_output_data.append(
                        {'step_name': value['step_name'], 'type': 'kill', 'proc_name': proc_nema,
                         'mem_value(MB)': mem_value})

        return pd.DataFrame(ios_kill_start_output_data), pd.DataFrame(origin_data)


if __name__ == '__main__':
    # 获取ios的数据  步骤数量 需要和footprint的编号对齐
    steps = ["1. 桌面静置",
            "2. 打开游戏",
            "3. 开始游戏>烽火地带>改枪台>改装>靶场使用",
            "4. 进地图后，静置5s",
            "5. 回到桌面",
            "6. 后台杀应用"]
    ios_file_path = r"/Users/clover/log"
    ios_mem_data, ios_steps_proc, ios_app_mem_data, ios_total_data = get_ios_mem_data(ios_file_path)
    # vmstat_data = get_vmstat_data(ios_file_path)

    with pd.ExcelWriter(f'ios1.xlsx') as writer:
        pd.DataFrame(ios_total_data).to_excel(writer, sheet_name='全量原始数据', index=False)
        # pd.DataFrame(vmstat_data).to_excel(writer, sheet_name='硬件预留', index=False)