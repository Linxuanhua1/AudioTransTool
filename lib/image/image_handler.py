import pyvips, subprocess, logging
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    def __init__(self, message: str, output_path: Path | None = None):
        super().__init__(message)
        self.output_path = output_path


class ImageHandler(ABC):
    def __init__(self, file_p, config):
        self.file_p: Path = file_p
        self.out_p: Path = file_p.with_suffix(".jxl")
        self.is_del_src_img = config['transcode']["is_del_src_img"]

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
        except KeyboardInterrupt as e:
            for p in output_paths:
                p.unlink(missing_ok=True)
                logger.debug(f"用户手动停止，已删除不完整的输出文件：{p}")

    @staticmethod
    def _run_jxl_encode(cmd, file_p: Path, out_p: Path, img_bytes: bytes):
        try:
            subprocess.run(cmd, capture_output=True, check=True, input=img_bytes)
        except subprocess.CalledProcessError as e:
            logger.error(e.stderr)
            raise ImageProcessingError(f"未能成功将 {file_p} 编码为 jxl", out_p)

    def _reencode2jxl_via_png(self):
        """解码为 png 后编码为 jxl，返回临时 png 路径供 guard 清理。"""
        logger.debug(f"正在将 {self.file_p} 转换为 jxl")
        tmp_png_bytes = self._decode_img()
        cmd = ['cjxl', '-j', '1', '--container', '1', '-q', '100', '--num_threads=16', '-', self.out_p]
        self._run_jxl_encode(cmd, self.file_p, self.out_p, tmp_png_bytes)

    def _reencode_file2jxl(self):
        img_bytes = self.file_p.read_bytes()
        cmd = ['cjxl', '-j', '1', '--container', '1', '-q', '100', '--num_threads=16', '-', self.out_p]
        self._run_jxl_encode(cmd, self.file_p, self.out_p, img_bytes)

    def _transfer_metadata(self):
        logger.debug(f"正在将 {self.file_p} 的元数据转移到 {self.out_p}")
        try:
            cmd = ['exiftool', '-@', '-']
            args = '\n'.join(['-m', '-overwrite_original', '-tagsFromFile', str(self.file_p), '-all:all', str(self.out_p)])
            subprocess.run(cmd, input=args, text=True, check=True, capture_output=True, encoding='utf-8')
        except subprocess.CalledProcessError as e:
            logger.error(e.stderr)
            raise ImageProcessingError(f"将 {self.file_p} 的元数据转移到 {self.out_p} 失败", self.out_p)
        logger.debug(f"成功将 {self.file_p} 的元数据转移到 {self.out_p}")

    def _decode_img(self) -> bytes:
        logger.debug(f"正在将 {self.file_p} 解码为 png 缓存")
        try:
            img  = pyvips.Image.new_from_file(str(self.file_p), access="sequential")
            png_img = img.pngsave_buffer()
        except Exception as e:
            raise ImageProcessingError(f"将 {self.file_p} 解码为 png 失败")
        logger.debug(f"成功将 {self.file_p} 解码为 png 缓存")
        return png_img

    def _finalize_output(self):
        self._transfer_metadata()
        if self.is_del_src_img:
            self.file_p.unlink(missing_ok=True)
            logger.debug(f"成功删除 {self.file_p}")
        logger.info(f"成功将{self.file_p}转换为jxl")


class TiffHandler(ImageHandler):
    def compress_img(self):
        with self._processing_guard(self.out_p):
            self._reencode2jxl_via_png()
            self._finalize_output()


class WebpHandler(ImageHandler):
    def compress_img(self):
        with self._processing_guard(self.out_p):
            self._reencode2jxl_via_png()
            self._finalize_output()


class BmpHandler(ImageHandler):
    def compress_img(self):
        with self._processing_guard(self.out_p):
            self._reencode2jxl_via_png()
            self._finalize_output()


class JpgHandler(ImageHandler):
    def compress_img(self):
        with self._processing_guard(self.out_p):
            self._reencode_file2jxl()
            self._finalize_output()


class PngHandler(ImageHandler):
    def compress_img(self):
        with self._processing_guard(self.out_p):
            self._reencode_file2jxl()
            self._finalize_output()
