from dataclasses import dataclass, field

@dataclass
class FolderStatus:
    has_log:  bool = False
    has_iso:  bool = False
    has_mp4:  bool = False
    has_mkv:  bool = False
    booklet_formats: set[str] = field(default_factory=set)  # 存储 booklet 图片格式


@dataclass
class ScanResult:
    """analyze() 的完整返回值，供上层直接使用。"""
    folder_content:        str = ""
    source:                str = ""
    score:                 str = ""
    quality:               str = ""  # 所有质量用+连接
    found_formats:         set[str] = field(default_factory=set)
    status:                FolderStatus = field(default_factory=FolderStatus)

    def to_dict(self) -> dict:
        return {
            "FOLDER_CONTENT": self.folder_content,
            "SOURCE": self.source,
            "SCORE": self.score,
            "QUALITY": self.quality,
            "FOUND_FORMATS": self.found_formats,
            "STATUS": self.status,
        }