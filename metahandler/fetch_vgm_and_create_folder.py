import requests, os
from bs4 import BeautifulSoup
os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.path.dirname(os.getcwd())
from lib.vgm import *


url = input("请输入链接：")
headers = {"User-Agent": "Mozilla/5.0"}
response_pmy_ser = requests.get(url, headers=headers)
soup = BeautifulSoup(response_pmy_ser.text, 'html.parser')

base_dir = get_base_dir_name(soup)
os.makedirs(base_dir, exist_ok=True)

pmy_cls = {'Game': [], 'Anime': [], 'Light Novel': [], 'Manga': [], 'N/A': []}
table = soup.select_one('div#collapse_sub table')
get_pmy_cls(table, pmy_cls)

sdy_cls = get_sdy_cls(pmy_cls, headers)

expand_album_data(sdy_cls, headers)

album_data = merge_duplicates(sdy_cls)

mk_dir_from_result(base_dir, album_data, None)

