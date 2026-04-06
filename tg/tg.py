import requests
import threading
import json
import os 
import time
import random
import re
import base64
import argparse

from bs4 import BeautifulSoup
from datetime import datetime, timedelta

requests.post = lambda url, **kwargs: requests.request(
    method="POST", url=url, verify=False, **kwargs
)
requests.get = lambda url, **kwargs: requests.request(
    method="GET", url=url, verify=False, **kwargs
)

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

os.system('cls' if os.name == 'nt' else 'clear')

if not os.path.exists('tg/config.txt'):
    with open('tg/config.txt', 'w'): pass

def json_load(path):
    with open(path, 'r', encoding="utf-8") as file:
        list_content = json.load(file)
    return list_content

def substring_del(string_list):
    string_list.sort(key=lambda s: len(s), reverse=True)
    out = []
    for s in string_list:
        if not any([s in o for o in out]):
            out.append(s)
    return out

tg_name_json = json_load('tg/ch.json')
inv_tg_name_json = json_load('tg/ch-inv.json')

inv_tg_name_json[:] = [x for x in inv_tg_name_json if len(x) >= 5]
inv_tg_name_json = list(set(inv_tg_name_json)-set(tg_name_json))

thrd_pars = int(os.getenv('THRD_PARS', '128'))


pars_dp = int(os.getenv('PARS_DP', '1'))

print(f'\nTotal channel names in tg/ch.json         - {len(tg_name_json)}')
print(f'Total channel names in tg/ch-inv.json - {len(inv_tg_name_json)}')


use_inv_tc = os.getenv('USE_INV_TC', 'n')
use_inv_tc = True if use_inv_tc.lower() == 'y' else False

start_time = datetime.now()

sem_pars = threading.Semaphore(thrd_pars)

config_all = list()
tg_name = list()
new_tg_name_json = list()

print(f'Try get new tg channels name from proxy configs in tg/config.txt...')

with open("tg/config.txt", "r", encoding="utf-8") as config_all_file:
    config_all = config_all_file.readlines()

pattern_telegram_user = r'(?:@)(\w{5,})|(?:%40)(\w{5,})|(?:t\.me\/)(\w{5,})'
pattern_datbef = re.compile(r'(?:data-before=")(\d*)')

for config in config_all:
    if config.startswith('slipnet://'):
        try:
            config = base64.b64decode(config[10:]).decode("utf-8")
        except:
            pass

    matches_usersname = re.findall(pattern_telegram_user, config, re.IGNORECASE)
    try:
        matches_usersname = re.findall(pattern_telegram_user, base64.b64decode(config).decode("utf-8"), re.IGNORECASE)
    except:
        pass
    
    for index, element in enumerate(matches_usersname):
        if element[0] != '':
            tg_name.append(element[0].lower().encode('ascii', 'ignore').decode())
        if element[1] != '':
            tg_name.append(element[1].lower().encode('ascii', 'ignore').decode())
        if element[2] != '':
            tg_name.append(element[2].lower().encode('ascii', 'ignore').decode())             

tg_name[:] = [x for x in tg_name if len(x) >= 5]
tg_name_json[:] = [x for x in tg_name_json if len(x) >= 5]    
tg_name = list(set(tg_name))
print(f'\nFound tg channel names - {len(tg_name)}')
print(f'Total old names        - {len(tg_name_json)}')
tg_name_json.extend(tg_name)
tg_name_json = list(set(tg_name_json))
tg_name_json = sorted(tg_name_json)
print(f'In the end, new names  - {len(tg_name_json)}')

with open('tg/ch.json', 'w', encoding="utf-8") as telegram_channels_file:
    json.dump(tg_name_json, telegram_channels_file, indent = 4)

print(f'\nSearch for new names is over - {str(datetime.now() - start_time).split(".")[0]}')

print(f'\nStart Parsing...\n')

