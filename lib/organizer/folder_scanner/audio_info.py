from decimal import Decimal
from pathlib import Path
import subprocess, json

from lib.constants import DSD_RATE_MAP, COMMENT_SOURCE_MAP
from .scan_models import FolderStatus
from lib.common.probe import MediaProbe


class AudioQuality:
    def __init__(self, quality_str: str):
        self.quality_str = quality_str
        self.category = self._categorize(quality_str)
        self.sort_key = self._get_sort_key()

    def _categorize(self, quality: str) -> str:
        """分类音频质量：DSD / PCM无损 / PCM有损"""
        if "bit" in quality and "kHz" in quality:
            return "PCM_LOSSLESS"
        if quality.endswith("k"):
            return "PCM_LOSSY"
        if "DSD" in quality:
            return "DSD"
        return "UNKNOWN"

    def _get_sort_key(self) -> tuple[int, ...]:
        """生成排序键：优先级 + 数值大小（降序）"""
        category_priority = {
            "DSD": 0,
            "PCM_LOSSLESS": 1,
            "PCM_LOSSY": 2,
            "UNKNOWN": 3,
        }

        priority = category_priority.get(self.category, 3)

        match self.category:
            case "DSD":
                dsd_value = self._parse_dsd_value()
                return (priority, -dsd_value)

            case "PCM_LOSSLESS":
                bit_depth, sample_rate = self._parse_pcm_lossless()
                return (priority, -bit_depth, -sample_rate)

            case "PCM_LOSSY":
                bitrate = self._parse_bitrate()
                return (priority, -bitrate)

            case _:
                return (priority, 0)

    def _parse_dsd_value(self) -> int:
        """解析 DSD 数值，如 'DSD128' -> 128"""
        try:
            return int(self.quality_str.removeprefix("DSD"))
        except ValueError:
            return 0

    def _parse_pcm_lossless(self) -> tuple[int, float]:
        """解析 PCM 无损格式，如 '24bit96kHz' -> (24, 96.0)"""
        try:
            bit_part, rate_part = self.quality_str.split("bit", maxsplit=1)
            bit_depth = int(bit_part)
            sample_rate = float(rate_part.removesuffix("-flt").removesuffix("kHz"))
            return bit_depth, sample_rate
        except (ValueError, AttributeError):
            return 0, 0.0

    def _parse_bitrate(self) -> int:
        """解析比特率，如 '320k' -> 320"""
        try:
            return int(self.quality_str.removesuffix("k"))
        except ValueError:
            return 0

    def __eq__(self, other):
        return self.quality_str == other.quality_str

    def __hash__(self):
        return hash(self.quality_str)

    def __lt__(self, other):
        return self.sort_key < other.sort_key

    @staticmethod
    def get_all_audio_qualities(
            audio_files: list[Path],
    ) -> tuple[str, set[str]]:
        """
        获取所有音频质量，返回 (quality_string, found_formats)。
        quality_string = "DSD128+24bit96kHz+320k" (按质量排序)
        """
        found_formats: set[str] = set()
        qualities: set[AudioQuality] = set()

        if not audio_files:
            return "N/A", found_formats

        # 批量 probe
        results = MediaProbe.probe(audio_files)

        # 构建路径到元数据的映射
        metadata_map: dict[Path, dict] = {}
        if results:
            for r in results:
                metadata_map[Path(r['SourceFile'])] = r

        for file_p in audio_files:
            ext = file_p.suffix.lower()
            found_formats.add(ext)

            try:
                info = metadata_map.get(file_p)
                if info is None:
                    continue
                quality_str = AudioInfoParse.parse_probe(ext, info)
                if quality_str != "N/A":
                    qualities.add(AudioQuality(quality_str))
            except Exception:
                continue

        # 排序并用+连接
        sorted_qualities = sorted(qualities)
        quality_string = "+".join(q.quality_str for q in sorted_qualities)

        return quality_string or "N/A", found_formats


