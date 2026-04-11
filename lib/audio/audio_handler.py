import subprocess, struct, logging
from pathlib import Path
from collections.abc import Generator
from contextlib import contextmanager
from enum import Enum, auto
from abc import ABC, abstractmethod

from lib.tags.transfer import TagsTransfer
from lib.common import probe, PathManager

logger = logging.getLogger(__name__)


class AudioEncodeFormat(Enum):
    FLAC = auto()
    WAVEPACK = auto()
    UNSUPPORTED = auto()


class AudioProcessingError(Exception):
    def __init__(self, message: str, output_path: Path | None = None):
        super().__init__(message)
        self.output_path = output_path


class AudioHandler(ABC):
    def __init__(self, file_p: Path, path_manager: PathManager, config):
        self.file_p: Path = file_p
        self.path_manager: PathManager = path_manager
        self.out_p: Path | None = None
        self.is_del_src_audio: bool = config['transcode']["is_del_src_audio"]
        self.is_en_flt_compress: bool = config['transcode']["is_en_flt_compress"]
        self.is_en_dsd_compress: bool = config['transcode']["is_en_dsd_compress"]
        self.is_en_flac0_compress: bool = config['transcode']["is_en_flac0_compress"]

    @abstractmethod
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        pass

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

    # ------------------------------------------------------------------ #
    #  编码方法：失败时 raise AudioProcessingError                         #
    # ------------------------------------------------------------------ #
    def _reencode_file2flac(self):
        audio_bytes = Path(self.file_p).read_bytes()
        cmd = ["flac", "-", "--best", "--threads=16", "-o", self.out_p]
        self._run_flac_encode(cmd, audio_bytes)

    def _reencode_pcmbytes2flac(self, pcm_bytes: bytes, endian: str, channels: str,
                                 sample_rate: str, bps: str):
        cmd = ['flac', "--force-raw-format", "--sign=signed", f"--endian={endian}",
               f'--channels={channels}', f'--sample-rate={sample_rate}', f'--bps={bps}',
               '-', '--best', '--threads=16', '-o', self.out_p]
        self._run_flac_encode(cmd, pcm_bytes)

    def _reencode_wavbytes2flac(self, wav_bytes: bytes):
        cmd = ['flac', '-', '--best', '--threads=16', '-o', self.out_p]
        self._run_flac_encode(cmd, wav_bytes)

    def _reencode_file2wv(self):
        logger.debug(f"正在将{self.file_p}转换为 Wavpack extrahigh extra-encode 6")
        cmd = ["wavpack", "--threads=12", "-hhx6", self.file_p, self.out_p]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        except subprocess.CalledProcessError as e:
            logger.error(e.stdout)
            raise AudioProcessingError(
                f"未能成功将{self.file_p}压缩为 Wavpack extrahigh extra-encode 6",
                self.out_p
            )
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
            raise AudioProcessingError(
                f"未能成功将{self.file_p}压缩为 flac8",
                self.out_p
            )
        logger.debug(f"成功将{self.file_p}压缩为 flac8")

    @staticmethod
    def _decode_to_wavbytes(cmd: list, audio_bytes: bytes = None) -> bytes:
        try:
            if audio_bytes is None:
                result = subprocess.run(cmd, check=True, capture_output=True)
            else:
                result = subprocess.run(cmd, check=True, capture_output=True, input=audio_bytes)
        except subprocess.CalledProcessError as e:
            raise AudioProcessingError(
                f"解码失败：{e.stderr.decode(errors='replace')}"
            )
        return result.stdout

    def _flac_similar_compress(self, cmd: list, audio_bytes: bytes = None):
        wav_bytes = self._decode_to_wavbytes(cmd, audio_bytes)
        self._reencode_wavbytes2flac(wav_bytes)
        self._finalize_output()

    @staticmethod
    def _pcm_encoding_to_format(stream: dict) -> AudioEncodeFormat:
        encoding = int(stream['Encoding'])
        bps = int(stream['BitsPerSample'])
        if encoding == 1 and bps in (16, 24, 32):
            return AudioEncodeFormat.FLAC
        elif encoding == 3 and bps in (32, 64):
            return AudioEncodeFormat.WAVEPACK
        else:
            return AudioEncodeFormat.UNSUPPORTED


