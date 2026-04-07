import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import mutagen
from mutagen.id3 import TXXX, Encoding


@dataclass
class TagBundle:
    """单个音频文件的标签快照，用于读取与回滚。"""
    file_path: Path
    artist:       list[str] = field(default_factory=list)
    albumartist:  list[str] = field(default_factory=list)
    composer:     list[str] = field(default_factory=list)
    date:         str = ""
    album:        str = ""
    catno:        str | list[str] = ""
    album_id:     str = ""
    comment:      str = ""
    # 来源探测用的额外字段
    qbz_tid:      Optional[str] = None
    url:          str = ""
    merchant:     str = ""


# 每种格式对应 (artist_key, albumartist_key, composer_key)
_TAG_KEYS: dict[str, tuple[str, str, str]] = {
    ".flac": ("artist",      "albumartist",    "composer"),
    ".ogg":  ("artist",      "albumartist",    "composer"),
    ".mp3":  ("TPE1",        "TPE2",           "TCOM"),
    ".wav":  ("TPE1",        "TPE2",           "TCOM"),
    ".dsf":  ("TPE1",        "TPE2",           "TCOM"),
    ".m4a":  ("©ART",        "aART",           "©wrt"),
    ".wma":  ("Author",      "WM/AlbumArtist", "WM/Composer"),
}

_VORBIS_EXTS  = {".flac", ".ogg"}
_ID3_EXTS     = {".mp3", ".wav", ".dsf"}
_M4A_EXTS     = {".m4a"}
_WMA_EXTS     = {".wma"}


