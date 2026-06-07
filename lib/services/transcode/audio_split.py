"""音频分轨任务（按 cue 切分整轨）。"""
import logging
from pathlib import Path

from lib.services.constants import DIRECT_SPLIT_FORMATS, AUDIO_EXT2CLI_CMD
from .audio import Splitter, AudioEncodeFormat
from .format_checker import AudioFormatChecker
from .transcode_task import TranscodeTask


logger = logging.getLogger("musicbox.services.transcode.audio_split")


class AudioSplit(TranscodeTask):
    """音频分轨任务（按 cue 切分整轨）。"""
    NAME = "音频分轨"
    DESCRIPTION = "音频分轨中"
    CALL_METHOD = "split_with_cue"

    def collect_tasks(self, folder_p: Path) -> list:
        # 1. 收集所有匹配扩展名的文件
        candidates: list[Path] = []
        for p in folder_p.rglob("*"):
            if not p.is_file():
                continue

            ext = p.suffix.lower()
            if ext not in DIRECT_SPLIT_FORMATS:
                continue

            if p.stat().st_size == 0:
                logger.error(f"{p}为空")
                continue

            cue_path = p.with_suffix(".cue")
            if cue_path.exists():
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

            if ext == ".flac":
                encode_format = AudioEncodeFormat.FLAC
            else:
                encode_format = AudioFormatChecker.check(ext, metadata, file_p, self.config)

            if encode_format is not AudioEncodeFormat.FLAC:
                continue

            cmd = AUDIO_EXT2CLI_CMD.get(ext, None)
            logger.debug(f"添加{file_p}到音频分轨队列中")
            tasks.append(Splitter(file_p, self.path_manager, self.config, cmd))

        return tasks