# ------------------------------------------------------------------ #
#  各格式 Handler                                                      #
# ------------------------------------------------------------------ #

class FlacHandler(AudioHandler):
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        if self.is_en_flac0_compress:
            stream: dict = probe(self.file_p)
            if stream is None:
                return AudioEncodeFormat.UNSUPPORTED
            sample_rate = int(stream['SampleRate'])
            channels = int(stream['Channels'])
            bits_per_sample = int(stream['BitsPerSample'])
            duration = float(stream['Duration'])

            pcm_size = sample_rate * channels * bits_per_sample * duration / 8
            flac_size = self.file_p.stat().st_size

            if flac_size / pcm_size > 0.9:
                return AudioEncodeFormat.FLAC

        return AudioEncodeFormat.UNSUPPORTED

    def compress_audio(self):
        if self._is_enc2flac_or_wv() is not AudioEncodeFormat.FLAC:
            logger.debug(f"{self.file_p}无需压缩")
            return
        self.out_p = self.path_manager.get_output_path(self.file_p)
        with self._processing_guard(self.out_p):
            self._reencode_file2flac()
            if self.is_del_src_audio:
                self._finalize_output(keep_original_name=True)
            else:
                self._finalize_output()


class ApeHandler(AudioHandler):
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        pass

    def compress_audio(self):
        self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
        with self._processing_guard(self.out_p):
            self._flac_similar_compress(['MAC', self.file_p, '-', '-d'])


class TakHandler(AudioHandler):
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        pass

    def compress_audio(self):
        self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
        with self._processing_guard(self.out_p):
            self._flac_similar_compress(['Takc', '-d', self.file_p, '-'])


class TtaHandler(AudioHandler):
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        pass

    def compress_audio(self):
        self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
        with self._processing_guard(self.out_p):
            self._flac_similar_compress(['ttaenc', '-d', self.file_p, '-'])


class M4aHandler(AudioHandler):
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        stream: dict = probe(self.file_p)
        audio_format = stream['AudioFormat'].lower()
        if audio_format == 'alac':
            return AudioEncodeFormat.FLAC
        return AudioEncodeFormat.UNSUPPORTED

    def compress_audio(self):
        if self._is_enc2flac_or_wv() is not AudioEncodeFormat.FLAC:
            logger.debug(f"{self.file_p}是有损音频，不会转换")
            return
        self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))

        # TODO: 跟进一下这个issue，refalac新版本不支持长路径，旧版本截止到1.83对应qaac2.83是支持长路径的
        # 不支持unc开头的路径即\\?\
        # https://github.com/nu774/qaac/issues/121
        with self._processing_guard(self.out_p):
            file_p = self.path_manager.to_norm_path(self.file_p)
            self._flac_similar_compress(['refalac', '-D', file_p, '-o', '-'])


class WavepackHandler(AudioHandler):
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        stream: dict = probe(self.file_p)
        data_format = stream['source'].split(' ')[1].lower()
        match data_format:
            case "dsd" | "floats":
                return AudioEncodeFormat.WAVEPACK
            case "ints":
                return AudioEncodeFormat.FLAC
            case _:
                return AudioEncodeFormat.UNSUPPORTED

    def compress_audio(self):
        compress_type = self._is_enc2flac_or_wv()
        if compress_type is AudioEncodeFormat.FLAC:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
            with self._processing_guard(self.out_p):
                wav_bytes = self._decode_to_wavbytes(['wvunpack', '--wav', "--threads=12", self.file_p, '-'])
                self._reencode_wavbytes2flac(wav_bytes)
                self._finalize_output()
        elif compress_type is AudioEncodeFormat.WAVEPACK:
            logger.debug(f"{self.file_p}无需压缩")
        else:
            logger.error(f"不支持压缩{self.file_p}")


