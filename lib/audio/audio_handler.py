import subprocess, struct, logging, mutagen
from pathlib import Path
from collections.abc import Generator
from contextlib import contextmanager
from enum import Enum, auto
from abc import ABC, abstractmethod

from lib.tags.transfer import TagsTransfer
from lib.constants import (CMD_WAVPACK2WAVBYTES, CMD_APE2WAVBYTES, CMD_TAK2WAVBYTES, CMD_TTA2WAVBYTES,
                           CMD_BYTES2WV, CMD_M4A2WAVBYTES, CMD_WAVBYTES2FLAC, CMD_PCMBYTES2FLAC)
from lib.common.path_manager import PathManager

logger = logging.getLogger(__name__)


class AudioEncodeFormat(Enum):
    FLAC = auto()
    WAVEPACK = auto()
    UNSUPPORTED = auto()


class AudioProcessingError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class AudioHandler(ABC):
    def __init__(self, file_p: Path, path_manager: PathManager, config,
                 metadata: dict | None = None, encode_format: AudioEncodeFormat = AudioEncodeFormat.UNSUPPORTED):
        self.file_p: Path = file_p
        self.path_manager: PathManager = path_manager
        self.out_p: Path | None = None
        self.metadata: dict | None = metadata
        self.encode_format: AudioEncodeFormat = encode_format
        self.is_del_src_audio: bool = config['transcode']["is_del_src_audio"]
        self.is_en_flt_compress: bool = config['transcode']["is_en_flt_compress"]
        self.is_en_dsd_compress: bool = config['transcode']["is_en_dsd_compress"]
        self.is_en_flac0_compress: bool = config['transcode']["is_en_flac0_compress"]

    @abstractmethod
    def compress_audio(self):
        pass

    # ------------------------------------------------------------------ #
    #  统一异常处理上下文：失败时自动清理输出文件并记录日志                        #
    # ------------------------------------------------------------------ #
    @contextmanager
    def _processing_guard(self, *output_paths: Path) -> Generator[None, None, None]:
        try:
            yield
        except AudioProcessingError as e:
            for p in output_paths:
                p.unlink(missing_ok=True)
                logger.error(f"已删除不完整的输出文件：{p}")
            logger.error(str(e))
        except KeyboardInterrupt as e:
            for p in output_paths:
                p.unlink(missing_ok=True)
                logger.debug(f"用户手动停止，已删除不完整的输出文件：{p}")
        except mutagen.apev2.APEBadItemError as e:
            for p in output_paths:
                p.unlink(missing_ok=True)
                logger.error(f"{self.file_p}存在无法解析的字段，请手动转码，已删除不完整的输出文件{p}")

    # ------------------------------------------------------------------ #
    #  编码方法：失败时 raise AudioProcessingError                         #
    # ------------------------------------------------------------------ #
    def _reencode_pcmbytes2flac(self, pcm_bytes: bytes, endian: str, channels: str,
                                 sample_rate: str, bps: str):
        cmd = CMD_PCMBYTES2FLAC.format(endian=endian, channels=channels, sample_rate=sample_rate,
                                       bps=bps, out_p=self.out_p)
        self._run_flac_encode(cmd, pcm_bytes)

    def _reencode_wavbytes2flac(self, wav_bytes: bytes):
        cmd = CMD_WAVBYTES2FLAC.format(out_p=self.out_p)
        self._run_flac_encode(cmd, wav_bytes)

    def _reencode_bytes2wv(self):
        logger.debug(f"正在将{self.file_p}转换为 Wavpack extrahigh extra-encode 6")
        audio_bytes = Path(self.file_p).read_bytes()
        cmd = CMD_BYTES2WV.format(out_p=self.out_p)
        try:
            subprocess.run(cmd, check=True, capture_output=True, input=audio_bytes)
        except subprocess.CalledProcessError as e:
            logger.error(e.stdout)
            raise AudioProcessingError(f"未能成功将{self.file_p}压缩为 Wavpack extrahigh extra-encode 6")
        logger.debug(f"成功将{self.file_p}压缩为 Wavpack extrahigh extra-encode 6")

    def _transfer_metadata(self):
        logger.debug(f"正在将{self.file_p}的元数据复制到{self.out_p}")
        TagsTransfer.transfer_meta(self.file_p, self.out_p)
        logger.debug(f"成功将{self.file_p}的元数据复制到{self.out_p}")

    def _finalize_output(self, keep_original_name: bool = False):
        self._transfer_metadata()

        if self.is_del_src_audio:
            self.file_p.unlink()
            if keep_original_name:
                self.out_p.rename(self.file_p)
                logger.debug(f"成功删除{self.file_p}并将输出文件更改为原名")
            else:
                logger.debug(f"成功删除{self.file_p}")
        logger.info(f"成功将{self.file_p}转换为flac")

    def _run_flac_encode(self, cmd, input_bytes: bytes):
        logger.debug(f"正在将{self.file_p}转换为 FLAC8")
        try:
            subprocess.run(cmd, check=True, capture_output=True, input=input_bytes)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors='replace') if e.stderr else e.stdout.decode(errors='replace')
            logger.error(stderr)
            raise AudioProcessingError(f"未能成功将{self.file_p}压缩为 flac8")
        logger.debug(f"成功将{self.file_p}压缩为 flac8")

    def _decode_to_wavbytes(self, cmd: str) -> bytes:
        try:
            result = subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise AudioProcessingError(f"解码失败：{e.stderr.decode(errors='replace')}")
        return result.stdout

    def _flac_similar_compress(self, cmd: str):
        wav_bytes = self._decode_to_wavbytes(cmd)
        self._reencode_wavbytes2flac(wav_bytes)
        del wav_bytes
        self._finalize_output()


