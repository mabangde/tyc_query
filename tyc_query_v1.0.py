import requests
import argparse
import chardet
import atexit
import csv
import os
import re
import datetime
import json
import time
from urllib.parse import urlparse
import urllib3
urllib3.disable_warnings()

# Define a variable to keep track of the last successfully processed query
def save_checkpoint(file_name, total_queries, current_index):
    # 保存检查点信息到文件
    with open("checkpoint.txt", "w") as checkpoint_file:
        checkpoint_file.write(f"{file_name}\n{total_queries}\n{current_index}")

def load_checkpoint():
    # 从检查点文件加载检查点信息
    checkpoint_info = []
    if os.path.exists("checkpoint.txt"):
        with open("checkpoint.txt", "r") as checkpoint_file:
            checkpoint_info = checkpoint_file.read().splitlines()
    return checkpoint_info

## url 请求函数

proxies = {
    
    }

def get_timesmap():
    timestamp = int(time.time() * 1000)
    timestamp_str = str(timestamp)
    return timestamp_str

# Global equity control parameters, float data type
# investment_threshold = 51.0 (Deprecated)

# Filtering Shareholder Companies (Upstream Investment Companies)
shareholder_group = '騰訊集團'  # 股权链中包含的公司
control_threshold = float(49.0)  # 控制最小投资占股

# 匹配符合股权条件的公司
def filter_equity(text):
    # Define a regular expression pattern to match investment percentages
    pattern = r'\[投资([\d\.]+)%\]'

    # Use regular expressions to find all investment percentages
    percentages = re.findall(pattern, text)

    # Convert percentages to float numbers
    num_list = [float(num) for num in percentages]

    # Check if the equity chain contains the specified shareholder group
    if shareholder_group in text:
        # Check if all investment percentages are greater than or equal to the control threshold
        if all(p >= control_threshold for p in num_list):
            return text

    return None

def load_token():
    try:
        with open('token.txt', 'r') as file:
            loaded_token = file.read().strip()
            if not loaded_token:
                loaded_token = input_and_save_token()
            return loaded_token
    except FileNotFoundError:
        return input_and_save_token()

def input_and_save_token():
    print("[-] Token 文件未找到或已失效，请输入新的 Token.")
    new_token = input("新的 X-AUTH-TOKEN 值: ").strip()
    with open('token.txt', 'w') as file:
        file.write(new_token)
    return new_token

def http_request(url, method='GET', data=None, headers=None, params=None, max_retries=2):
    session = requests.Session()
    """
    执行 HTTP 请求的通用函数

    参数：
    - method: HTTP 请求方法，可以是 'GET'、'POST' 等
    - url: 请求的 URL
    - data: POST 请求的数据（可选）
    - headers: 请求头部信息（可选）
    - params: URL 查询参数（可选）
    - max_retries: 最大重试次数
    - error_keywords: 错误关键字列表，只有在响应中包含这些关键字时才触发重试

    返回值：
    - response: 包含响应的 requests.Response 对象
    """
    retry_attempt = 1
    mustlogin_count = 0
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'

    base_headers = {
        "host": host,
        "Content-Type": "application/json",
        "User-Agent": ua,
        "Referer": "https://www.tianyancha.com/",
        "version": "TYC-Web",
    }

    if headers is not None:
        base_headers.update(headers)

    # Update the X-AUTH-TOKEN header here if needed
    base_headers["X-AUTH-TOKEN"] = load_token()
    time.sleep(1)
    timeout = (30, 30)
    
    for retry_attempt in range(1, max_retries + 1):
        if method == 'GET':
            response = session.get(url, params=params, headers=base_headers, proxies=proxies, verify=False,timeout=timeout)
        elif method == 'POST':
            response = session.post(url, data=data.encode('utf-8'), headers=base_headers, params=params, proxies=proxies, verify=False,timeout=timeout)
        else:
            raise ValueError("不支持的 HTTP 方法")

        try:
            if response:
                response_json = response.json()

            else:
                response_json = {} 
        
        except Exception as e:
            print("[-] Error:",e)
            response_json = {}
            time.sleep(10)
            continue

        if 'mustlogin' in response_json.get('message', ''):
            if mustlogin_count == 0:
                # 第一次出现'mustlogin'表示token无效，需要重新输入
                input_and_save_token()
                mustlogin_count += 1
        if '请稍后重试' not in response_json.get('message', ''):
            return response

        print('[-] message:', response_json.get('message', ''))
        print('正在:第', retry_attempt, "次重试..")
        if retry_attempt < max_retries:
            print("正在等待 40 秒后重试...")
            time.sleep(40)
        else:
            print("已达到最大重试次数，停止重试。")
            return None

    return response