class WavHandler(AudioHandler):
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        stream: dict = probe(self.file_p)
        return self._pcm_encoding_to_format(stream)

    def compress_audio(self):
        compress_type = self._is_enc2flac_or_wv()
        if compress_type is AudioEncodeFormat.FLAC:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
            with self._processing_guard(self.out_p):
                self._reencode_file2flac()
                self._finalize_output()
        elif compress_type is AudioEncodeFormat.WAVEPACK and self.is_en_flt_compress:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".wv"))
            with self._processing_guard(self.out_p):
                self._reencode_file2wv()
                self._finalize_output()
        else:
            logger.error(f"不支持压缩{self.file_p}")
            return


class AiffHandler(AudioHandler):
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        stream: dict = probe(self.file_p)
        file_type = stream['FileType']
        bits_per_sample = int(stream['SampleSize'])
        if file_type == "AIFF" and bits_per_sample in (16, 24, 32):
            return AudioEncodeFormat.FLAC
        elif file_type == "AIFC" and bits_per_sample in (32, 64):
            return AudioEncodeFormat.WAVEPACK
        return AudioEncodeFormat.UNSUPPORTED

    def compress_audio(self):
        compress_type = self._is_enc2flac_or_wv()
        if compress_type is AudioEncodeFormat.FLAC:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".flac"))
            with self._processing_guard(self.out_p):
                stream: dict = probe(self.file_p)
                sample_rate, bps, channels = stream['SampleRate'], stream['SampleSize'], stream['NumChannels']
                pcm_bytes = self.extract_pcm_bytes(self.file_p)
                if pcm_bytes == b'':
                    logger.error(f"{self.file_p}是空文件")
                    return
                self._reencode_pcmbytes2flac(pcm_bytes, 'big', channels, sample_rate, bps)
                self._finalize_output()
        elif compress_type is AudioEncodeFormat.WAVEPACK and self.is_en_flt_compress:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".wv"))
            with self._processing_guard(self.out_p):
                self._reencode_file2wv()
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
    def _is_enc2flac_or_wv(self) -> AudioEncodeFormat:
        stream: dict = probe(self.file_p)
        file_type = stream.get('FileType').lower() if stream else None
        if file_type == "dsf":
            return AudioEncodeFormat.WAVEPACK
        else:
            dst = self.is_dff_dst()
            if dst:
                return AudioEncodeFormat.UNSUPPORTED
            elif dst is None:
                logger.error(f"{self.file_p}不是合法的 DFF 文件")
                return AudioEncodeFormat.UNSUPPORTED
            return AudioEncodeFormat.WAVEPACK

    def compress_audio(self):
        if self._is_enc2flac_or_wv() is AudioEncodeFormat.WAVEPACK and self.is_en_dsd_compress:
            self.out_p = self.path_manager.get_output_path(self.file_p.with_suffix(".wv"))
            with self._processing_guard(self.out_p):
                self._reencode_file2wv()
                self._finalize_output()
        else:
            logger.error(f"不支持压缩{self.file_p}，可能原因是dff是压缩过的，可以尝试用foobar手动转换")

    def is_dff_dst(self) -> bool | None:
        with self.file_p.open("rb") as f:
            header = f.read(12)
            if len(header) < 12:
                return None
            form_id = header[0:4]
            # form_size = struct.unpack(">Q", header[4:12])[0]
            if form_id != b"FRM8":
                return None
            form_type = f.read(4)
            if form_type != b"DSD ":
                return None
            while True:
                chunk_header = f.read(12)
                if len(chunk_header) < 12:
                    break
                chunk_id = chunk_header[0:4]
                chunk_size = struct.unpack(">Q", chunk_header[4:12])[0]
                if chunk_id == b"DST ":
                    return True
                if chunk_id == b"DSD ":
                    return False
                f.seek(chunk_size, 1)
                if chunk_size % 2 == 1:
                    f.seek(1, 1)
        return None