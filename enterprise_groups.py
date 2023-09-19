import requests
import re
import time
from bs4 import BeautifulSoup 
import urllib.parse
from timeit import default_timer as timer
import csv
import urllib3
import random
urllib3.disable_warnings()

#登录天眼查后，寻找cookie 为 auth_token的参数填入下方

def http(url,Referer):
    auth_token = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIxMzA3MTIyNzc3MSIsImlhdCI6MTY5NDU5NjE0MiwiZXhwIjoxNjk3MTg4MTQyfQ.lMu3xPBIba0veBkkwSaZMm9GkFnSKxW3Q16y4roz6SgthiBfxZn5HPPJy7vAH5xcX3EKc3U66j3vnEEJEQVA-w"
    csrfToken = "t3ADGn_ijPeIWaHt2ZbLoJpb"
    proxies = {
    "http": "http://127.0.0.1:8080",
    "https": "http://127.0.0.1:8080",
    }

    cookies = {
        'csrfToken' : csrfToken,
        'auth_token': auth_token
    }

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh,zh-CN;q=0.9,en;q=0.8,zh-TW;q=0.7,eo;q=0.6',
        'Connection': 'keep-alive',
        'Referer': Referer,
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    req = requests.get(url,headers=headers,cookies=cookies,proxies=proxies, verify=False , timeout=5)
    html_text = req.text

    if req.url != url:
        print('身份失效...')
        print('跳转后的URL:', req.url)
        print('请重新打开浏览器登陆，并替换cookie中auth_token...')
        req.close()
        exit()
    
    if 'unlogin-mask-risk' in html_text:
        print('登陆失效，请在网页端重新登陆，并重新设置COOKIE auth_token 、csrfToken 字段...')
        print('浏览器访问：{}'.format(url))
        req.close()
        exit()

    if '请进行身份验证以继续使用' in html_text:
        print('请进行身份验证以继续使用')
        print('浏览器访问：{}'.format(url))
        req.close()
        exit()
    req.close()
    
    return html_text

'''
cid 企业id：3131283508
groupid ： 企业成员组id： 1dbe82aedb4f432c975bba6083485bb0
根据关键字返回企业id及企业组ID
'''
def get_ids(str):
    #print('get_ids...')
    key = urllib.parse.quote(str)
    url = "https://www.tianyancha.com/search?key={}".format(key)
    Referer = 'https://www.tianyancha.com/'
    html_text = http(url ,Referer)
    #print(html_text)
    match = re.search(r'"companyGroup":{"id":"([0-9a-fA-F]{32})",', html_text)
    match1 = re.search(r'/company/([\d]+)',html_text)
    if match and match1:
        company_group_id = match.group(1)  # 企业成员ID
        company_id = match1.group(1)    # 企业ID
        return company_group_id,company_id

def random_delay():
    delay = random.randint(2, 8)  # 生成1至5之间的随机整数
    time.sleep(delay)  # 使用time.sleep()函数进行延时

## 获取企业组成员
def get_company_groups(cids,enterprise_name):
    group_id = cids[0]
    company_id = cids[1]
    url = "https://www.tianyancha.com/group/{}/{}".format(company_id,group_id)
    Referer = url
    html_text = http(url,Referer)
    enterprise = (re.findall("<span class='rt'>(.+?)<",html_text))
    if enterprise:
        print("=" * 35)
        print("全部企业共：{}家".format(enterprise[0]))
        print("核心企业共：{}家".format(enterprise[1]))
        print("上市企业共：{}家".format(enterprise[2]))
        print("=" * 35)
        
        if len(enterprise[1]):
                print("共获取:",int(float(enterprise[1])/10+0.99)+1,"页数据")
                
                #for i in range(103,105):
                for i in range(1,int(float(enterprise[1])/10+0.99)+1):
                    print("正在获取:",i,"页数据")
                    #random_delay()
                    get_companys_url = "https://www.tianyancha.com/company/groupPagination.html?uuid={}&type=1&page={}".format(group_id,i)
                    html_data = http(get_companys_url,Referer)
                    soup = BeautifulSoup(html_data, 'html.parser')
                    ## 找到 table 
                    table = soup.find('table', class_='table')

                    ## 找到首个tbody
                    tbody = table.find('tbody')

                    ## 获取所有tbody 中tr
                    tr_all = tbody.find_all('tr')

                    for tr in tr_all:

                        # 找到所有的<td>元素
                        td_elements = tr.find_all('td')

                        # 初始化数据字段
                        data = {
                            "序号": "",
                            "企业ID": "",
                            "企业名称": "",
                            "法定代表人": "",
                            "注册资本": "",
                            "成立日期": "",
                            "登记状态": ""
                        }

                        if len(td_elements)==11:
                            for i, td in enumerate(td_elements):
                                if i==0:
                                    data["序号"] = td.get_text(strip=True)
                                if i==3:
                                    data["企业名称"] = td.get_text(strip=True)
                                    data["企业ID"] = td.find('a')['href'].split('/')[-1]
                                if i==6:
                                    data["法定代表人"] = td.get_text(strip=True)
                                if i==8:
                                    data["注册资本"] = td.get_text(strip=True)
                                if i==9:
                                    data["成立日期"] = td.get_text(strip=True)
                                if i==10:
                                    data["登记状态"] = td.get_text(strip=True)

                            for key, value in data.items():
                                print(f"{key}: {value}")

                            print("="*35)
                            csv_filename = f'{enterprise_name}_核心企业.csv'
                            with open(csv_filename, mode='a', newline='', encoding='utf-8-sig') as csvfile:
                                # 创建CSV写入器
                                csv_writer = csv.DictWriter(csvfile, fieldnames=data.keys())

                                # 如果文件为空，写入表头
                                if csvfile.tell() == 0:
                                    csv_writer.writeheader()
                                # 写入数据行
                                csv_writer.writerow(data)
                    
def main():
    enterprise = '国家电网有限公司' # 定义集团名称
    ids = get_ids(enterprise)
    get_company_groups(ids,enterprise)

if __name__=="__main__":
    main()
