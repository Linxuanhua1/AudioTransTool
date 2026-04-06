import mutagen
from typing import Optional, Tuple
from pathlib import Path

from lib.path_manager import PathManager
from lib.organizer.utils import separate_text


TAG_MAP = {
    '.flac': ("artist", "albumartist", "composer"),
    '.ogg':  ("artist", "albumartist", "composer"),
    '.mp3':  ("TPE1", "TPE2", "TCOM"),
    '.wav':  ("TPE1", "TPE2", "TCOM"),
    '.m4a':  ("©ART", "aART", "©wrt"),
    '.wma':  ("Author", "WM/AlbumArtist", "WM/Composer"),
}


def read_tags(audio, file_p: Path) -> Optional[Tuple]:
    """根据文件类型读取 artist / albumartist / composer 的键名和当前值。"""
    ext = file_p.suffix
    if ext not in TAG_MAP:
        print(f'不支持的格式，文件为 {file_p}')
        return None

    artist_key, albumartist_key, composer_key = TAG_MAP[ext]

    if ext == '.wma':
        return (
            artist_key, albumartist_key, composer_key,
            [i.value for i in audio.get(artist_key, [])],
            [i.value for i in audio.get(albumartist_key, [])],
            [i.value for i in audio.get(composer_key, [])],
        )
    return (
        artist_key, albumartist_key, composer_key,
        audio.get(artist_key, []),
        audio.get(albumartist_key, []),
        audio.get(composer_key, []),
    )


def update_tags(file_p: Path) -> Optional[Tuple]:
    """处理并更新单个音频文件的标签，返回撤回所需的原始数据。"""
    try:
        audio = mutagen.File(file_p)
        result = read_tags(audio, file_p)
        if result is None:
            return None

        artist_key, albumartist_key, composer_key, old_artist, old_albumartist, old_composer = result
        new_artist = separate_text(old_artist)
        new_albumartist = separate_text(old_albumartist)
        new_composer = separate_text(old_composer)

        if new_artist == old_artist and new_albumartist == old_albumartist and new_composer == old_composer:
            print(f"{file_p} 无需修改")
            return None

        print(f"修改前 [{file_p}]:\n  Artist: {old_artist}\n  Album Artist: {old_albumartist}\n  Composer: {old_composer}")
        audio[artist_key] = new_artist
        audio[albumartist_key] = new_albumartist
        audio[composer_key] = new_composer
        audio.save()

        _, _, _, updated_artist, updated_albumartist, updated_composer = read_tags(audio, file_p)
        print(f"修改后 [{file_p}]:\n  Artist: {updated_artist}\n  Album Artist: {updated_albumartist}\n  Composer: {updated_composer}")
        print("-" * 50)

        return file_p, artist_key, albumartist_key, composer_key, old_artist, old_albumartist, old_composer

    except Exception as e:
        print(f"[错误] 处理文件 {file_p} 时出错: {e}")
        return None


def process_directory_separate(folder_p: Path):
    """递归处理目录下所有音频文件的标签分割，处理完后询问是否撤回。"""
    modified_files = []

    for p in folder_p.rglob('*'):
        if p.suffix.lower().endswith(tuple(TAG_MAP.keys())):
            result = update_tags(p)
            if result:
                modified_files.append(result)

    if modified_files:
        if input("是否撤回修改？(y/n): ").strip().lower() == 'y':
            for file_path, artist_key, albumartist_key, composer_key, old_artist, old_albumartist, old_composer in modified_files:
                audio = mutagen.File(file_path)
                audio[artist_key] = old_artist
                audio[albumartist_key] = old_albumartist
                audio[composer_key] = old_composer
                audio.save()
                print(f"已撤回{file_path}的修改")


def separate_tag():
    print("询问输入文件夹的时候，输入#返回主菜单")
    while True:
        folder_p = PathManager.check_input_folder_path()
        if folder_p == '#':
            print('返回主菜单')
            return
        process_directory_separate(folder_p)
