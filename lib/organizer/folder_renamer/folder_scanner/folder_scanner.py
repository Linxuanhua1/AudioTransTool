from pathlib import Path
from collections import Counter
from jinja2 import Template

from lib.constants import IMAGE_FORMATS, AUDIO_FORMAT_ORDER, ALLOWED_READ_AUDIO_FORMAT
from .scan_models import ScanResult, FolderStatus
from .audio_info import AudioSource, AudioQuality


class FolderScanner:
    @staticmethod
    def analyze(folder_p: Path, threshold: int,
                folder_content_template: Template, standard_tag: dict[str, set]) -> ScanResult:
        """扫描文件夹并返回完整的 ScanResult。"""
        status, audio_files = FolderScanner.scan(folder_p, threshold)
        quality_str, found_formats = AudioQuality.get_all_audio_qualities(audio_files)
        suffix = FolderScanner.build_suffix(found_formats, status, folder_content_template)
        src, score = AudioSource.detect_source(status, folder_p, standard_tag)
        return ScanResult(folder_content=suffix, source=src, score=score, quality=quality_str,
                          found_formats=found_formats, status=status)

    @staticmethod
    def scan(folder_p: Path, threshold: int) -> tuple[FolderStatus, list[Path]]:
        """递归扫描文件夹，返回 (FolderStatus, [audio_file_paths])。"""
        status = FolderStatus()
        audio_files: list[Path] = []
        image_counter = Counter[str]()  # 统计每种图片格式的数量

        for p in folder_p.rglob("*"):
            ext = p.suffix.lower()
            
            # 统计图片格式
            if ext in IMAGE_FORMATS:
                # 标准化扩展名（.jpg 和 .jpeg 统一为 .jpg）
                normalized_ext = ".jpg" if ext == ".jpeg" else ext
                image_counter[normalized_ext] += 1
            
            match ext:
                case ".log":
                    status.has_log = True
                case ".iso" | ".vob" | ".bdmv":
                    status.has_iso = True
                case ".mkv":
                    status.has_mkv = True
                case ".mp4":
                    status.has_mp4 = True

            if ext in ALLOWED_READ_AUDIO_FORMAT:
                audio_files.append(p)
        
        # 根据阈值判断哪些格式是 booklet
        status.booklet_formats = {
            fmt for fmt, count in image_counter.items() 
            if count >= threshold
        }
        
        return status, audio_files

    @staticmethod
    def build_suffix(found_formats: set[str], status: FolderStatus, folder_content_template: Template) -> str:
        """构建形如 flac+dsf+iso+jpg+png 的后缀字符串。"""
        # 音频格式按优先级排序
        audio_parts = sorted( (fmt[1:] for fmt in found_formats), key=lambda x: AUDIO_FORMAT_ORDER.get(f".{x}", 999), )
        audio_parts = "+".join(audio_parts)
        # 视频格式
        video_parts = [ fmt for fmt, flag in [ ("mp4", status.has_mp4), ("mkv", status.has_mkv), ] if flag ]
        video_parts = "+".join(video_parts)
        # ISO 格式
        iso_parts = "iso" if status.has_iso else ''
        # Booklet 图片格式（按字母顺序）
        booklet_parts = sorted(fmt[1:] for fmt in status.booklet_formats)
        booklet_parts = "+".join(booklet_parts)
        suffix = folder_content_template.render(audio_parts=audio_parts, video_parts=video_parts, iso_parts=iso_parts, booklet_parts=booklet_parts)
        return suffix

