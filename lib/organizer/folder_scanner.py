import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from lib.audio.audio_handler import probe
from lib.organizer.audio_tag_reader import AudioTagReader


# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #

PRIORITY_ORDER = [".dsf", ".wav", ".flac", ".m4a", ".mp3", ".ogg", '.wma']

AUDIO_TYPE_QUALITY: dict[str, int] = {
    ".dsf": 4,
    '.wv': 3,
    ".wav": 3,
    '.aiff': 3,
    ".flac": 2,
    ".m4a": 1,
    ".mp3": 1,
    ".ogg": 1,
    '.wma': 1
}

_DSD_RATE_MAP = {
    "2.8224":  "DSD64",
    "5.6448":  "DSD128",
    "11.2896": "DSD256",
    "22.5792": "DSD512",
    "45.1584": "DSD1024",
}

_COMMENT_SOURCE_MAP = {
    "jasrac /": "MORA",
    "ototoy":   "OTOTOY",
    "bandcamp": "Bandcamp",
}


@dataclass
class FolderStatus:
    has_log:  bool = False
    has_pic:  bool = False
    has_iso:  bool = False
    has_bdmv: bool = False
    has_mp4:  bool = False
    has_mkv:  bool = False


@dataclass
class ScanResult:
    """analyze() 的完整返回值，供上层直接使用。"""
    suffix:        str = ""
    label:         str = ""
    best_info:     tuple[str, str] = ("N/A", "N/A")
    found_formats: set[str] = field(default_factory=set)
    status:        FolderStatus = field(default_factory=FolderStatus)


class FolderScanner:
    """
    无状态工具类，所有方法为静态方法。

    用法
    ----
    result = FolderScanner.analyze(folder_path)
    # result.suffix / result.label / result.best_info
    """


    @staticmethod
    def analyze(folder_p: Path) -> ScanResult:
        """扫描文件夹并返回完整的 ScanResult。"""
        status, audio_files = FolderScanner.scan(folder_p)
        best_info, found_formats = FolderScanner.get_best_audio_info(audio_files)
        suffix = FolderScanner.build_suffix(found_formats, status)
        label  = FolderScanner.determine_label(status, best_info, folder_p)
        return ScanResult(
            suffix=suffix,
            label=label,
            best_info=best_info,
            found_formats=found_formats,
            status=status,
        )

    # ------------------------------------------------------------------ #
    # 扫描文件
    # ------------------------------------------------------------------ #

    @staticmethod
    def scan(folder_path: Path) -> tuple[FolderStatus, list[tuple[str, Path]]]:
        """递归扫描文件夹，返回 (FolderStatus, [(ext, full_path), ...])。"""
        status = FolderStatus()
        audio_files: list[tuple[str, Path]] = []

        for p in folder_path.rglob("*"):
            ext = p.suffix

            match ext:
                case ".jxl":
                    status.has_pic = True
                case ".log":
                    status.has_log = True
                case ".iso" | ".vob" | ".bdmv":
                    status.has_iso = True
                case ".mkv":
                    status.has_mkv = True
                case ".mp4":
                    status.has_mp4 = True

            if ext in AUDIO_TYPE_QUALITY:
                audio_files.append((ext, p))

        return status, audio_files

    # ------------------------------------------------------------------ #
    # 最佳音质
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_best_audio_info(
        audio_files: list[tuple[str, Path]],
    ) -> tuple[tuple[str, str], set[str]]:
        """
        按优先级选出最佳音频，返回 (best_info, found_formats)。
        best_info = (bit_depth_or_N/A, sample_rate_or_bitrate)
        """
        best_quality = -1
        best_info: tuple[str, str] = ("N/A", "N/A")
        found_formats: set[str] = set()

        for ext in PRIORITY_ORDER:
            for file_ext, file_p in audio_files:
                if file_ext != ext:
                    continue
                found_formats.add(file_ext)
                if AUDIO_TYPE_QUALITY[file_ext] <= best_quality:
                    break

                info = probe(file_p)
                best_info = FolderScanner._parse_probe(ext, info)
                best_quality = AUDIO_TYPE_QUALITY[file_ext]
                break

        return best_info, found_formats

    @staticmethod
    def _parse_probe(ext: str, info: dict) -> tuple[str, str]:
        if ext == ".flac":
            sr    = f"{Decimal(int(info['sample_rate'])) / 1000}kHz"
            depth = f"{int(info['bits_per_raw_sample'])}bit"
            return depth, sr
        if ext == ".wav":
            sr    = f"{Decimal(int(info['sample_rate'])) / 1000}kHz"
            depth = f"{int(info['bits_per_sample'])}bit"
            return depth, sr
        if ext in {".m4a", ".mp3", ".ogg"}:
            br = f"{round(Decimal(int(info['bit_rate'])) / 1000)}k"
            return "N/A", br
        if ext == ".dsf":
            key = str(Decimal(int(info["bit_rate"])) / 2_000_000)
            label = _DSD_RATE_MAP.get(key, key)
            return "N/A", label
        return "N/A", "N/A"

    # ------------------------------------------------------------------ #
    # 后缀拼接
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_suffix(found_formats: set[str], status: FolderStatus) -> str:
        """构建形如 [flac+dsf+iso] 的后缀字符串。"""
        parts = sorted(
            [fmt[1:] for fmt in found_formats],
            key=lambda x: PRIORITY_ORDER.index("." + x),
        )
        if status.has_mp4:
            parts.append("mp4")
        if status.has_mkv:
            parts.append("mkv")
        if status.has_bdmv:
            parts.append("bdmv")
        if status.has_iso:
            parts.append("iso")
        if status.has_pic:
            parts.append("jxl")
        return "[" + "+".join(parts) + "]"

    # ------------------------------------------------------------------ #
    # 来源标签
    # ------------------------------------------------------------------ #

    @staticmethod
    def determine_label(
        status: FolderStatus,
        best_info: tuple[str, str],
        folder_p: Path,
    ) -> str:
        """判断音频来源，返回标签字符串（EAC / e-onkyo / MORA / Qobuz ...）。"""
        if status.has_log:
            return "EAC"
        if best_info[0] == "32bit":
            return "e-onkyo"
        return FolderScanner.detect_source(folder_p)

    @staticmethod
    def detect_source(folder_path: Path) -> str:
        """逐文件检查标签，推断在线音源。"""
        for file in os.listdir(folder_path):
            ext = file.lower()
            file_path = os.path.join(folder_path, file)

            if ext.endswith((".wma", ".mp3", ".ogg", ".m4a")):
                return "WEB"

            if not ext.endswith((".wav", ".flac", ".dsf")):
                continue

            bundle = AudioTagReader.read(Path(file_path))
            if bundle is None:
                return "WEB"

            # Vorbis / ID3 共用字段（AudioTagReader 已统一填充）
            if bundle.qbz_tid:
                return "Qobuz"
            if "tidal" in bundle.url.lower():
                return "Tidal"
            if "amazon" in bundle.merchant.lower():
                return "Amazon"

            comment_lower = bundle.comment.lower()
            for key, value in _COMMENT_SOURCE_MAP.items():
                if key in comment_lower:
                    return value

            if ext.endswith(".dsf"):
                return "ISO转DSF"

            return "WEB"

        return "WEB"