def process(i_url):
    sem_pars.acquire()
    html_pages = list()
    cur_url = i_url
    god_tg_name = False
    for itter in range(1, pars_dp+1):
        while True:
            try:
                response = requests.get(f'https://t.me/s/{cur_url}')
            except:
                time.sleep(random.randint(5,25))
                pass
            else:
                if itter == pars_dp:
                    print(f'{tg_name_json.index(i_url)+1} of {walen} - {i_url}')
                html_pages.append(response.text)
                last_datbef = re.findall(pattern_datbef, response.text)
                break
        if not last_datbef:
            break
        cur_url = f'{i_url}?before={last_datbef[0]}'
    for page in html_pages:
        soup = BeautifulSoup(page, 'html.parser')
        code_tags = soup.find_all(class_='tgme_widget_message_text')
        for code_tag in code_tags:
            code_content2 = str(code_tag).split('<br/>')
            for code_content in code_content2:
                if "slipnet://" in code_content:
                    codes.append(re.sub(htmltag_pattern, '', code_content))
                    new_tg_name_json.append(i_url)
                    god_tg_name = True                    
    if not god_tg_name:
        inv_tg_name_json.append(i_url)
    sem_pars.release()

htmltag_pattern = re.compile(r'<.*?>')

codes = list()

walen = len(tg_name_json)
for url in tg_name_json:
    threading.Thread(target=process, args=(url,)).start()
    
while threading.active_count() > 1:
    time.sleep(1)

print(f'\nParsing completed - {str(datetime.now() - start_time).split(".")[0]}')

print(f'\nStart check and remove duplicate from parsed configs...')

codes = list(set(codes))

processed_codes = list()

for part in codes:
    part = re.sub('%0A', '', part)
    part = re.sub('%250A', '', part)
    part = re.sub('%0D', '', part)
    part = requests.utils.unquote(requests.utils.unquote(part)).strip()
    part = re.sub('amp;', '', part)
    part = re.sub('�', '', part)
    part = re.sub('fp=firefox', 'fp=chrome', part)
    part = re.sub('fp=safari', 'fp=chrome', part)
    part = re.sub('fp=edge', 'fp=chrome', part)
    part = re.sub('fp=360', 'fp=chrome', part)
    part = re.sub('fp=qq', 'fp=chrome', part)
    part = re.sub('fp=ios', 'fp=chrome', part)
    part = re.sub('fp=android', 'fp=chrome', part)
    part = re.sub('fp=randomized', 'fp=chrome', part)
    part = re.sub('fp=random', 'fp=chrome', part)
    if "slipnet://" in part:
        part = f'slipnet://{part.split("slipnet://")[1]}'
        processed_codes.append(part.strip())
        continue

print(f'\nTrying to delete corrupted configurations...') 

processed_codes = list(set(processed_codes))
processed_codes = [x for x in processed_codes if (len(x)>13) and (("…" in x and "#" in x) or ("…" not in x))]
new_processed_codes = list()
for x in processed_codes:
    if x[-2:] == '…»':
        x=x[:-2]
    if x[-1:] == '…':
        x=x[:-1]
    if x[-1:] == '»':
        x=x[:-1]
    if x[-2:-1] == '%':
        x=x[:-2]
    if x[-1:] == '%':
        x=x[:-1]
    if x[-1:] == '`':
        x=x[:-1]        
    new_processed_codes.append(x.strip())
processed_codes = list(set(new_processed_codes))

#processed_codes = substring_del(processed_codes)
#processed_codes = list(set(processed_codes))
processed_codes = sorted(processed_codes)

print(f'\nDelete tg channels that not contains proxy configs...')

new_tg_name_json = list(set(new_tg_name_json))
new_tg_name_json = sorted(new_tg_name_json)

print(f'\nRemaining tg channels after deletion - {len(new_tg_name_json)}')

inv_tg_name_json = list(set(inv_tg_name_json))
inv_tg_name_json = sorted(inv_tg_name_json)

print(f'\nSave new tg/ch.json, tg/ch-inv.json and tg/config.txt...')

with open('tg/ch.json', 'w', encoding="utf-8") as telegram_channels_file:
    json.dump(new_tg_name_json, telegram_channels_file, indent = 4)

with open('tg/ch-inv.json', 'w', encoding="utf-8") as inv_telegram_channels_file:
    json.dump(inv_tg_name_json, inv_telegram_channels_file, indent = 4)

with open("tg/config.txt", "w", encoding="utf-8") as file:
    for code in processed_codes:
        file.write(code.encode("utf-8").decode("utf-8") + "\n")

print(f'\nTime spent - {str(datetime.now() - start_time).split(".")[0]}')
#print(f'\nTime spent - {timedelta(seconds=int((datetime.now() - start_time).total_seconds()))}')
