"""图片转码任务。"""
import logging, psutil, pyvips
from pathlib import Path

from .registry import IMAGE_HANDLERS
from .format_checker import ImageFormatChecker
from .transcode_task import TranscodeTask


logger = logging.getLogger("musicbox.services.transcode.image_transcode")


class ImageTranscode(TranscodeTask):
    """图片转码任务。"""
    NAME = "图片转码"
    DESCRIPTION = "图片转码中"
    CALL_METHOD = "compress_img"

    @property
    def max_threads(self) -> int:
        # 图片压缩瓶颈在 CPU，始终使用物理核心数（不受 is_hdd 影响）
        return psutil.cpu_count(logical=False)

    def collect_tasks(self, folder_p: Path) -> list:
        # 1. 收集所有匹配扩展名的文件（按 config 规则处理封面等图片）
        png_targets = self.config["transcode"]["img_to_png_names"]
        candidates: list[Path] = []
        for p in folder_p.rglob("*"):
            if not p.is_file():
                continue

            ext = p.suffix.lower()

            if ext not in IMAGE_HANDLERS:
                continue

            if p.stat().st_size == 0:
                logger.error(f"{p}为空")
                continue

            # 根据 config 中 img_to_png_names 规则处理需转换为 png 的图片（如封面）
            if self._apply_img_png_rule(p, png_targets):
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

            if not ImageFormatChecker.check(ext, metadata, file_p):
                continue

            handler_cls = IMAGE_HANDLERS[ext]
            handler = handler_cls(file_p, self.config)
            logger.debug(f"添加{file_p}到图片转码队列中")
            tasks.append(handler)

        return tasks

    @staticmethod
    def _apply_img_png_rule(p: Path, png_targets: list[str]) -> bool:
        """按 config 中 img_to_png_names 定义的规则处理需转换为 png 的图片。

        文件名（stem，不区分大小写）命中 png_targets 中任意项时：
          - 已是目标 png 名（如 Cover.png）：跳过，不再压缩
          - 已是 png 但文件名大小写不符：重命名为目标名
          - 其它图片格式：解码后写出为目标 png，并删除原文件
        输出文件名采用 config 中书写的大小写（如配置 "Cover" -> 输出 Cover.png）。
        返回 True 表示该文件已被本规则处理（应从转码候选中排除），False 表示未命中。
        """
        stem = p.stem
        ext = p.suffix.lower()
        for target in png_targets:
            if stem.lower() != str(target).lower():
                continue
            canonical_name = f"{target}.png"
            save_p = p.parent / canonical_name
            if p.name == canonical_name:
                # 已是规范的目标 png，无需处理
                return True
            if ext == ".png":
                # 已是 png，仅修正文件名大小写
                p.rename(save_p)
                logger.debug(f"已将 {p} 重命名为 {save_p}")
                return True
            # 其它图片格式 -> 解码为 png 写出
            img = pyvips.Image.new_from_file(str(p), access="sequential")
            img.write_to_file(str(save_p))
            p.unlink()
            logger.debug(f"已将 {p} 转换为 {save_p}")
            return True
        return False