# ------------------------------------------------------------------ #
#  各格式 Handler                                                      #
# ------------------------------------------------------------------ #

class FlacHandler(AudioHandler):
    def compress_audio(self):
        if self.encode_format is not AudioEncodeFormat.FLAC:
            logger.debug(f"{self.file_p}无需压缩")
            return
        self.out_p = self.path_manager.get_output_path(self.file_p)
        with self._processing_guard(self.out_p):
            audio_bytes = self.file_p.read_bytes()
            self._reencode_wavbytes2flac(audio_bytes)
            del audio_bytes
            if self.is_del_src_audio:
                self._finalize_output(keep_original_name=True)
            else:
                self._finalize_output()


class ApeHandler(AudioHandler):
    def compress_audio(self):
        self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
        with self._processing_guard(self.out_p):
            self._flac_similar_compress(CMD_APE2WAVBYTES.format(file_p=self.file_p))


class TakHandler(AudioHandler):
    def compress_audio(self):
        self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
        with self._processing_guard(self.out_p):
            self._flac_similar_compress(CMD_TAK2WAVBYTES.format(file_p=self.file_p))


class TtaHandler(AudioHandler):
    def compress_audio(self):
        self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
        with self._processing_guard(self.out_p):
            self._flac_similar_compress(CMD_TTA2WAVBYTES.format(file_p=self.file_p))


class M4aHandler(AudioHandler):
    def compress_audio(self):
        if self.encode_format is not AudioEncodeFormat.FLAC:
            logger.debug(f"{self.file_p}是有损音频，不会转换")
            return
        self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))

        with self._processing_guard(self.out_p):
            file_p = self.path_manager.to_norm_path(self.file_p)
            self._flac_similar_compress(CMD_M4A2WAVBYTES.format(file_p=self.file_p))


class WavepackHandler(AudioHandler):
    def compress_audio(self):
        if self.encode_format is AudioEncodeFormat.FLAC:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
            with self._processing_guard(self.out_p):
                wav_bytes = self._decode_to_wavbytes(CMD_WAVPACK2WAVBYTES.format(file_p=self.file_p))
                self._reencode_wavbytes2flac(wav_bytes)
                del wav_bytes
                self._finalize_output()
        elif self.encode_format is AudioEncodeFormat.WAVEPACK:
            logger.debug(f"{self.file_p}无需压缩")
        else:
            logger.error(f"不支持压缩{self.file_p}")


class WavHandler(AudioHandler):
    def compress_audio(self):
        if self.encode_format is AudioEncodeFormat.FLAC:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
            with self._processing_guard(self.out_p):
                audio_bytes = self.file_p.read_bytes()
                self._reencode_wavbytes2flac(audio_bytes)
                del audio_bytes
                self._finalize_output()
        elif self.encode_format is AudioEncodeFormat.WAVEPACK and self.is_en_flt_compress:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".wv"))
            with self._processing_guard(self.out_p):
                self._reencode_bytes2wv()
                self._finalize_output()
        else:
            logger.error(f"不支持压缩{self.file_p}")
            return


class AiffHandler(AudioHandler):
    def compress_audio(self):
        if self.encode_format is AudioEncodeFormat.FLAC:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
            with self._processing_guard(self.out_p):
                sample_rate = self.metadata['SampleRate']
                bps = self.metadata['SampleSize']
                channels = self.metadata['NumChannels']
                pcm_bytes = self.extract_pcm_bytes(self.file_p)
                if pcm_bytes == b'':
                    logger.error(f"{self.file_p}是空文件")
                    return
                self._reencode_pcmbytes2flac(pcm_bytes, 'big', channels, sample_rate, bps)
                self._finalize_output()
        elif self.encode_format is AudioEncodeFormat.WAVEPACK and self.is_en_flt_compress:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".wv"))
            with self._processing_guard(self.out_p):
                self._reencode_bytes2wv()
                self._finalize_output()
        else:
            logger.error(f"不支持压缩{self.file_p}")
            return

    @staticmethod
    def iter_chunks(f, end_pos):
        while f.tell() < end_pos:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            chunk_id = hdr[:4]
            chunk_size = struct.unpack(">I", hdr[4:])[0]
            data_pos = f.tell()
            yield chunk_id, chunk_size, data_pos
            f.seek(data_pos + chunk_size + (chunk_size % 2))

    @staticmethod
    def extract_pcm_bytes(path: Path) -> bytes:
        with path.open("rb") as f:
            form = f.read(4)
            if form != b"FORM":
                raise ValueError("不是 AIFF/AIFC 文件")
            form_size = struct.unpack(">I", f.read(4))[0]
            form_type = f.read(4)
            if form_type not in (b"AIFF", b"AIFC"):
                raise ValueError(f"不支持的 FORM type: {form_type!r}")

            form_end = 8 + form_size
            for chunk_id, chunk_size, data_pos in AiffHandler.iter_chunks(f, form_end):
                if chunk_id == b"SSND":
                    f.seek(data_pos)
                    offset = struct.unpack(">I", f.read(4))[0]
                    audio_data_pos = f.tell() + offset
                    payload_size = chunk_size - 8 - offset
                    if payload_size < 0:
                        raise ValueError("SSND chunk 大小非法")
                    f.seek(audio_data_pos)
                    return f.read(payload_size)
        return b''


class DSDHandler(AudioHandler):
    def compress_audio(self):
        if self.encode_format is AudioEncodeFormat.WAVEPACK and self.is_en_dsd_compress:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".wv"))
            with self._processing_guard(self.out_p):
                self._reencode_bytes2wv()
                self._finalize_output()
        else:
            logger.error(f"不支持压缩{self.file_p}，可能原因是dff是压缩过的，可以尝试用foobar手动转换")
