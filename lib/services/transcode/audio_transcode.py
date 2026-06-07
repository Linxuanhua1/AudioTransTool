"""音频转码任务。"""
import logging
from pathlib import Path

from lib.services.constants import DIRECT_SPLIT_FORMATS
from .audio import AudioEncodeFormat
from .registry import AUDIO_HANDLERS
from .format_checker import AudioFormatChecker
from .transcode_task import TranscodeTask


logger = logging.getLogger("musicbox.services.transcode.audio_transcode")


class AudioTranscode(TranscodeTask):
    """音频转码任务。"""
    NAME = "音频转码"
    DESCRIPTION = "音频转码中"
    CALL_METHOD = "compress_audio"

    # 同一次运行（自定义任务流）中若也包含 split_cue，则置 True：
    # 对「支持直接分轨且存在同名 .cue」的整轨文件跳过转码，交由 split_cue 直接分轨处理。
    skip_cue_direct_split: bool = False

    def collect_tasks(self, folder_p: Path) -> list:
        # 1. 收集所有匹配扩展名的文件
        candidates: list[Path] = []
        for p in folder_p.rglob("*"):
            if not p.is_file():
                continue

            ext = p.suffix.lower()

            if ext not in AUDIO_HANDLERS:
                continue

            if p.stat().st_size == 0:
                logger.error(f"{p}为空")
                continue

            if self.skip_cue_direct_split and ext in DIRECT_SPLIT_FORMATS:
                cue_path = p.with_suffix(".cue")
                if cue_path.exists():
                    continue

            candidates.append(p)

        if not candidates:
            return []

        # 2. 批量 probe
        metadata_map = self._batch_probe(candidates)

        # 3. 用 FormatChecker 过滤并创建 handler
        tasks = []
        for file_p in candidates:
            ext = file_p.suffix.lower()
            metadata = metadata_map.get(file_p)
            encode_format = AudioFormatChecker.check(ext, metadata, file_p, self.config)

            if encode_format is AudioEncodeFormat.UNSUPPORTED:
                continue

            handler_cls = AUDIO_HANDLERS[ext]
            handler = handler_cls(file_p, self.path_manager, self.config,
                                  metadata=metadata, encode_format=encode_format)
            logger.debug(f"添加{file_p}到音频转码队列中")
            tasks.append(handler)

        return tasks