## 通过企业名查企业ID
def get_company_info(name):
    print(f'[i] 通过企业名称：{name},查询企业ID')
    timestamp_str = get_timesmap()
    company_url = f'https://capi.tianyancha.com/cloud-tempest/web/searchCompanyV3?_={timestamp_str}'
    data = '{"word":"' + str(name) + '","sortType":"1","pageSize":0,"referer":"search","pageNum":0}'
    response = http_request(company_url, method='POST', data=data)
    if response:
        json_data = response.json()
        if 'data' in json_data:
            companyList = json_data['data']['companyList']
            for compay in companyList:
                if compay['name']:
                    company_name = compay['name'].replace('<em>', '').replace('</em>', '')
                    company_name = company_name.strip()
                    if name in company_name:
                        company_info = {}  # 创建一个字典来存储公司信息
                        company_info['公司ID'] = compay['id']
                        company_info['公司名称'] = company_name
                        company_info['注册资本'] = compay['regCapital']
                        company_info['成立日期'] = compay['estiblishTime'].replace(' 00:00:00.0','')

                        # 处理websites字段，保持与之前的方式一致
                        site = str(compay['websites']).split('\t')
                        website = []
                        for w in site:
                            if w and ';' not in w:  # 添加检查 w 是否为空
                                website.append(w)
                        company_info['域名列表'] = ','.join(map(str, website)) if website else '-'

                        company_info['邮箱列表'] = ','.join(compay['emailList']) if compay['emailList'] else '-'
                        company_info['登记状态'] = compay['regStatus']
                        return [company_info]  # 返回第一个匹配的字典数据

        return []  # 如果没有匹配的数据，则返回空列表

## 通过企业ID 查询企业备案号
def get_company_icp(cid):
    print(f"[i] 正在查询企业ID: {cid} 备案号...")
    headers = {
        'authority': 'capi.tianyancha.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh,zh-CN;q=0.9,en;q=0.8,zh-TW;q=0.7,eo;q=0.6',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    }
    timestamp_str = get_timesmap()
    params = {
        '_': f'{timestamp_str}',
        'gid': f'{cid}',
        'pageSize': '10',
        'pageNum': '1',
    }
    try:
        tyc_icp_api_url = 'https://capi.tianyancha.com/cloud-history-information/historyIntellectualProperty/icpRecordList'
        response = http_request(tyc_icp_api_url, method='GET', params=params,headers=headers)
        #print(response.json())
        json_data= response.json()
        if 'data' in json_data and 'total' in json_data['data'] and json_data['data']['total'] >= 1:
            licenses = set()
            for company in json_data['data']['item']:
                #print(company)
                license = company.get('liscense')
                if license:
                    licenses.add(license)
            return ', '.join(licenses) if licenses else '-'
    except (ValueError, KeyError):
        pass
    return '-'



def get_company_icp1(cid):
    headers = {
        'authority': 'capi.tianyancha.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh,zh-CN;q=0.9,en;q=0.8,zh-TW;q=0.7,eo;q=0.6',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    }
    timestamp_str = get_timesmap()
    params = {
        '_': f'{timestamp_str}',
        'id': f'{cid}',
        'pageSize': '10',
        'pageNum': '1',
    }
    try:
        tyc_icp_api_url = 'https://capi.tianyancha.com/cloud-intellectual-property/intellectualProperty/icpRecordList'
        response = http_request(tyc_icp_api_url, method='GET', params=params,headers=headers)
        #print(response.json())
        json_data= response.json()
        if 'data' in json_data and 'itemTotal' in json_data['data'] and json_data['data']['itemTotal'] >= 1:
            licenses = set()
            for company in json_data['data']['item']:
                license = company.get('liscense')
                if license:
                    licenses.add(license)
            return ', '.join(licenses) if licenses else '-'
    except (ValueError, KeyError):
        pass
    return '-'