class AudioTagReader:
    """
    无状态工具类——所有方法均为静态/类方法。

    用法示例
    --------
    bundle = AudioTagReader.read(Path("track.flac"))
    AudioTagReader.write_catno(Path("track.flac"), "ABCD-1234")
    AudioTagReader.write_album_id(Path("track.flac"), "some-uuid")
    AudioTagReader.restore(bundle)
    """

    @staticmethod
    def read(file_path: Path) -> Optional[TagBundle]:
        """
        读取单个文件的标签，返回 TagBundle；格式不支持则返回 None。
        """
        ext = file_path.suffix.lower()
        if ext not in _TAG_KEYS:
            print(f"[AudioTagReader] 不支持的格式：{file_path}")
            return None

        try:
            audio = mutagen.File(str(file_path))
        except Exception as e:
            print(f"[AudioTagReader] 无法打开 {file_path}：{e}")
            return None

        if audio is None:
            return None

        bundle = TagBundle(file_path=file_path)
        artist_k, albumartist_k, composer_k = _TAG_KEYS[ext]

        if ext in _VORBIS_EXTS:
            bundle.artist       = audio.get(artist_k, [])
            bundle.albumartist  = audio.get(albumartist_k, [])
            bundle.composer     = audio.get(composer_k, [])
            bundle.album        = audio.tags.get("ALBUM",  [""])[0] if audio.tags else ""
            bundle.catno        = audio.tags.get("CATALOGNUMBER", [""])[0] if audio.tags else ""
            bundle.comment      = audio.tags.get("COMMENT", [""])[0] if audio.tags else ""
            bundle.qbz_tid      = audio.tags.get("QBZ:TID",   [None])[0] if audio.tags else None
            bundle.url          = audio.tags.get("URL",        [""])[0]  if audio.tags else ""
            bundle.merchant     = audio.tags.get("MERCHANTNAME", [""])[0] if audio.tags else ""

            raw_date = (audio.tags.get("DATE") or audio.tags.get("YEAR") or [""])[0] if audio.tags else ""
            bundle.date = ".".join(re.split(r"[-/]", raw_date[:10])) if raw_date else ""

        elif ext in _ID3_EXTS:
            tags = audio.tags or {}
            bundle.artist       = [str(tags[artist_k][0])]      if artist_k      in tags else []
            bundle.albumartist  = [str(tags[albumartist_k][0])] if albumartist_k in tags else []
            bundle.composer     = [str(tags[composer_k][0])]    if composer_k    in tags else []
            bundle.album        = str(tags["TALB"][0]) if "TALB" in tags else ""

            txxx_catno = tags.get("TXXX:CATALOGNUMBER")
            bundle.catno = str(txxx_catno[0]) if txxx_catno else ""

            txxx_mbid = tags.get("TXXX:MusicBrainz Album Id")
            bundle.album_id = str(txxx_mbid[0]) if txxx_mbid else ""

            # DSF COMMENT 用 COMM 帧；WAV/MP3 通常也是 COMM
            try:
                bundle.comment = str(tags.getall("COMM")[0]) if hasattr(tags, "getall") else ""
            except (IndexError, AttributeError):
                bundle.comment = ""

            raw_date = (str(tags["TDRC"][0]) if "TDRC" in tags
                        else str(tags["TDAT"][0]) if "TDAT" in tags else "")
            bundle.date = ".".join(re.split(r"[-/]", raw_date[:10])) if raw_date else ""

        elif ext in _M4A_EXTS:
            bundle.artist       = audio.get(artist_k, [])
            bundle.albumartist  = audio.get(albumartist_k, [])
            bundle.composer     = audio.get(composer_k, [])

        elif ext in _WMA_EXTS:
            bundle.artist       = [i.value for i in audio.get(artist_k, [])]
            bundle.albumartist  = [i.value for i in audio.get(albumartist_k, [])]
            bundle.composer     = [i.value for i in audio.get(composer_k, [])]

        return bundle


    @staticmethod
    def write_people_tags(
        file_path: Path,
        artist: list[str],
        albumartist: list[str],
        composer: list[str],
    ) -> bool:
        """写入 artist / albumartist / composer，返回是否成功。"""
        ext = file_path.suffix.lower()
        if ext not in _TAG_KEYS:
            return False

        try:
            audio = mutagen.File(str(file_path))
            artist_k, albumartist_k, composer_k = _TAG_KEYS[ext]
            audio[artist_k]      = artist
            audio[albumartist_k] = albumartist
            audio[composer_k]    = composer
            audio.save()
            return True
        except Exception as e:
            print(f"[AudioTagReader] 写入失败 {file_path}：{e}")
            return False

    @staticmethod
    def write_catno(file_path: Path, catno: str | list[str]) -> bool:
        """写入 CATALOGNUMBER，自动适配格式。"""
        ext = file_path.suffix.lower()
        try:
            audio = mutagen.File(str(file_path))
            if ext in _VORBIS_EXTS:
                audio["CATALOGNUMBER"] = catno
            elif ext in _ID3_EXTS:
                audio.tags.add(TXXX(encoding=Encoding.UTF8, desc="CATALOGNUMBER", text=catno))
            else:
                print(f"[AudioTagReader] write_catno 不支持 {ext}")
                return False
            audio.save()
            return True
        except Exception as e:
            print(f"[AudioTagReader] write_catno 失败 {file_path}：{e}")
            return False

    @staticmethod
    def write_album_id(file_path: Path, album_id: str) -> bool:
        """写入 MusicBrainz Album Id，自动适配格式。"""
        ext = file_path.suffix.lower()
        try:
            audio = mutagen.File(str(file_path))
            if ext in _VORBIS_EXTS:
                audio["MUSICBRAINZ_ALBUMID"] = album_id
            elif ext in _ID3_EXTS:
                audio.tags.add(TXXX(encoding=Encoding.UTF8, desc="MusicBrainz Album Id", text=album_id))
            else:
                print(f"[AudioTagReader] write_album_id 不支持 {ext}")
                return False
            audio.save()
            return True
        except Exception as e:
            print(f"[AudioTagReader] write_album_id 失败 {file_path}：{e}")
            return False

    @staticmethod
    def restore(bundle: TagBundle) -> bool:
        """将 TagBundle 中保存的人物标签写回文件，用于撤回操作。"""
        return AudioTagReader.write_people_tags(
            bundle.file_path,
            bundle.artist,
            bundle.albumartist,
            bundle.composer,
        )

    @staticmethod
    def supported_extensions() -> frozenset[str]:
        return frozenset(_TAG_KEYS.keys())
