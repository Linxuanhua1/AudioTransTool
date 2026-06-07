"""转码任务基类。

封装三类转码任务（AudioTranscode / AudioSplit / ImageTranscode）共用的逻辑：
线程数策略、批量 probe、并发执行。子类通过类属性声明
NAME / DESCRIPTION / CALL_METHOD，并实现 collect_tasks 收集本类型的待处理任务。
"""
import concurrent.futures, logging, psutil
from pathlib import Path
from operator import methodcaller
from typing import Any
from tqdm import tqdm
from abc import ABC, abstractmethod

from lib.utils import PathManager, MediaProbe


logger = logging.getLogger("musicbox.services.transcode.transcode_task")


class TranscodeTask(ABC):
    """转码任务基类。

    封装三类任务共用的逻辑：线程数策略、批量 probe、并发执行。
    子类通过类属性声明 NAME / DESCRIPTION / CALL_METHOD，
    并实现 collect_tasks 收集待处理的 handler 列表。
    """
    NAME: str = ""             # 显示名
    DESCRIPTION: str = ""      # 进度条描述
    CALL_METHOD: str = ""      # 在收集到的 handler 上要调用的方法名

    def __init__(self, config: dict[str, Any], path_manager: PathManager):
        self.config = config
        self.path_manager = path_manager

    @property
    def max_threads(self) -> int:
        """音频处理瓶颈在硬盘：hdd 时单线程，ssd 时为物理核心数。"""
        return 1 if self.config["transcode"]["is_hdd"] else psutil.cpu_count(logical=False)

    @abstractmethod
    def collect_tasks(self, folder_p: Path) -> list:
        """收集本类型在 folder_p 下的待处理任务（handler 列表）。"""
        ...

    def process(self, folder_p: Path) -> None:
        """收集并并发执行本类型任务。"""
        logger.info(f"{self.NAME}任务开始")
        tasks = self.collect_tasks(folder_p)
        if tasks:
            logger.info(f"找到 {len(tasks)} 个{self.NAME}任务")
            call_func = methodcaller(self.CALL_METHOD)
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                list(tqdm(
                    executor.map(call_func, tasks),
                    total=len(tasks),
                    desc=self.DESCRIPTION
                ))
        else:
            logger.info(f"没有符合条件的{self.NAME}任务")
        logger.info(f"{self.NAME}任务结束")

    @staticmethod
    def _batch_probe(paths: list[Path]) -> dict[Path, dict]:
        """批量 probe 文件，返回 {路径: 元数据} 映射"""
        results = MediaProbe.probe(paths)
        if not results:
            return {}

        metadata_map: dict[Path, dict] = {}
        for item in results:
            source = Path(item["SourceFile"])
            metadata_map[source] = item

        return metadata_map
