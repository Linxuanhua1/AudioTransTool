import subprocess, chardet, logging
from pathlib import Path
from mutagen.flac import FLAC
from typing import Any
from lib.common import PathManager, probe


logger = logging.getLogger(__name__)


class Splitter:
    def __init__(self, file_p: Path, p_man: PathManager, config: dict):
        self.out_p_man: PathManager = p_man
        self.file_p = file_p
        self.is_del_single_track: bool = config["transcode"]['is_del_single_trk']

    @staticmethod
    def extract_pcm_segment_frame(pcm_data, sample_rate, bit_depth, channels, start_frame, end_frame):
        # 计算公式：先算一个采样点的字节数，位深除以8乘通道数，再计算一帧有多少采样点，最后计算一帧有多少字节，根据开始帧计算跳转字节
        bytes_per_sample = (bit_depth // 8) * channels
        samples_per_frame = sample_rate // 75
        bytes_per_frame = bytes_per_sample * samples_per_frame
        start_byte = start_frame * bytes_per_frame
        if end_frame is not None:
            end_byte = end_frame * bytes_per_frame
            return pcm_data[start_byte:end_byte]
        else:
            return pcm_data[start_byte:]

    def split_flac_with_cue(self):
        logger.debug(f"正在分轨{self.file_p}")
        tracks = CueParser.paser_cue_data(self.file_p.with_suffix('.cue'))
        stream = probe(self.file_p)

        sample_rate, channels, bps = stream['SampleRate'], stream['Channels'], stream['BitsPerSample']
        logger.debug(f"正在将{self.file_p}转换为pcm数据缓存到内存中")

        flac_bytes = self.file_p.read_bytes()
        try:
            result = subprocess.run(['flac.exe', '-d', '--stdout', "-"], input=flac_bytes,
                                            capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(e.stderr.decode())
            logger.error(f"未能成功分轨{self.file_p}")
            return
        pcm_data: bytes = result.stdout[44:]  # 跳过wav头文件
        logger.debug(f"成功将{self.file_p}转换音频为pcm数据")

        for i, track in enumerate(tracks):
            logger.debug(f'正在分割第{i+1}首曲目，曲目名为{track.get("TITLE")}')
            start_frame = track['INDEX01']
            end_frame = tracks[i + 1]['INDEX01'] if i < len(tracks) - 1 else None
            raw = Splitter.extract_pcm_segment_frame(pcm_data, sample_rate, bps, channels, start_frame,
                                                     end_frame)

            filename = f"{track['TRACKNUMBER']} - {track.get('TITLE', track['TRACKNUMBER'])}.flac"
            filename = PathManager.safe_filename(filename)
            desired_out_p = Path(self.file_p.parent / filename)
            out_p = self.out_p_man.get_output_path(desired_out_p)

            cmd = ['flac', "--force-raw-format", "--sign=signed", f"--endian=little",
                   f'--channels={channels}', f'--sample-rate={sample_rate}', f'--bps={bps}',
                   '-', '--best', '--threads=16', '-o', out_p]
            subprocess.run(cmd, check=True, capture_output=True, input=raw)
            logger.debug(f'成功将{self.file_p}的第{i+1}轨转换为flac')

            split_audio_flac = FLAC(out_p)
            for field, tag in track.items():
                if field != 'INDEX01':
                    split_audio_flac[field] = str(tag)
            split_audio_flac.save()
            logger.debug(f'成功将cuesheet的元数据写入第{i+1}轨音频')

        if self.is_del_single_track:
            self.file_p.unlink()
            self.file_p.with_suffix('.cue').unlink()
            logger.debug(f'成功删除{self.file_p}和其cue文件')
        logger.info(f'{self.file_p}分轨成功')


class CueParser:
    # 全角到半角的映射表（预计算以提高性能）
    _FULL_TO_HALF_MAP = {chr(i): chr(i - 65248) for i in range(65281, 65375)}
    _FULL_TO_HALF_MAP[chr(12288)] = ' '  # 全角空格

    @classmethod
    def paser_cue_data(cls, file_p):
        raw = open(file_p, "rb").read()
        result = chardet.detect(raw)

        with open(file_p, encoding=result['encoding']) as f:
            lines = [
                ''.join(cls._FULL_TO_HALF_MAP.get(char, char) for char in line.strip())
                for line in f.readlines()
                if line.strip()
            ]
            # 全角字符替换为半角字符，同时去除空行

        tracks_info = cls._parse_lines(lines)

        return tracks_info

    @classmethod
    def _parse_lines(cls, lines: list[str]) -> list[dict[str, str]]:
        is_album_info = True
        album_info: dict[str, str] = {}
        tracks_info = []
        current_track: dict[str, Any] | None = None

        for line in lines:
            cmd, _, args = line.partition(' ')
            args = args.strip(' "')
            if cmd == 'REM':
                cls._parse_rem_line(args, is_album_info, album_info, current_track)
            elif cmd == 'FILE':
                continue
            elif cmd == 'TRACK':
                is_album_info = False
                num, _, __ = args.partition(' ')
                if current_track:  # cue文件的格式，每到一个track开头的行说明上一个数据已经添加完成，添加进列表
                    tracks_info.append(current_track)
                current_track = {'TRACKNUMBER': str(int(args.split(' ')[0]))}  # 只取编号
            elif cmd == 'INDEX':
                cls._parse_index_line(args, current_track)
            else:
                cls._parse_metadata_line(cmd, args, is_album_info, album_info, current_track)

        tracks_info.append(current_track)  # 添加最后一轨
        album_info["TOTALTRACKS"] = str(len(tracks_info))
        tracks_info = [i | album_info for i in tracks_info]  # 每一个track都添加album的信息
        return tracks_info

    @staticmethod
    def _parse_rem_line(args, album_info_flag, album_info, current_track):
        field, _, tag = args.partition(' ')
        tag = tag.strip(' "')
        if tag != '':
            if album_info_flag:
                album_info[field] = tag
            else:
                current_track[field] = tag

    @staticmethod
    def _parse_index_line(args, current_track):
        num, _, pos = args.partition(' ')
        if num == '01':
            minute, sec, frame = pos.split(':')
            frames = (int(minute) * 60 + int(sec)) * 75 + int(frame)
            current_track['INDEX01'] = frames

    @staticmethod
    def _parse_metadata_line(cmd, args, is_album_info, album_info, current_track):
        field, tag = cmd, args
        if is_album_info:
            if field == "PERFORMER":
                album_info['ALBUMARTIST'] = tag
            elif field == "TITLE":
                album_info['ALBUM'] = tag
            else:
                album_info[field] = tag
        else:
            if field == "PERFORMER":
                current_track['ARTIST'] = tag
            else:
                current_track[field] = tag

