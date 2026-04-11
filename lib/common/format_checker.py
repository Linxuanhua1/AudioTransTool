"""
格式检测器：集中管理所有格式的"是否需要转换"判断逻辑。
由 TaskManager 在批量 probe 之后调用，决定是否将文件加入转码队列。
"""
import struct
import logging
from pathlib import Path

from lib.audio.audio_handler import AudioEncodeFormat


logger = logging.getLogger(__name__)


class AudioFormatChecker:
    """根据 probe 元数据判断音频文件的目标编码格式"""

    @staticmethod
    def check(ext: str, metadata: dict | None, file_p: Path, config: dict) -> AudioEncodeFormat:
        if metadata is None:
            return AudioEncodeFormat.UNSUPPORTED

        checkers = {
            '.flac': AudioFormatChecker._check_flac,
            '.m4a': AudioFormatChecker._check_m4a,
            '.wv': AudioFormatChecker._check_wavepack,
            '.wav': AudioFormatChecker._check_wav,
            '.aiff': AudioFormatChecker._check_aiff,
            '.aif': AudioFormatChecker._check_aiff,
            '.aifc': AudioFormatChecker._check_aiff,
            '.dsf': AudioFormatChecker._check_dsd,
            '.dff': AudioFormatChecker._check_dsd,
            # 这些格式始终转换为 FLAC
            '.ape': AudioFormatChecker._always_flac,
            '.tak': AudioFormatChecker._always_flac,
            '.tta': AudioFormatChecker._always_flac,
        }

        checker = checkers.get(ext)
        if checker is None:
            return AudioEncodeFormat.UNSUPPORTED
        return checker(metadata, file_p, config)

    @staticmethod
    def _always_flac(metadata: dict, file_p: Path, config: dict) -> AudioEncodeFormat:
        return AudioEncodeFormat.FLAC

    @staticmethod
    def _check_flac(metadata: dict, file_p: Path, config: dict) -> AudioEncodeFormat:
        if not config['transcode'].get('is_en_flac0_compress', False):
            return AudioEncodeFormat.UNSUPPORTED

        try:
            sample_rate = int(metadata['SampleRate'])
            channels = int(metadata['Channels'])
            bits_per_sample = int(metadata['BitsPerSample'])
            duration = float(metadata['Duration'])
        except (KeyError, ValueError, TypeError):
            return AudioEncodeFormat.UNSUPPORTED

        pcm_size = sample_rate * channels * bits_per_sample * duration / 8
        flac_size = file_p.stat().st_size

        if flac_size / pcm_size > 0.9:
            return AudioEncodeFormat.FLAC
        return AudioEncodeFormat.UNSUPPORTED

    @staticmethod
    def _check_m4a(metadata: dict, file_p: Path, config: dict) -> AudioEncodeFormat:
        audio_format = metadata.get('AudioFormat', '').lower()
        if audio_format == 'alac':
            return AudioEncodeFormat.FLAC
        return AudioEncodeFormat.UNSUPPORTED

    @staticmethod
    def _check_wavepack(metadata: dict, file_p: Path, config: dict) -> AudioEncodeFormat:
        source = metadata.get('source', '')
        parts = source.split(' ')
        if len(parts) < 2:
            return AudioEncodeFormat.UNSUPPORTED

        data_format = parts[1].lower()
        match data_format:
            case "dsd" | "floats":
                return AudioEncodeFormat.WAVEPACK
            case "ints":
                return AudioEncodeFormat.FLAC
            case _:
                return AudioEncodeFormat.UNSUPPORTED

    @staticmethod
    def _check_wav(metadata: dict, file_p: Path, config: dict) -> AudioEncodeFormat:
        return AudioFormatChecker._pcm_encoding_to_format(metadata)

    @staticmethod
    def _check_aiff(metadata: dict, file_p: Path, config: dict) -> AudioEncodeFormat:
        file_type = metadata.get('FileType', '')
        try:
            bits_per_sample = int(metadata['SampleSize'])
        except (KeyError, ValueError, TypeError):
            return AudioEncodeFormat.UNSUPPORTED

        if file_type == "AIFF" and bits_per_sample in (16, 24, 32):
            return AudioEncodeFormat.FLAC
        elif file_type == "AIFC" and bits_per_sample in (32, 64):
            return AudioEncodeFormat.WAVEPACK
        return AudioEncodeFormat.UNSUPPORTED

    @staticmethod
    def _check_dsd(metadata: dict, file_p: Path, config: dict) -> AudioEncodeFormat:
        if not config['transcode'].get('is_en_dsd_compress', False):
            return AudioEncodeFormat.UNSUPPORTED

        file_type = (metadata.get('FileType') or '').lower()
        if file_type == "dsf":
            return AudioEncodeFormat.WAVEPACK

        # dff: 需要检查是否是 DST 压缩
        dst = AudioFormatChecker._is_dff_dst(file_p)
        if dst:
            logger.error(f"{file_p}是DST压缩的DFF，不支持直接转换")
            return AudioEncodeFormat.UNSUPPORTED
        elif dst is None:
            logger.error(f"{file_p}不是合法的 DFF 文件")
            return AudioEncodeFormat.UNSUPPORTED
        return AudioEncodeFormat.WAVEPACK

    @staticmethod
    def _pcm_encoding_to_format(metadata: dict) -> AudioEncodeFormat:
        try:
            encoding = int(metadata['Encoding'])
            bps = int(metadata['BitsPerSample'])
        except (KeyError, ValueError, TypeError):
            return AudioEncodeFormat.UNSUPPORTED

        if encoding == 1 and bps in (16, 24, 32):
            return AudioEncodeFormat.FLAC
        elif encoding == 3 and bps in (32, 64):
            return AudioEncodeFormat.WAVEPACK
        return AudioEncodeFormat.UNSUPPORTED

    @staticmethod
    def _is_dff_dst(file_p: Path) -> bool | None:
        """检查 DFF 文件是否使用了 DST 压缩"""
        try:
            with file_p.open("rb") as f:
                header = f.read(12)
                if len(header) < 12:
                    return None
                if header[0:4] != b"FRM8":
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
        except OSError:
            return None
        return None


