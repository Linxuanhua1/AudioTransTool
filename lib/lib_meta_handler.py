import requests, os, sys, tomllib, musicbrainzngs, mutagen
from bs4 import BeautifulSoup
from enum import Enum
from typing import List, Tuple, Optional
from mutagen.id3 import TXXX, Encoding

sys.path.append(os.path.dirname(os.getcwd()))
from lib.vgm import *
from lib.utils import check_multi_result, check_input_folder_path, custom_safe_filename, unfold_catno, fold_catno
from lib.folder_info import analyze_folder_file


musicbrainzngs.set_useragent("MyMusicApp","1.0","your@email.com")

TAG_MAP = {
    '.flac': ("artist", "albumartist", "composer"),
    '.ogg': ("artist", "albumartist", "composer"),
    '.mp3': ("TPE1", "TPE2", "TCOM"),
    '.wav': ("TPE1", "TPE2", "TCOM"),
    '.m4a': ("©ART", "aART", "©wrt"),
    '.wma': ("Author", "WM/AlbumArtist", "WM/Composer"),
}

with open("lib/config.toml", 'rb') as f:
    config = tomllib.load(f)

SEPARATORS = config['separators']


def drop_duplicate():
    print("询问输入字符串的时候，输入#返回主菜单")
    while True:
        input_str = input('请输入要去重的字符串：')
        if input_str == '#':
            print('返回主菜单')
            return
        # 分割 + 去重 + 保留顺序
        unique_names = list(dict.fromkeys(input_str.split("\\")))
        # 再合并为字符串
        result = "\\\\".join(unique_names)
        print(result)


def fetch_vgm_and_create_folder():
    print("询问输入链接的时候，输入#返回主菜单")
    while True:
        url = input("请输入链接：")
        if url == '#':
            print("返回主菜单")
            return
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


def get_meta_from_musicbrainz():
    print("询问输入文件夹的时候，输入#返回主菜单")
    while True:
        folder_path = check_input_folder_path()
        if folder_path == '#':
            print('返回主菜单')
            return

        for dir in os.listdir(folder_path):
            base_path = os.path.join(folder_path, dir)
            if os.path.isdir(base_path):
                catno = None
                for file in os.listdir(base_path):
                    if file.endswith(".flac"):
                        audio = mutagen.File(os.path.join(base_path, file))
                        catno = audio.tags.get('CATALOGNUMBER')
                        break
                    elif file.endswith((".dsf", ".wav")):
                        audio = mutagen.File(os.path.join(base_path, file))
                        catno = audio.tags.get('TXXX:CATALOGNUMBER')
                        break
                if catno:
                    result = musicbrainzngs.search_releases(catno=catno[0] if isinstance(catno, list) else catno,
                                                            limit=5)
                    album_id = check_multi_result(result)
                    if album_id:
                        for file in os.listdir(base_path):
                            if file.endswith(".flac"):
                                audio = mutagen.File(os.path.join(base_path, file))
                                audio["MUSICBRAINZ_ALBUMID"] = album_id
                                audio.save()
                            elif file.endswith((".dsf", ".wav")):
                                audio = mutagen.File(os.path.join(base_path, file))
                                audio.tags.add(TXXX(encoding=Encoding.UTF8, desc='MusicBrainz Album Id', text=album_id))
                                audio.save()
                        print(f"成功将albumid写入{base_path}下的音频")
                    else:
                        print('没有查询到结果')
                else:
                    print('该文件夹下没有的音频没有搜索需要的元数据，请标上后再试')


