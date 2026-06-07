from enum import Enum
from dataclasses import dataclass


class ImageType(Enum):
    Other = 0
    Icon = 1
    OtherIcon = 2
    Front = 3
    Back = 4
    Leaflet = 5
    Media = 6
    LeadArtist = 7
    Artist = 8
    Conductor = 9
    Band = 10
    Composer = 11
    Lyricist = 12
    RecordingLocation = 13
    DuringRecording = 14
    DuringPerformance = 15
    ScreenCapture = 16
    Fish = 17
    Illustration = 18
    BandLogo = 19
    PublisherLogo = 20


@dataclass(frozen=True)
class InternalImageTag:
    data: bytes
    type: ImageType | None
    desc: str | None
    mime: str | None

    def __str__(self):
        return (
            f"(图片标签: 类型={self.type}, 描述={self.desc}, "
            f"MIME={self.mime}, 数据长度={len(self.data) if self.data else 0})"
        )

    def __repr__(self):
        return (
            f"(图片标签: 类型={self.type}, 描述={self.desc}, "
            f"MIME={self.mime}, 数据长度={len(self.data) if self.data else 0})"
        )