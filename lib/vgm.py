import re, os, requests, random, sys
sys.path.append(os.path.dirname(os.getcwd()))
from bs4 import BeautifulSoup
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from lib.common_method import custom_safe_filename


def get_base_dir_name(soup):
    span = soup.find('span', class_='albumtitle')
    for em in span.find_all('em'):
        em.decompose()
    base_dir = span.get_text(strip=True)
    return base_dir


def get_pmy_cls(table, pmy_cls):
    for row in table.find_all('tr')[1:]:  # 跳过标题行
        data_dict = {'date': '', 'name': '', 'url': ''}
        cols = row.find_all('td')
        if len(cols) < 2:
            continue

        # 1. 日期
        data_tag = cols[0].get_text(strip=True)
        date = data_tag if data_tag else 'N/A'

        # 2. 链接部分
        a_tag = cols[1].find('a')
        if not a_tag:
            continue
        href = a_tag['href']
        url = 'https://vgmdb.net' + href

        # 3. 名称（lang=ja）
        name_tag = a_tag.find('span', class_='productname', lang='ja')
        name = name_tag.get_text(strip=True) if name_tag else 'N/A'

        # 4. 类型：链接尾部 span，例如 (Game)
        type_tag = a_tag.find('span', class_='label')
        type_text = type_tag.get_text(strip=True).strip("()") if type_tag else 'N/A'

        data_dict['name'] = name
        data_dict['url'] = url
        data_dict['date'] = date
        pmy_cls[type_text].append(data_dict)

def fetch_sdy_info(data, headers):
    url = data['url']
    print(f'[sdy] 正在处理 {url}')
    sleep(random.uniform(0.5, 1.5))
    try:
        response_sdy_ser = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response_sdy_ser.text, 'html.parser')
        current_year = None
        results = []

        for tr in soup.select('div#discotable tr'):
            if tr.get('rel') == 'year':
                year_tag = tr.find('h3', class_='time')
                if year_tag:
                    current_year = year_tag.text.strip()
            elif tr.get('rel'):
                tds = tr.find_all('td')
                if len(tds) >= 2:
                    date_md = tds[0].get_text(strip=True)
                    full_date = f"{current_year}-{date_md.replace('.', '-')}" if current_year else date_md

                    a_tag = tds[1].find('a', class_='albumtitle')
                    url = a_tag['href'] if a_tag else None

                    title_ja = ''
                    if a_tag:
                        ja_span = a_tag.find('span', lang='ja')
                        if ja_span:
                            for em in ja_span.find_all('em'):
                                em.decompose()
                            title_ja = ja_span.get_text(strip=True)

                    label_tag = tds[1].find('span', class_='smallfont label')
                    label = label_tag.get_text(strip=True) if label_tag else 'N/A'

                    if url and 'Fan Arrangement' not in label:
                        results.append({
                            'date': full_date,
                            'title': title_ja,
                            'series': data['name'],
                            'url': url,
                            'type': data['type']
                        })
        return results
    except Exception as e:
        print(f'[sdy] 错误: {url} - {e}')
        return []

def get_sdy_cls(pmy_cls, headers):
    all_data = []
    tasks = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        for field, datas in pmy_cls.items():
            for data in datas:
                data['type'] = field  # 为后续使用添加类型信息
                tasks.append(executor.submit(fetch_sdy_info, data, headers))

        for future in as_completed(tasks):
            all_data.extend(future.result())

    return all_data

def merge_duplicates(entries):
    title_map = defaultdict(list)

    # 分组：按 title 聚合
    for entry in entries:
        key = (entry['title'], entry['Catalog Number'])
        title_map[key].append(entry)
    result = []

    for title, items in title_map.items():
        if len(items) == 1:
            # 没有重复，直接加入
            result.append(items[0])
        else:
            # 有重复，保留第一个，改 type 为 compilation
            merged = items[0].copy()
            merged['type'] = 'Compilation'
            result.append(merged)

    return result

def mk_dir_from_result(base_dir, result, pattern):
    for item in result:
        type_tag = custom_safe_filename(item['type'])
        series_tag = custom_safe_filename(item['series'])
        date_tag = custom_safe_filename(item['date'])
        title_tag = custom_safe_filename(item['title'])
        catalogue_number_tag = custom_safe_filename(item['Catalog Number'])
        os.makedirs(f"{base_dir}/{type_tag}/{series_tag}/{date_tag} {title_tag} [{catalogue_number_tag}]", exist_ok=True)

def fetch_album_details(i, headers, max_retries=3):
    url = i['url']
    retries = 0
    delay_range = (0.5, 1.5)

    while retries < max_retries:
        print(f'[album] 正在处理 {url} (尝试 {retries + 1}/{max_retries})')
        sleep(random.uniform(*delay_range))

        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.select_one("table#album_infobit_large")

            if table:
                for row in table.select("tr"):
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        label = cols[0].get_text(strip=True)
                        if label == "Catalog Number":
                            # 只提取第一个 <a> 标签的文本
                            first_catalog = cols[1].find("a")
                            if first_catalog:
                                i[label] = first_catalog.get_text(strip=True)
                            else:
                                i[label] = cols[1].get_text(" ", strip=True)
                        else:
                            value = cols[1].get_text(" ", strip=True)
                            i[label] = value
            return  # 成功处理，退出函数

        except requests.exceptions.RequestException as e:
            print(f'[album] 错误: {url} - {e}')
            retries += 1
            if retries >= max_retries:
                print(f'[album] 多次失败，跳过：{url}')
                return


def expand_album_data(album_data, headers):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_album_details, item, headers) for item in album_data]
        for _ in as_completed(futures):
            pass  # 仅等待任务完成