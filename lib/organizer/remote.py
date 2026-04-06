import os
import requests
import mutagen
import musicbrainzngs
from bs4 import BeautifulSoup
from mutagen.id3 import TXXX, Encoding

from lib.path_manager import PathManager
from lib.meta.vgm import (
    get_base_dir_name, get_pmy_cls, get_sdy_cls,
    expand_album_data, merge_duplicates, mk_dir_from_result,
)

musicbrainzngs.set_useragent("MyMusicApp", "1.0", "your@email.com")


def get_meta_from_musicbrainz():
    print("询问输入文件夹的时候，输入#返回主菜单")
    while True:
        folder_path = PathManager.check_input_folder_path()
        if folder_path == '#':
            print('返回主菜单')
            return

        for dir_name in os.listdir(folder_path):
            base_path = os.path.join(folder_path, dir_name)
            if not os.path.isdir(base_path):
                continue

            catno = None
            for file in os.listdir(base_path):
                file_path = os.path.join(base_path, file)
                if file.endswith(".flac"):
                    audio = mutagen.File(file_path)
                    catno = audio.tags.get('CATALOGNUMBER')
                    break
                elif file.endswith((".dsf", ".wav")):
                    audio = mutagen.File(file_path)
                    catno = audio.tags.get('TXXX:CATALOGNUMBER')
                    break

            if not catno:
                print('该文件夹下没有的音频没有搜索需要的元数据，请标上后再试')
                continue

            result = musicbrainzngs.search_releases(
                catno=catno[0] if isinstance(catno, list) else catno,
                limit=5,
            )
            album_id = check_multi_result(result)
            if not album_id:
                print('没有查询到结果')
                continue

            for file in os.listdir(base_path):
                file_path = os.path.join(base_path, file)
                if file.endswith(".flac"):
                    audio = mutagen.File(file_path)
                    audio["MUSICBRAINZ_ALBUMID"] = album_id
                    audio.save()
                elif file.endswith((".dsf", ".wav")):
                    audio = mutagen.File(file_path)
                    audio.tags.add(TXXX(encoding=Encoding.UTF8, desc='MusicBrainz Album Id', text=album_id))
                    audio.save()
            print(f"成功将 albumid 写入 {base_path} 下的音频")


def fetch_vgm_and_create_folder():
    print("询问输入链接的时候，输入#返回主菜单")
    headers = {"User-Agent": "Mozilla/5.0"}

    while True:
        url = input("请输入链接：")
        if url == '#':
            print("返回主菜单")
            return

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        base_dir = get_base_dir_name(soup)
        os.makedirs(base_dir, exist_ok=True)

        pmy_cls = {'Game': [], 'Anime': [], 'Light Novel': [], 'Manga': [], 'N/A': []}
        table = soup.select_one('div#collapse_sub table')
        get_pmy_cls(table, pmy_cls)

        sdy_cls = get_sdy_cls(pmy_cls, headers)
        expand_album_data(sdy_cls, headers)
        album_data = merge_duplicates(sdy_cls)
        mk_dir_from_result(base_dir, album_data, None)
