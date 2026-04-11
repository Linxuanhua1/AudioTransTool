import pyvips, subprocess, logging
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from lib.common import probe


logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    def __init__(self, message: str, output_path: Path | None = None):
        super().__init__(message)
        self.output_path = output_path


class ImageHandler(ABC):
    def __init__(self, file_p, config):
        self.file_p: Path = file_p
        self.out_p: Path = file_p.with_suffix(".jxl")
        self.is_del_src_img = config["is_del_src_img"]

    @abstractmethod
    def _is_enc2jxl(self) -> bool:
        pass

    @abstractmethod
    def compress_img(self):
        pass

    @contextmanager
    def _processing_guard(self, *output_paths: Path) -> Generator[None, None, None]:
        try:
            yield
        except ImageProcessingError as e:
            for p in output_paths:
                p.unlink(missing_ok=True)
                logger.debug(f"已删除不完整的输出文件：{p}")
            logger.error(str(e))

    @staticmethod
    def _run_jxl_encode(cmd, file_p: Path, out_p: Path):
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
        except subprocess.CalledProcessError as e:
            logger.error(e.stderr)
            raise ImageProcessingError(f"未能成功将 {file_p} 编码为 jxl", out_p)

    def _reencode2jxl_via_png(self):
        """解码为 png 后编码为 jxl，返回临时 png 路径供 guard 清理。"""
        logger.debug(f"正在将 {self.file_p} 转换为 jxl")
        tmp_png_p = self._decode_img()
        cmd = ['cjxl', '-j', '1', '--container', '1', '-q', '100', '--num_threads=16', tmp_png_p, self.out_p]
        self._run_jxl_encode(cmd, self.file_p, self.out_p)

    def _reencode_file2jxl(self):
        cmd = ['cjxl', '-j', '1', '--container', '1', '-q', '100', '--num_threads=16', self.file_p, self.out_p]
        self._run_jxl_encode(cmd, self.file_p, self.out_p)

    def _transfer_metadata(self):
        logger.debug(f"正在将 {self.file_p} 的元数据转移到 {self.out_p}")
        try:
            cmd = ['exiftool', '-@', '-']
            args = '\n'.join(['-m', '-overwrite_original', '-tagsFromFile', str(self.file_p), '-all:all', str(self.out_p)])
            subprocess.run(cmd, input=args, text=True, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(e.stderr)
            raise ImageProcessingError(f"将 {self.file_p} 的元数据转移到 {self.out_p} 失败", self.out_p)
        logger.debug(f"成功将 {self.file_p} 的元数据转移到 {self.out_p}")

    def _decode_img(self) -> Path:
        logger.debug(f"正在将 {self.file_p} 解码为 png 缓存")
        tmp_png_p = self.file_p.with_suffix(".png")
        try:
            img = pyvips.Image.new_from_file(str(self.file_p), access="sequential")
            img.write_to_file(str(tmp_png_p))
        except Exception as e:
            raise ImageProcessingError(f"将 {self.file_p} 解码为 png 失败：{e}", tmp_png_p)
        logger.debug(f"成功将 {self.file_p} 解码为 png 缓存")
        return tmp_png_p

    def _finalize_output(self):
        self._transfer_metadata()
        if self.is_del_src_img:
            self.file_p.unlink(missing_ok=True)
            logger.info(f"成功删除 {self.file_p}")


class TiffHandler(ImageHandler):
    def _is_enc2jxl(self) -> bool:
        metadata = probe(self.file_p)
        color_space = int(metadata['PhotometricInterpretation'])
        bit_depth = int(metadata['BitsPerSample'].split(" ")[0])
        if color_space in (0, 1, 2, 3, 4, 6) and bit_depth in (8, 16, 32):
            return True
        logger.error(f"{self.file_p} 不支持转换为 jxl")
        return False

    def compress_img(self):
        if not self._is_enc2jxl():
            return
        tmp_png_p = self.file_p.with_suffix(".png")
        with self._processing_guard(tmp_png_p, self.out_p):
            self._reencode2jxl_via_png()
            self._finalize_output()
            tmp_png_p.unlink(missing_ok=True)  # 成功时也要清理临时 png


class WebpHandler(ImageHandler):
    def _is_enc2jxl(self) -> bool:
        pass

    def compress_img(self):
        tmp_png_p = self.file_p.with_suffix(".png")
        with self._processing_guard(tmp_png_p, self.out_p):
            self._reencode2jxl_via_png()
            self._finalize_output()
            tmp_png_p.unlink(missing_ok=True)  # 成功时也要清理临时 png


class BmpHandler(ImageHandler):
    def _is_enc2jxl(self) -> bool:
        pass

    def compress_img(self):
        tmp_png_p = self.file_p.with_suffix(".png")
        with self._processing_guard(tmp_png_p, self.out_p):
            self._reencode2jxl_via_png()
            self._finalize_output()
            tmp_png_p.unlink(missing_ok=True)  # 成功时也要清理临时 png


class JpgHandler(ImageHandler):
    def _is_enc2jxl(self) -> bool:
        metadata = probe(self.file_p)
        color_components = len(metadata["BitsPerSample"].split(" "))
        if color_components in (1, 3):
            return True
        logger.error(f"{self.file_p} 不支持转换为 jxl（颜色分量数：{color_components}）")
        return False

    def compress_img(self):
        if not self._is_enc2jxl():
            return

        with self._processing_guard(self.out_p):
            self._reencode_file2jxl()
            self._finalize_output()


class PngHandler(ImageHandler):
    def _is_enc2jxl(self) -> bool:
        pass

    def compress_img(self):
        with self._processing_guard(self.out_p):
            self._reencode_file2jxl()
            self._finalize_output()