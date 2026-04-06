from pathlib import Path
import re
import mutagen
from mutagen.id3 import TXXX, Encoding

from lib.path_manager import PathManager
from lib.organizer.utils import unfold_catno, fold_catno
from lib.organizer.folder_info import analyze_folder_file
from lib.organizer.utils import map_pattern


# ── 正则选择器配置 ────────────────────────────────────────────────

RENAME_PATTERNS = {
    '1': r'(.*) \[.*?\] (.*)',
    '2': r'\[(.*?)\] (.*?) \[.*?\].*',
    '3': r'\[(.*?)\]\[.*?\]\[(.*?)\].*',
    '4': r'(\d{6}) \[.*?\](.*?)\[',
}

RENAME_PROMPT = [
    '选择匹配的正则表达式：',
    r'1、(.*) \[.*?\] (.*)',
    r'2、\[(.*?)\] (.*?) \[.*?\].*',
    r'3、\[(.*?)\]\[.*?\]\[(.*?)\].*',
    r'4、(\d{6}) \[.*?\](.*?)\[',
    '5、自定义',
]

CATNO_PATTERNS = {
    '1': r'\[.*?\] .*? \[(.*?)\]',
    '2': r'\d{4}.\d{2}.\d{2} \[(.*?)\].*',
    '3': r'\d{6} \[(.*?)\].*',
    '4': r'.*?\[(.*?)\].*',
}

CATNO_PROMPT = [
    '选择匹配的正则表达式：',
    r'1、\[.*?\] .*? \[(.*?)\]',
    r'2、\d{4}.\d{2}.\d{2} \[(.*?)\].*',
    r'3、\d{6} \[(.*?)\].*',
    r'4、.*?\[(.*?)\].*',
]

# ── 内部工具函数 ──────────────────────────────────────────────────

def _normalize_date(orig_date: str) -> str:
    """将 6 位、8 位或已含点的日期统一为 YYYY.MM.DD 格式。"""
    if '.' in orig_date:
        return orig_date
    if len(orig_date) == 6:
        prefix = "19" if int(orig_date[:2]) > 50 else "20"
        return f'{prefix}{orig_date[:2]}.{orig_date[2:4]}.{orig_date[4:]}'
    return f'{orig_date[:4]}.{orig_date[4:6]}.{orig_date[6:]}'


def _build_folder_name(date: str, label: str, title: str, best_info: tuple, suffix: str) -> str:
    if best_info[0] == 'N/A':
        return f"[{date}][{label}][{title}][{best_info[1]}]{suffix}"
    return f"[{date}][{label}][{title}][{best_info[0]}{best_info[1]}]{suffix}"


def _safe_rename(old_path: Path, new_path: Path, old_name: str, new_name: str):
    print(f"旧文件夹名：{old_name}")
    print(f"新文件夹名：{new_name}")
    old_path.rename(new_path)

# ── 公开功能函数 ──────────────────────────────────────────────────

def rename_folder_from_name():
    print('提示输入路径的时候输入$可以更改正则表达式，输入#返回主菜单')
    pattern = map_pattern(RENAME_PROMPT, RENAME_PATTERNS)

    while True:
        folder_path = PathManager.check_input_folder_path()
        if folder_path == '#':
            print('返回主菜单')
            return
        if folder_path == '$':
            pattern = map_pattern(RENAME_PROMPT, RENAME_PATTERNS)
            continue

        for folder in os.listdir(folder_path):
            match = re.match(pattern, folder)
            if not match:
                continue
            folder_full_path = os.path.join(folder_path, folder)
            suffix, label, best_info = analyze_folder_file(folder_full_path)
            date = _normalize_date(match.group(1))
            new_name = _build_folder_name(date, label, match.group(2), best_info, suffix)
            _safe_rename(folder_full_path, os.path.join(folder_path, new_name), folder, new_name)


