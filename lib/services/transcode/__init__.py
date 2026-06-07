"""转码服务包：对外导出三个任务类、共享基类，以及 任务名 -> 任务类 注册表。

环已被打破（utils / constants 均为叶子，tags 不依赖 transcode），故此处可安全 eager 导出。
"""
from .transcode_task import TranscodeTask
from .audio_transcode import AudioTranscode
from .audio_split import AudioSplit
from .image_transcode import ImageTranscode


# config 中 task_pipeline 使用的 transcode 任务名 -> 任务类 映射
TASK_NAME_TO_CLASS = {
    "audio_transcode": AudioTranscode,
    "split_cue": AudioSplit,
    "image_transcode": ImageTranscode,
}

__all__ = [
    "TranscodeTask",
    "AudioTranscode",
    "AudioSplit",
    "ImageTranscode",
    "TASK_NAME_TO_CLASS",
]