def rename_folder_from_name():
    def map_pattern():
        while True:
            pattern = input('选择匹配的正则表达式：\n'
                            '1、(.*) \\[.*?\\] (.*)\n'
                            '2、\\[(.*?)\\] (.*?) \\[.*?\\].*\n'
                            '3、\\[(.*?)\\]\\[.*?\\]\\[(.*?)\\].*\n'
                            '4、(\\d{6}) \\[.*?\\](.*?)\\[\n'
                            '5、自定义\n'
                            '请输入数字：')
            if pattern == '1':
                pattern = r'(.*) \[.*?\] (.*)'
                return pattern
            elif pattern == '2':
                pattern = r'\[(.*?)\] (.*?) \[.*?\].*'
                return pattern
            elif pattern == '3':
                pattern = r'\[(.*?)\]\[.*?\]\[(.*?)\].*'
                return pattern
            elif pattern == '4':
                pattern = r'(\d{6}) \[.*?\](.*?)\['
                return pattern
            elif pattern == '5':
                pattern = input("请输入正则表达式：")
                return pattern
            else:
                print('输入匹配模式不正确请重新输入')

    print('提示输入路径的时候输入$可以更改正则表达式，输入#返回主菜单')
    pattern = map_pattern()

    while True:
        folder_path = check_input_folder_path()
        if folder_path == '#':
            print('返回主菜单')
            return
        if folder_path == '$':
            pattern = map_pattern()
            continue

        for folder in os.listdir(folder_path):
            match = re.match(pattern, folder)
            if match:
                folder_full_path = os.path.join(folder_path, folder)
                suffix, label, best_info = analyze_folder_file(folder_full_path)
                orig_date = match.group(1)
                if '.' in orig_date:
                    date = orig_date
                elif len(orig_date) == 6:
                    prefix = "19" if int(orig_date[:2]) > 50 else "20"
                    date = f'{prefix}{orig_date[:2]}.{orig_date[2:4]}.{orig_date[4:]}'
                else:
                    date = f'{orig_date[:4]}.{orig_date[4:6]}.{orig_date[6:]}'
                if best_info[0] == 'N/A':
                    new_folder_name = f"[{date}][{label}][{match.group(2)}][{best_info[1]}]{suffix}"
                else:
                    new_folder_name = f"[{date}][{label}][{match.group(2)}][{best_info[0]}{best_info[1]}]{suffix}"
                new_folder_full_path = os.path.join(folder_path, new_folder_name)
                print(f"旧文件夹名：{folder}")
                print(f"新文件夹名：{new_folder_name}")
                os.rename(folder_full_path, new_folder_full_path)
            else:
                # print(f"no match for {folder}")
                pass


def rename_folder_from_tag():
    print('提示输入路径的时候输入#返回主菜单')
    while True:
        folder_path = check_input_folder_path()
        if folder_path == '#':
            print("返回主菜单")
            return
        for folder in os.listdir(folder_path):
            folder_full_path = os.path.join(folder_path, folder)
            suffix, label, best_info = analyze_folder_file(folder_full_path)
            for file in os.listdir(folder_full_path):
                if file.lower().endswith(".flac"):
                    audio = mutagen.File(os.path.join(folder_full_path, file))
                    try:
                        date = '.'.join(re.split(r'[-/]', audio.tags['DATE'][0][:10]))
                    except KeyError:
                        date = '.'.join(re.split(r'[-/]', audio.tags['YEAR'][0][:10]))
                    album = custom_safe_filename(audio.tags['ALBUM'][0])
                    break
                elif file.lower().endswith('.dsf'):
                    audio = mutagen.File(os.path.join(folder_full_path, file))
                    try:
                        date = '.'.join(re.split(r'[-/]', str(audio.tags['TDAT'][0])[:10]))
                    except KeyError:
                        date = '.'.join(re.split(r'[-/]', str(audio.tags['TDRC'][0])[:10]))
                    album = custom_safe_filename(audio.tags['TALB'][0])
                    break
            if best_info[0] == 'N/A':
                new_folder_name = f"[{date}][{label}][{album}][{best_info[1]}]{suffix}"
            else:
                new_folder_name = f"[{date}][{label}][{album}][{best_info[0]}{best_info[1]}]{suffix}"
            new_folder_full_path = os.path.join(folder_path, new_folder_name)
            print(f"旧文件夹名：{folder}")
            print(f"新文件夹名：{new_folder_name}")
            os.rename(folder_full_path, new_folder_full_path)


# TODO: 还没写完
def write_catno_from_file():
    while True:
        folder_path = check_input_folder_path()
        for folder in os.listdir(folder_path):
            base_folder = os.path.join(folder_path, folder)
            if os.path.isdir(base_folder):
                for file in os.listdir(base_folder):
                    if file.endswith(('.txt', '.log')):
                        name, ext = os.path.splitext(file)
                        catno = name