class ImageFormatChecker:
    """根据 probe 元数据判断图片文件是否需要转换为 JXL"""

    @staticmethod
    def check(ext: str, metadata: dict | None, file_p: Path) -> bool:
        if metadata is None:
            return False

        checkers = {
            '.tif': ImageFormatChecker._check_tiff,
            '.tiff': ImageFormatChecker._check_tiff,
            '.jpg': ImageFormatChecker._check_jpg,
            '.jpeg': ImageFormatChecker._check_jpg,
            # 这些格式始终转换
            '.png': ImageFormatChecker._always_true,
            '.bmp': ImageFormatChecker._always_true,
            '.webp': ImageFormatChecker._always_true,
        }

        checker = checkers.get(ext)
        if checker is None:
            return False
        return checker(metadata, file_p)

    @staticmethod
    def _always_true(metadata: dict, file_p: Path) -> bool:
        return True

    @staticmethod
    def _check_tiff(metadata: dict, file_p: Path) -> bool:
        try:
            color_space = int(metadata['PhotometricInterpretation'])
            bit_depth = int(metadata['BitsPerSample'].split(" ")[0])
        except (KeyError, ValueError, TypeError):
            logger.error(f"{file_p} 无法读取 TIFF 元数据")
            return False

        if color_space in (0, 1, 2, 3, 4, 6) and bit_depth in (8, 16, 32):
            return True
        logger.error(f"{file_p} 不支持转换为 jxl")
        return False

    @staticmethod
    def _check_jpg(metadata: dict, file_p: Path) -> bool:
        try:
            color_components = len(metadata["BitsPerSample"].split(" "))
        except (KeyError, TypeError):
            logger.error(f"{file_p} 无法读取 JPG 元数据")
            return False

        if color_components in (1, 3):
            return True
        logger.error(f"{file_p} 不支持转换为 jxl（颜色分量数：{color_components}）")
        return False