class AudioInfoParse:
    @staticmethod
    def parse_probe(ext: str, stream: dict) -> str:
        """解析音频质量信息"""
        match ext:
            case ".flac":
                return AudioInfoParse._join_pcm_quality(
                    stream["BitsPerSample"],
                    stream["SampleRate"],
                )

            case ".aiff" | ".aifc" | ".aif":
                return AudioInfoParse._join_pcm_quality(
                    stream["SampleSize"],
                    stream["SampleRate"],
                    is_float=bool(stream.get("CompressionType")),
                )

            case ".wav":
                return AudioInfoParse._join_pcm_quality(
                    stream["BitsPerSample"],
                    stream["SampleRate"],
                    is_float=int(stream["Encoding"]) == 3,
                )

            case ".dsf":
                return DSD_RATE_MAP.get(
                    AudioInfoParse._fmt_mhz_key(stream["SampleRate"]),
                    "N/A"
                )

            case ".wv":
                return AudioInfoParse._parse_wv_source(stream["source"])

            case ".m4a":
                if stream["AudioFormat"].lower() == "alac":
                    return AudioInfoParse._join_pcm_quality(
                        stream["AudioBitsPerSample"],
                        stream["AudioSampleRate"],
                    )
                return AudioInfoParse._fmt_bitrate_k(stream["BitsPerSample"])

            case ".wma":
                return AudioInfoParse._fmt_bitrate_k(stream["MaxBitrate"])

            case ".mp3":
                return AudioInfoParse._fmt_bitrate_k(stream["AudioBitrate"])

            case _:
                return "N/A"

    @staticmethod
    def _fmt_khz(value: int | str) -> str:
        return f"{Decimal(int(value)) / 1000}kHz"

    @staticmethod
    def _fmt_mhz_key(value: int | str) -> str:
        return str(Decimal(int(value)) / 1_000_000)

    @staticmethod
    def _fmt_bit(value: int | str) -> str:
        return f"{int(value)}bit"

    @staticmethod
    def _fmt_bitrate_k(value: int | str) -> str:
        return f"{round(Decimal(value) / 1000)}k"

    @staticmethod
    def _join_pcm_quality(depth: int | str, sample_rate: int | str, is_float: bool = False) -> str:
        result = AudioInfoParse._fmt_bit(depth) + AudioInfoParse._fmt_khz(sample_rate)
        if is_float:
            result += "-flt"
        return result

    @staticmethod
    def _parse_wv_source(source: str) -> str:
        """
        例如:
        '1-bit DSD at 2822400 Hz'
        '24-bit ints at 96000 Hz'
        '32-bit floats at 48000 Hz'
        """
        try:
            parts = source.strip().lower().split()
            depth = parts[0].split("-")[0]  # 1-bit -> 1
            data_format = parts[1]  # dsd / ints / floats
            sample_rate = parts[3]  # 2822400 / 96000 / 48000
        except (IndexError, AttributeError):
            return "N/A"

        match data_format:
            case "dsd":
                return DSD_RATE_MAP.get(AudioInfoParse._fmt_mhz_key(sample_rate), "N/A")
            case "ints":
                return AudioInfoParse._join_pcm_quality(depth, sample_rate)
            case "floats":
                return AudioInfoParse._join_pcm_quality(depth, sample_rate, is_float=True)
            case _:
                return "N/A"


class AudioSource:
    @staticmethod
    def detect_source(status: FolderStatus, folder_p: Path) -> tuple[str, str]:
        """
        检测音频来源，统一返回 (source, score)。
        有日志时 source=ripper, score=抓取评分；无日志时 score=""。
        """
        if status.has_log:
            log_p = next(folder_p.glob("*.log"))
            ripper, score = AudioSource._probe_log(log_p)
            return ripper, score
        else:
            for p in folder_p.rglob("*"):
                ext = p.suffix.lower()
                if ext in (".wma", ".mp3", ".ogg", ".m4a"):
                    return "WEB", ""
                if ext not in (".wav", ".flac", ".dsf"):
                    continue
                bundle = AudioTagReader.read(Path(p))
                if bundle is None:
                    return "WEB", ""

                # Vorbis / ID3 共用字段（AudioTagReader 已统一填充）
                if bundle.qbz_tid:
                    return "Qobuz", ""
                if "tidal" in bundle.url.lower():
                    return "Tidal", ""
                if "amazon" in bundle.merchant.lower():
                    return "Amazon", ""

                comment_lower = bundle.comment.lower()
                for key, value in COMMENT_SOURCE_MAP.items():
                    if key in comment_lower:
                        return value, ""

                if ext == ".dsf":
                    return "ISO转DSF", ""

                return "WEB", ""

            return "WEB", ""


    @staticmethod
    def _probe_log(log_p: Path) -> tuple[str, str]:
        cmd = ['cambia', '-p', log_p]
        result = subprocess.run(cmd, capture_output=True, check=True, text=True, encoding="utf-8")

        if not result.stdout:
            return "UnknownRipper", "0"
        info = json.loads(result.stdout)
        ripper_raw = info['parsed']['parsed_logs'][0]['ripper']
        match ripper_raw:
            case "Exact Audio Copy":
                ripper = "EAC"
            case "X Lossless Decoder":
                ripper = "XLD"
            case _:
                ripper = "UnknownRipper"
        score = info['evaluation_combined'][0]['evaluations'][0]['score']

        return ripper, score