## 企业股权分析
## investment_threshold 控股投资阈值float 数据类型
def equity_analysis(cid):
    print(f'[i] 正在查询企业ID: {cid} 股权穿透信息...')
    current_year = datetime.datetime.now().year
    timestamp = get_timesmap()
    timestamp_plus_5 = int(timestamp) + 5
    headers = {
        # 'Content-Length': '140',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Pm': '141',
        'Spm': 'i101',
        'X-Tycid': '6a55e7d0c87f11ed82f2dfb0999cb370', # 根据实际情况配置一般通一个账号不会变
        'Sec-Ch-Ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Page_id': 'TYCGraphPage',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
        'Eventid': 'i101',
        'X-Spm-Referer': f'https://graph.tianyancha.com/web/tree/controller?cid={cid}&category=SAC&depth=3&entityType=2&spm=&pm=&export=',
        'Version': 'TYC-Web',
        'Origin': 'https://graph.tianyancha.com',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': f'https://graph.tianyancha.com/web/tree/controller?cid={cid}&category=SAC&depth=3&entityType=2&spm=&pm=&export='
    }

    params = {
        '_': timestamp_plus_5,
    }

    json_data = {
        'entityId': f'{cid}',
        'entityType': 2,
        'year': f'{current_year}',
        'spm': 'i101',
        'pm': '141',
        'page_id': 'TYCGraphPage',
        'eventId': 'i101',
        'traceId': timestamp,
    }
    data = json.dumps(json_data)

    tyc_url ='https://capi.tianyancha.com/tyc-enterprise-graph/ei/get/actual/controller/graph'

    response = http_request(tyc_url, method='POST', headers=headers,params=params,data=data)

    json_data = response.json()
    #print(json_data)
    if json_data['data']:
        paths = json_data['data']['paths'][0]['groupedPaths'][0]['pathText']
        company_name = json_data['data']['brief'][0]['text']

        # 构建股权关联路径格式，将 "rightArrow" 条目替换为 "[投资100%]"
        formatted_paths = []
        for path in paths:
            if path['textType'] == 'rightArrow':
                formatted_paths.append('['+path['text']+']')
            if path['textType'] == 'entity':
                formatted_paths.append(path['text'])

        # 将格式化后的路径以 "->" 连接并打印
        path_format = "->".join(formatted_paths)
        return path_format
    else: 
        #company_name = "-"
        path_format = "-"
        return path_format

## 所有信息查询入口
def query_infos(company_name,mode=0):
    get_companys = get_company_info(company_name)
    
    if get_companys:
        company_infos = get_companys[0]
        company_id = company_infos.get('公司ID')
        company_zt = company_infos.get('登记状态')
        if company_zt in ['存续','正常','开业','在业']:
            get_company_icps = get_company_icp(company_id)
            if get_company_icps == '-':
                get_company_icps = get_company_icp1(company_id)
            company_icps ={
                '企业备案' :get_company_icps
            }
            # 控制股权参数float 类型
            #print(equitys)
            equitys = equity_analysis(company_id)
            #print(equitys)
            path = {
                '股权穿透信息':equitys
            }

            if filter_equity(equitys):
                combined_info = {**company_infos, **company_icps, **path}
                print('=' * 50)
                for key, value in combined_info.items():
                    print(f"{key}: {value}")
                print('=' * 50)

                csv_filename = args.output_file

                with open(csv_filename, 'a', newline='', encoding='utf-8-sig') as csv_file:
                    fieldnames = combined_info.keys()
                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    if csv_file.tell() == 0:
                        writer.writeheader()
                    writer.writerow(combined_info)
            if mode==1:
                combined_info = {**company_infos, **company_icps, **path}
                print('=' * 50)
                for key, value in combined_info.items():
                    print(f"{key}: {value}")
                print('=' * 50)

                csv_filename = args.output_file

                with open(csv_filename, 'a', newline='', encoding='utf-8-sig') as csv_file:
                    fieldnames = combined_info.keys()
                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    if csv_file.tell() == 0:
                        writer.writeheader()
                    writer.writerow(combined_info)

def main(args):
    if args.query:
        # 单个查询模式
        mode = 1
        company_name = args.query
        print('[i] 正在查询: ', company_name, "企业信息...")
        query_infos(company_name,mode)

    elif args.file:
        # 批量查询模式
        with open(args.file, 'rb') as f:
            result = chardet.detect(f.read())

        with open(args.file, 'r', encoding=result['encoding']) as file:
            query_strings = file.read().splitlines()

        total_queries = len(query_strings)
        
        # 从检查点加载上次的查询状态
        checkpoint_info = load_checkpoint()
        if checkpoint_info:
            file_name, total_queries, current_index = checkpoint_info
            total_queries = int(total_queries)  # 将字符串转换为整数
            current_index = int(current_index)    # 将字符串转换为整数
            print(f'[i] 上次查询文件: {file_name}, 总查询数: {total_queries}, 当前索引: {current_index}')
        else:
            file_name = args.file
            current_index = 0

        for index in range(current_index, total_queries):
            query_string = query_strings[index]
            print(f'[i] 正在查询 ({index + 1}/{total_queries}): {query_string} 企业信息...')
            query_infos(query_string,mode=0)
            
            # 更新检查点信息
            save_checkpoint(file_name, total_queries, index + 1)
     

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="天眼查企业信息查询")
    parser.add_argument("-q", "--query", type=str, help="A single query string for web data.")
    parser.add_argument("-f", "--file", type=str, help="A file containing a list of query strings, one per line.")
    parser.add_argument("-o", "--output_file", type=str, default="company_name_infos.csv", help="Output CSV filename.")
    args = parser.parse_args()
    main(args)