def rename_folder_from_tag():
    print('提示输入路径的时候输入#返回主菜单')
    while True:
        folder_path = PathManager.check_input_folder_path()
        if folder_path == '#':
            print("返回主菜单")
            return

        for folder in os.listdir(folder_path):
            folder_full_path = os.path.join(folder_path, folder)
            suffix, label, best_info = analyze_folder_file(folder_full_path)

            date = album = None
            for file in os.listdir(folder_full_path):
                ext = file.lower()
                file_path = os.path.join(folder_full_path, file)
                audio = mutagen.File(file_path)
                if ext.endswith(('.flac', '.ogg')):
                    try:
                        date = '.'.join(re.split(r'[-/]', audio.tags['DATE'][0][:10]))
                    except KeyError:
                        date = '.'.join(re.split(r'[-/]', audio.tags['YEAR'][0][:10]))
                    album = PathManager.safe_filename(audio.tags['ALBUM'][0])
                    break
                elif ext.endswith(('.dsf', '.wav')):
                    try:
                        date = '.'.join(re.split(r'[-/]', str(audio.tags['TDAT'][0])[:10]))
                    except KeyError:
                        date = '.'.join(re.split(r'[-/]', str(audio.tags['TDRC'][0])[:10]))
                    album = PathManager.safe_filename(audio.tags['TALB'][0])
                    break

            if date and album:
                new_name = _build_folder_name(date, label, album, best_info, suffix)
                _safe_rename(folder_full_path, os.path.join(folder_path, new_name), folder, new_name)


def write_catno_from_folder_name():
    print('提示输入路径的时候输入$可以更改正则表达式，输入#返回主菜单')
    pattern = map_pattern(CATNO_PROMPT, CATNO_PATTERNS)

    while True:
        folder_path = PathManager.check_input_folder_path()
        if folder_path == '#':
            print('返回主菜单')
            return
        if folder_path == '$':
            pattern = map_pattern(CATNO_PROMPT, CATNO_PATTERNS)
            continue

        print('-' * 50)
        for folder in os.listdir(folder_path):
            base_folder = os.path.join(folder_path, folder)
            if not os.path.isdir(base_folder):
                continue
            result = re.match(pattern, folder)
            if not result:
                continue

            catno = result.group(1)
            if "~" in catno or '～' in catno:
                catno = unfold_catno(catno)

            print(f'为 {base_folder} 下的音频写入光盘编号')
            log_count = 0
            tmp_log_path = None

            for file in os.listdir(base_folder):
                file_lower = file.lower()
                file_path = os.path.join(base_folder, file)
                if file_lower.endswith('.flac'):
                    audio = mutagen.File(file_path)
                    audio['CATALOGNUMBER'] = catno
                    audio.save()
                elif file_lower.endswith(('.dsf', '.wav')):
                    audio = mutagen.File(file_path)
                    audio.tags.add(TXXX(encoding=Encoding.UTF8, desc='CATALOGNUMBER', text=catno))
                    audio.save()
                elif file_lower.endswith('.log'):
                    log_count += 1
                    tmp_log_path = file_path

            # log / txt 处理
            display_catno = fold_catno(catno) if isinstance(catno, list) else catno
            if log_count == 1:
                _, log_file = os.path.split(tmp_log_path)
                expected = f'{display_catno}.log'
                if log_file != expected:
                    os.rename(tmp_log_path, os.path.join(base_folder, expected))
                    print(f'将 {log_file} 改名为 {expected}')
                else:
                    print(f'{log_file} 无需改名')
            elif log_count > 1:
                print('文件夹下有多个 log 文件，不进行重命名，请手动复核')
            else:
                txt_path = os.path.join(base_folder, f'{display_catno}.txt')
                if not os.path.exists(txt_path):
                    with open(txt_path, 'w') as f:
                        f.write("")
                    print(f'因文件夹下没有 log 文件，已创建 {display_catno}.txt')
                else:
                    print(f'当前路径下已有 {display_catno}.txt')

            print('完成写入')
            print('-' * 50)