def write_catno_from_folder_name():
    def map_pattern():
        while True:
            pattern = input('选择匹配的正则表达式：\n'
                            '1、\\[.*?\\] .*? \\[(.*?)\\]\n'
                            '2、\\d{4}.\\d{2}.\\d{2} \\[(.*?)\\].*\n'
                            "3、\\d{6} \\[(.*?)\\].*\n"
                            '请输入数字：')
            if pattern == '1':
                pattern = r'\[.*?\] .*? \[(.*?)\]'
                return pattern
            elif pattern == '2':
                pattern = r'\d{4}.\d{2}.\d{2} \[(.*?)\].*'
                return pattern
            elif pattern == '3':
                pattern = r'\d{6} \[(.*?)\].*'
                return pattern
            else:
                print('输入匹配模式不正确请重新输入')

    print('提示输入路径的时候输入$可以更改正则表达式，输入#返回主菜单')
    pattern = map_pattern()

    while True:
        folder_path = check_input_folder_path()
        if folder_path == '#':
            print('返回主菜单')
            return
        if folder_path == '$':
            pattern = map_pattern()
            continue

        print('-' * 50)
        for folder in os.listdir(folder_path):
            base_folder = os.path.join(folder_path, folder)
            if os.path.isdir(base_folder):
                result = re.match(pattern, folder)
                if result:
                    log_count = 0
                    catno = result.group(1)
                    if "~" in catno or '～' in catno:
                        catno = unfold_catno(catno)
                    print(f'为{base_folder}下的音频写入光盘编号')
                    for file in os.listdir(base_folder):
                        if file.lower().endswith('.flac'):
                            audio = mutagen.File(os.path.join(base_folder, file))
                            audio['CATALOGNUMBER'] = catno
                            audio.save()
                        elif file.lower().endswith(('.dsf', '.wav')):
                            audio = mutagen.File(os.path.join(base_folder, file))
                            audio.tags.add(TXXX(encoding=Encoding.UTF8, desc='CATALOGNUMBER', text=catno))
                            audio.save()
                        elif file.lower().endswith('.log'):
                            log_count += 1
                            tmp_log_path = os.path.join(base_folder, file)
                    if log_count == 1:
                        _, file = os.path.split(tmp_log_path)
                        if file != f'{catno}.log':
                            os.rename(tmp_log_path, os.path.join(base_folder, f'{catno}.log'))
                            print(f'将{file}改名为{catno}.log')
                        else:
                            print(f'{file}无需改名')
                    elif log_count > 1:
                        print(f'文件夹下有多个log文件不进行重命名，请手动复核')
                    else:
                        catno = fold_catno(catno) if isinstance(catno, list) else catno
                        txt_path = os.path.join(base_folder, f'{catno}.txt')
                        if not os.path.exists(txt_path):
                            with open(os.path.join(base_folder, f'{catno}.txt'), 'w') as f:
                                f.write("")
                            print(f'因文件夹下没有log文件在文件夹下创建了{catno}.txt')
                        else:
                            print(f'当前路径下已有{catno}.txt')
                    print(f'完成写入')
                    print('-' * 50)
                else:
                    pass


