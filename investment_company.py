# author:Wolvez
# time:2023/10/31
import random
import traceback
import requests
import time
import optparse
import json
import base64
from urllib.parse import urlparse
import urllib.request
import re
import tldextract
from datetime import datetime
import math
from openpyxl import Workbook
from configparser import ConfigParser

requests.packages.urllib3.disable_warnings()
import urllib
import os
proxies = {
    'http': 'http://127.0.0.1:8081',
    'https': 'http://127.0.0.1:8081'
}

x_auth_token = 'eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIxMzUwMTE3OTYzNiIsImlhdCI6MTY5ODY1ODA0NywiZXhwIjoxNzAxMjUwMDQ3fQ.8hBts2BQyV6AAgOAq1CbaHGo61z_voXF-1SEwge4RL2b4xKOnT5DBZicddHpC0jVz5Bw-bSRapGmLntfz6pW-A'



def remove_html_tags_and_spaces(text):
    clean = re.compile('<.*?>')
    text_without_tags = re.sub(clean, '', text)
    text_without_spaces = re.sub(r'\s', '', text_without_tags)
    return text_without_spaces


def get_timesmap():
    timestamp = int(time.time() * 1000)
    timestamp_str = str(timestamp)
    return timestamp_str

timestamp_str = get_timesmap()


## 通过企业名查企业ID
def get_company_info(name):
    #print(f'[i] 通过企业名称：{name},查询企业ID')
    
    company_url = f'https://capi.tianyancha.com/cloud-tempest/web/searchCompanyV3?_={timestamp_str}'
    data = '{"word":"' + str(name) + '","sortType":"1","pageSize":0,"referer":"search","pageNum":0}'
    response = http_request(company_url, method='POST', data=data)
    if response:
        json_data = response.json()
        if 'data' in json_data:
            companyList = json_data['data']['companyList']
            for compay in companyList:
                if compay['name']:
                    company_name = remove_html_tags_and_spaces(str(compay['name']))
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



## 查询下属子公司及投资情况

def get_child_companies(id):
    id_list = []
    company_url = "https://capi.tianyancha.com/cloud-company-background/company/investListV2"
    per_page = 100
    page = 1
    '''
    "percentLevel":"-100"  包含全部持股比例
    "percentLevel":"1" 不到5%
    "percentLevel":"2"  5% 以上
    "percentLevel":"3"  %25 以上
    "percentLevel":"4"  %50 以上
    "percentLevel":"5"  %90 以上
    "percentLevel":"6"  100% 
    '''
   

    while True:
        data = {
            "gid": str(id),
            "pageSize": per_page,
            "pageNum": page,
            "province": "",
            "percentLevel": "4",
            "category": "-100"
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-AUTH-TOKEN": x_auth_token
        }

        response = http_request(company_url, method='POST', json_data=data, headers=headers)
        j = response.json()

        for i in range(len(j['data']['result'])):
            entry = {}
            '''
            percent_data = j['data']['result'][i]['percent']
            if percent_data != '' and percent_data != "-" and percent_data is not None:
                occ_r = str(percent_data)  # 转为字符串
                occ_r = occ_r[:-1]
                occ_rev = float(occ_r)
                if occ_rev >= float(company_occ):
            '''
            entry['id'] = j['data']['result'][i]['id']
            entry['name'] = j['data']['result'][i]['name']
            entry['regStatus'] = j['data']['result'][i]['regStatus']
            entry['percent'] = j['data']['result'][i]['percent']
            id_list.append(entry)

        if page * per_page >= j['data']['total']:
            break

        page += 1

    return id_list



def input_and_save_token():
    print("[-] Token 文件未找到或已失效，请输入新的 Token.")
    new_token = input("新的 X-AUTH-TOKEN 值: ").strip()
    with open('token.txt', 'w') as file:
        file.write(new_token)
    return new_token

def load_token():
    try:
        with open('token.txt', 'r') as file:
            loaded_token = file.read().strip()
            if not loaded_token:
                loaded_token = input_and_save_token()
            return loaded_token
    except FileNotFoundError:
        return input_and_save_token()

def http_request(url, method='GET', data=None, json_data=None, headers=None, params=None, max_retries=2):
    session = requests.Session()
    """
    执行 HTTP 请求的通用函数

    参数：
    - method: HTTP 请求方法，可以是 'GET'、'POST' 等
    - url: 请求的 URL
    - data: POST 请求的数据（可选）
    - json_data: POST 请求的 JSON 数据（可选）
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
            if json_data is not None:
                response = session.post(url, json=json_data, headers=base_headers, params=params, proxies=proxies, verify=False,timeout=timeout)
            else:
                response = session.post(url, data=data.encode('utf-8'), headers=base_headers, params=params, proxies=proxies, verify=False,timeout=timeout)
        else:
            raise ValueError("不支持的 HTTP 方法")

        try:
            if response:
                response_json = response.json()
            else:
                response_json = {} 
        except session.exceptions.Timeout:
            print("请求超时")

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
 


def get_company_chain(company_id, current_chain=None):
    child_companies = get_child_companies(company_id)

    if current_chain is None:
        current_chain = []

    company_chains = []

    # 递归获取子公司的子公司列表和关系链条
    for child_company in child_companies:
        child_company_name = child_company['name']
        child_company_id = child_company['id']
        investment_percent = child_company['percent']
        chain_description = f"{child_company_name} (投资比例: {investment_percent})"

        child_company_chain = current_chain + [chain_description]  # 构建子公司的关系链

        company_chains.append(child_company_chain)

        # 打印当前关系链
        print(" => ".join(child_company_chain))

        # 递归调用以获取子公司的子公司和关系链条
        child_company_chains = get_company_chain(child_company_id, child_company_chain)
        if child_company_chains:
            company_chains.extend(child_company_chains)

    return company_chains

if __name__ == '__main__':
    
    # 指定公司名称，开始获取子公司信息和关系链条
    company_name = "谷歌公司"  # 请替换为实际的公司名称
    #all_subcompany_chains = get_company_chain(company_name)
    company_info =get_company_info(company_name)
    company_id = int(company_info[0]['公司ID'])
    get_company_chain(company_id)
 