def separate_tag():
    def separate_text(values: List[str]) -> List[str]:
        """尝试将单一字符串按多个分隔符拆分为多个值。"""
        if len(values) == 1:
            text = values[0]
            # 构建正则分隔符，注意对特殊字符转义
            pattern = '|'.join(re.escape(sep) for sep in SEPARATORS)
            return [v.strip() for v in re.split(pattern, text) if v.strip()]
        return values

    def read_tags(audio, file_path: str) -> Optional[Tuple[str, str, str, List[str], List[str], List[str]]]:
        """根据文件类型返回标签字段名及其值。"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext in TAG_MAP:
            artist_key, albumartist_key, composer_key = TAG_MAP[ext]
            if ext == '.wma':
                return (
                    artist_key,
                    albumartist_key,
                    composer_key,
                    [i.value for i in audio.get(artist_key, [])],
                    [i.value for i in audio.get(albumartist_key, [])],
                    [i.value for i in audio.get(composer_key, [])],
                )
            else:
                return (
                    artist_key,
                    albumartist_key,
                    composer_key,
                    audio.get(artist_key, []),
                    audio.get(albumartist_key, []),
                    audio.get(composer_key, []),
                )
        print(f'不支持的格式，文件为 {file_path}')
        return None

    def update_tags(file_path: str) -> Optional[Tuple]:
        """处理并更新单个音频文件的标签。"""
        try:
            audio = mutagen.File(file_path)
            result = read_tags(audio, file_path)
            if result is None:
                return None

            artist_key, albumartist_key, composer_key, old_artist, old_albumartist, old_composer = result
            new_artist = separate_text(old_artist)
            new_albumartist = separate_text(old_albumartist)
            new_composer = separate_text(old_composer)

            if new_artist == old_artist and new_albumartist == old_albumartist and new_composer == old_composer:
                print(f"{file_path} 无需修改")
                return None

            print(
                f"修改前 [{file_path}]:\n  Artist: {old_artist}\n  Album Artist: {old_albumartist}\n  Composer: {old_composer}")
            audio[artist_key] = new_artist
            audio[albumartist_key] = new_albumartist
            audio[composer_key] = new_composer
            audio.save()

            # 验证更新后标签
            _, _, _, updated_artist, updated_albumartist, updated_composer = read_tags(audio, file_path)
            print(
                f"修改后 [{file_path}]:\n  Artist: {updated_artist}\n  Album Artist: {updated_albumartist}\n  Composer: {updated_composer}")
            print("-" * 50)

            return file_path, artist_key, albumartist_key, composer_key, old_artist, old_albumartist, old_composer

        except Exception as e:
            print(f"[错误] 处理文件 {file_path} 时出错: {e}")
            return None

    def process_directory(folder_path: str):
        """递归处理整个目录下的音频文件，并支持撤回。"""
        modified_files = []

        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(tuple(TAG_MAP.keys())):
                    result = update_tags(os.path.join(root, file))
                    if result:
                        modified_files.append(result)

        if modified_files:
            undo = input("是否撤回修改？(y/n): ").strip().lower()
            if undo == "y":
                for file_path, artist_key, albumartist_key, composer_key, old_artist, old_albumartist, old_composer in modified_files:
                    audio = mutagen.File(file_path)
                    audio[artist_key] = old_artist
                    audio[albumartist_key] = old_albumartist
                    audio[composer_key] = old_composer
                    audio.save()
                    print(f"已撤回 {file_path} 的修改")

    print("询问输入文件夹的时候，输入#返回主菜单")
    while True:
        folder_path = check_input_folder_path()
        if folder_path == '#':
            print('返回主菜单')
            return
        process_directory(folder_path)


def pop_hdlr():
    print("询问输入文件夹的时候，输入#返回主菜单")
    while True:
        folder_path = check_input_folder_path()
        if folder_path == '#':
            print('返回主菜单')
            return
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.m4a'):
                    audio = mutagen.File(os.path.join(root, file))
                    if audio.get('hdlr', None):
                        audio.pop('hdlr')  # 如果存在则删除，不存在则忽略
                    audio.save()


class Action(Enum):
    SEPARATE_TAG = ('分割音频的艺术家、专辑艺术家和编曲家', separate_tag)
    POP_HDLR = ('删除musictag导致的m4a元数据损坏的字段hdlr', pop_hdlr)
    DROP_DUPLICATE = ("字符串去重", drop_duplicate)
    FETCH_VGM_AND_CREATE_FOLDER = ("从vgm拉取系列数据并创建对应文件夹", fetch_vgm_and_create_folder)
    GET_META_FROM_MUSICBRAINZ = ("根据光盘编号从musicbrainz拉取数据", get_meta_from_musicbrainz)
    RENAME_FOLDER_FROM_NAME = ('提取文件夹名重命名文件夹', rename_folder_from_name)
    RENAME_FOLDER_FROM_TAG = ("根据歌曲标签重命名文件夹", rename_folder_from_tag)
    WRITE_CATNO_FROM_FILE = ('（未完成）根据文件夹下的.txt和.log的文件名写入音频的光盘编号标签', write_catno_from_file)
    WRITE_CATNO_FROM_FOLDER_NAME = ("提取文件夹名中的光盘编号写入音频标签", write_catno_from_folder_name)

    def __init__(self, display_name, func):
        self.display_name = display_name
        self.func = func