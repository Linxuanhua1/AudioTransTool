import subprocess, json, os, io, re, logging, mutagen
from mutagen.flac import Picture
from mutagen.id3._specs import PictureType
from PIL import Image
from typing import Callable
from lib.metadata_mapping import ID3v24_TO_VORBIS, APEV2_TO_VORBIS, MP4_TO_VORBIS, ID3v23_TO_VORBIS
from lib.utils import *

os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.path.dirname(os.getcwd()) + '/bin/'

ALLOWED_SAMPLE_FMT = ['s32', 's32p', 's16', 's16p']

logger = logging.getLogger(__name__)

def setup_audio_module_logger(work_logger):
    global logger
    logger = work_logger


class AudioProbe:
    @staticmethod
    def probe(file_path: str) -> dict:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_entries',
            'stream=sample_fmt,codec_name,bits_per_raw_sample,bits_per_sample,channels,sample_rate,duration,bit_rate',
            file_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            return json.loads(result.stdout)['streams'][0]
        except subprocess.CalledProcessError:
            raise Exception('可能是单个文件夹路径超过了260字符，请检查一下')

    @staticmethod
    def is_allowed_to_convert(file_path: str) -> bool:
        data = AudioProbe.probe(file_path)
        codec_name = data['codec_name']
        sample_fmt = data['sample_fmt']

        if codec_name == 'aac':
            logger.info(f'{file_path} 是有损音频不会转换')
            return False
        if codec_name == 'flac':
            sample_rate = int(data['sample_rate'])
            channels = int(data['channels'])
            bits_per_sample = int(data['bits_per_raw_sample'])
            duration = float(data['duration'])

            pcm_size = sample_rate * channels * bits_per_sample * duration / 8
            flac_size = os.path.getsize(file_path)
            return flac_size / pcm_size > 0.9

        if sample_fmt in ALLOWED_SAMPLE_FMT:
            return True

        logger.info(f'不支持的编码格式，编码格式为 {sample_fmt}')
        return False


class AudioEncoder:
    @staticmethod
    def encode_file2flac(file_path, target_path):
        """
        wav和flac可以直接转换为flac，使用这个函数
        """
        try:
            cmd = ['flac', file_path, '--best', '--threads=16', '-o', target_path]
            subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
        except subprocess.CalledProcessError as e:
            logger.error(e.stdout)
            raise Exception('可能是单个文件夹路径超过了260字符，请检查一下')

    @staticmethod
    def encode_pcm2flac(raw:bytes, output, sample_rate, channels, bps):
        """
        分轨使用的函数，裸pcm流转换为flac
        """
        cmd = ['flac', "--force-raw-format", "--sign=signed", "--endian=little", f'--channels={channels}',
               f'--sample-rate={sample_rate}', f'--bps={bps}', '-', '--best', '--threads=16', '-o', output]
        proc_encode = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        proc_encode.stdin.write(raw)
        proc_encode.stdin.close()
        proc_encode.wait()

    @staticmethod
    def encode_wav_bytes2flac(wav_data:bytes, target_path):
        """
        别的解码器转换出来的wav转换为flac
        """
        cmd = ['flac', '-', '--best', '--threads=16', '-o', target_path]
        proc_encode = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        proc_encode.stdin.write(wav_data)
        proc_encode.stdin.close()
        proc_encode.wait()


class AudioConversionExecutor:
    @staticmethod
    def file_direct2flac(file_path: str, is_del_source_audio: bool, meta_transfer: Callable[[mutagen, mutagen], None] or None):
        """直接把 WAV或者 FLAC0 转成 FLAC8，并搬运元数据"""
        root, name = get_root_dir_and_name(file_path)
        target_path = handle_repeat_file_name(root, name, 'flac')

        logger.info(f'正在将转换为 FLAC8')
        AudioEncoder.encode_file2flac(file_path, target_path)

        source_audio = mutagen.File(file_path)
        target_audio = mutagen.File(target_path)
        if meta_transfer:  # flac转flac不需要手动迁移元数据
            meta_transfer(source_audio, target_audio)
        logger.info(f'成功将元数据从源文件转移到转码后的文件')
        if is_del_source_audio:
            os.remove(file_path)
            if not meta_transfer:  # flac文件肯定会重名，所以删除后改回原名
                os.rename(target_path, file_path)
            logger.info(f'成功删除源文件')

    @staticmethod
    def via_wav2flac(file_path: str, is_del_source_audio: bool, cmd: list, meta_transfer: Callable[[mutagen, mutagen], None]):
        """先用外部命令把任意格式转成 WAV，再转 FLAC 并复制元数据"""
        root, name = get_root_dir_and_name(file_path)
        target_path = handle_repeat_file_name(root, name, 'flac')

        logger.info(f'正在将文件转换为WAV，缓存到内存中')
        proc_decode = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        wav_data, _ = proc_decode.communicate()
        logger.info(f'已成功缓存')
        AudioEncoder.encode_wav_bytes2flac(wav_data, target_path)
        logger.info(f'正在将内存中的WAV转换为FLAC')

        source_audio = mutagen.File(file_path)
        target_audio = mutagen.File(target_path)
        meta_transfer(source_audio, target_audio)
        logger.info(f'成功将元数据从源文件转移到转码后的FLAC文件上')

        if is_del_source_audio:
            os.remove(file_path)
            logger.info(f'成功删除源文件')
        logger.info('-' * 100)


class AudioHandler:
    @staticmethod
    def flac2flac(file_path: str, is_delete_origin_audio: bool):
        AudioConversionExecutor.file_direct2flac(file_path, is_delete_origin_audio, None)

    @staticmethod
    def wav2flac(file_path: str, is_delete_origin_audio: bool):
        AudioConversionExecutor.file_direct2flac(file_path, is_delete_origin_audio, MetaConverter.convert_id3)

    @staticmethod
    def m4a2flac(file_path: str, is_del_source_audio: bool):
        audio = mutagen.File(file_path)
        if audio.tags:
            audio.tags.pop('hdlr', None)  # 如果存在则删除，不存在则忽略
        audio.save()
        d_cmd = ['refalac', '-D', file_path, '-o', '-']
        AudioConversionExecutor.via_wav2flac(file_path, is_del_source_audio, d_cmd, MetaConverter.convert_mp4)

    @staticmethod
    def ape2flac(file_path: str, is_del_source_audio: bool):
        d_cmd = ['mac', file_path, '-', '-d']
        AudioConversionExecutor.via_wav2flac(file_path, is_del_source_audio, d_cmd, MetaConverter.convert_apev2)

    @staticmethod
    def tak2flac(file_path: str, is_del_source_audio: bool):
        d_cmd = ['Takc', '-d', file_path, '-']
        AudioConversionExecutor.via_wav2flac(file_path, is_del_source_audio, d_cmd, MetaConverter.convert_apev2)

    @staticmethod
    def tta2flac(file_path: str, is_del_source_audio: bool):
        d_cmd = ['ttaenc', '-d', file_path, '-']
        AudioConversionExecutor.via_wav2flac(file_path, is_del_source_audio, d_cmd, MetaConverter.convert_id3)


class MetaConverter:
    """负责统一调用的对外接口"""
    @staticmethod
    def convert_id3(source_audio, target_audio):
        return ID3Converter.to_vorbis(source_audio, target_audio)

    @staticmethod
    def convert_apev2(source_audio, target_audio):
        return APEv2Converter.to_vorbis(source_audio, target_audio)

    @staticmethod
    def convert_mp4(source_audio, target_audio):
        return MP4Converter.to_vorbis(source_audio, target_audio)


class ID3Converter:
    @staticmethod
    def _id3_pic_to_vorbis(tag, target_audio) -> None:
        pic = Picture()
        pic.data = tag.data
        pic.mime = tag.mime
        pic.desc = tag.desc
        pic.type = tag.type
        target_audio.add_picture(pic)

    @staticmethod
    def _id3_mapping_to_vorbis(field, version) -> str or list[str, str]:
        if field.startswith("TXXX:"):
            if 'musicbrainz' in field.lower():
                vorbis_field = ('MUSICBRAINZ_' + field.replace('TXXX:MusicBrainz', '').replace(' ', '')).upper()
            elif 'acoustid' in field.lower():
                vorbis_field = field.replace('TXXX:', '').replace(' ', '_').upper()
            else:
                vorbis_field = field.replace('TXXX:', '').replace(' ', '')
        elif field.startswith("COMM:"):
            vorbis_field = 'COMMENT'
        elif field == 'MVIN':
            vorbis_field = ['MOVEMENT', 'MOVEMENTTOTAL']
        elif field.startswith('APIC:'):
            vorbis_field = field
        else:
            try:
                if version == 4:
                    vorbis_field = ID3v24_TO_VORBIS[field]
                elif version == 3:
                    vorbis_field = ID3v23_TO_VORBIS[field]
                else:
                    raise Exception(f"未成功检测到id3的版本")
            except KeyError:
                raise KeyError(f'未知的元数据字段{field}')
        return vorbis_field

    @classmethod
    def to_vorbis(cls, source_audio, target_audio) -> None:
        try:
            version = source_audio.tags.version[1]
        except AttributeError:
            logger.info(f'源音频没有元数据，无需传递')
            return
        for field, tag in source_audio.tags.items():
            vorbis_field = cls._id3_mapping_to_vorbis(field, version)
            if isinstance(vorbis_field, list):
                metadatas = tag.text[0].split("/")
                for field, metadata in zip(vorbis_field, metadatas):
                    target_audio[field] = metadata
            else:
                if vorbis_field.startswith('APIC:'):
                    cls._id3_pic_to_vorbis(tag, target_audio)
                elif 'RATING' in vorbis_field:
                    target_audio[vorbis_field] = [str(tag.rating)]
                else:
                    target_audio[vorbis_field] = [str(i) for i in tag.text]
        target_audio.save()


class APEv2Converter:
    @staticmethod
    def _apev2_pic_to_vorbis(tag, field, target_audio) -> None:
        pic = Picture()
        try:
            img = Image.open(io.BytesIO(tag.value))
            pic.data = tag.value
        except IOError:
            img = Image.open(io.BytesIO(tag.value.split(b'\0', 1)[1]))
            pic.data = tag.value.split(b'\0', 1)[1]
        pic.mime = "image/{0}".format(img.format.lower())
        pic.type = APEV2_TO_VORBIS[field]
        target_audio.add_picture(pic)

    @classmethod
    def to_vorbis(cls, source_audio, target_audio) -> None:
        if source_audio.tags:
            for field, tag in source_audio.tags.items():
                if field.startswith('Cover Art'):
                    cls._apev2_pic_to_vorbis(tag, field, target_audio)
                    continue
                elif field in APEV2_TO_VORBIS:
                    vorbis_field = APEV2_TO_VORBIS[field]
                else:
                    vorbis_field = field
                target_audio[vorbis_field] = [i.decode() for i in tag.value.encode().split(b'\0')]
            target_audio.save()


class MP4Converter:
    @staticmethod
    def _mp4_mapping_to_vorbis(field) -> str or list[str, str]:
        if field.startswith('----'):
            if 'musicbrainz' in field.lower():
                vorbis_field = ('MUSICBRAINZ_' + field.replace('----:com.apple.iTunes:MusicBrainz', '').replace(' ', '')).upper()
            elif 'acoustid' in field.lower():
                vorbis_field = field.replace('----:com.apple.iTunes:', '').replace(' ', "_").upper()
            else:
                vorbis_field = field.replace('----:com.apple.iTunes:', '').replace(' ', "").upper()
        elif field == 'covr':  # covr字段不做修改，直接返回
            vorbis_field = field
        elif field.startswith('xid'):
             vorbis_field = 'xid'
        else:
            vorbis_field = MP4_TO_VORBIS[field]
        return vorbis_field

    @staticmethod
    def _mp4_pic_to_vorbis(tag, target_audio) -> None:
        for p in tag:
            pic = Picture()
            img = Image.open(io.BytesIO(p))
            pic.data = p
            pic.mime = "image/{0}".format(img.format.lower())
            pic.type = PictureType.COVER_FRONT
            target_audio.add_picture(pic)

    @classmethod
    def to_vorbis(cls, source_audio, target_audio):
        if source_audio.tags:
            for field, tag in source_audio.tags.items():
                vorbis_field = cls._mp4_mapping_to_vorbis(field)

                if isinstance(vorbis_field, list):  # 处理'trkn': [(1, 13)] 'disk': [(1, 1)]
                    for field, metadata in zip(vorbis_field, tag[0]):
                        target_audio[field] = str(metadata)
                elif vorbis_field == 'xid':
                    for t in tag:
                        t = t.split(":")
                        target_audio["CONTENTPROVIDER"] = t[0]
                        target_audio[t[1]] = t[2]
                elif vorbis_field == 'ENCODEDBY':  # 编码器不需要写入flac的元数据
                    continue
                else:
                    if vorbis_field == 'covr':
                        cls._mp4_pic_to_vorbis(tag, target_audio)
                    elif vorbis_field == "COMPILATION":
                        target_audio[vorbis_field] = str(int(tag))
                    else:
                        tag = [str(i.decode()) if isinstance(i, bytes) else str(i) for i in tag]
                        target_audio[vorbis_field] = tag
            target_audio.save()


class Splitter:
    @staticmethod
    def extract_pcm_segment_frame(pcm_data, sample_rate, bit_depth, channels, start_frame, end_frame):
        bytes_per_sample = (bit_depth // 8) * channels
        samples_per_frame = sample_rate // 75
        bytes_per_frame = bytes_per_sample * samples_per_frame
        start_byte = start_frame * bytes_per_frame
        if end_frame is not None:
            end_byte = end_frame * bytes_per_frame
            return pcm_data[start_byte:end_byte]
        else:
            return pcm_data[start_byte:]

    @staticmethod
    def split_flac_with_cue(file_path, is_delete_single_track, lock):
        source_root, source_name = get_root_dir_and_name(file_path)
        logger.info(f"正在分轨{file_path}")
        tracks = CueParser.paser_cue_data(f'{os.path.join(source_root, source_name)}.cue')
        data = AudioProbe.probe(file_path)
        sample_rate, channels, bits_per_sample = int(data['sample_rate']), int(data['channels']), int(data['bits_per_raw_sample'])
        logger.info(f"正在将音频转换为pcm数据缓存到内存中")
        process_decode = subprocess.Popen(['flac.exe', '-d', '--stdout', file_path], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        pcm_data, _ = process_decode.communicate()
        pcm_data = pcm_data[44:]  # 跳过wav头文件
        logger.info(f"成功转换音频为pcm数据")
        for i, track in enumerate(tracks):
            try:
                logger.info(f'正在分割第{i+1}首曲目，曲目名为{track["TITLE"]}')
            except KeyError:
                logger.info(f'正在分割第{i + 1}首曲目，该音频无曲目名')
            start_frame = track['INDEX01']
            end_frame = tracks[i + 1]['INDEX01'] if i < len(tracks) - 1 else None
            raw = Splitter.extract_pcm_segment_frame(pcm_data, sample_rate, bits_per_sample, channels, start_frame,
                                                     end_frame)
            logger.info('正在将曲目转换成flac')
            with lock:
                filename = f"{track['TRACKNUMBER']} - {track['TITLE']}"
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                split_audio_path_flac = handle_repeat_file_name(source_root, filename, 'flac')
                AudioEncoder.encode_pcm2flac(raw, split_audio_path_flac, sample_rate, channels, bits_per_sample)
            logger.info('成功转换为flac')
            split_audio_flac = mutagen.File(split_audio_path_flac)
            for field, tag in track.items():
                if field != 'INDEX01':
                    split_audio_flac[field] = str(tag)
            split_audio_flac.save()
            logger.info('成功将cuesheet的元数据写入分轨音频')

        if is_delete_single_track:
            os.remove(f'{os.path.join(source_root, source_name)}.cue')
            os.remove(file_path)
            logger.info('成功删除源文件和源文件的cue')
        logger.info(f'分轨完成')
        logger.info('-'*100)


class CueParser:
    # 全角到半角的映射表（预计算以提高性能）
    _FULL_TO_HALF_MAP = {chr(i): chr(i - 65248) for i in range(65281, 65375)}
    _FULL_TO_HALF_MAP[chr(12288)] = ' '  # 全角空格

    @classmethod
    def paser_cue_data(cls, file_path):
        enc = cls._detect_encoding(file_path)

        with open(file_path, encoding=enc) as f:
            lines = [
                cls._normalize_string(line.strip())
                for line in f.readlines()
                if line.strip()
            ]
            # 全角字符替换为半角字符，同时去除空行

        tracks_info = cls._parse_lines(lines)

        return tracks_info

    @classmethod
    def _normalize_string(cls, text: str) -> str:
        """全角转半角"""
        return ''.join(cls._FULL_TO_HALF_MAP.get(char, char) for char in text)

    @staticmethod
    def _detect_encoding(file_path):
        """
        检测编码，仅检测 utf-8 / utf-8-sig / utf-16 (LE/BE)
        如果是别的编码格式会报错
        """
        with open(file_path, "rb") as f:
            raw = f.read()

            # UTF-8 BOM
            if raw.startswith(b'\xef\xbb\xbf'):
                return 'utf-8-sig'

            # UTF-16 BOM
            elif raw.startswith(b'\xff\xfe'):
                return 'utf-16-le'
            elif raw.startswith(b'\xfe\xff'):
                return 'utf-16-be'

            # 默认 UTF-8
            else:
                return 'utf-8'

    @classmethod
    def _parse_lines(cls, lines: list[str]) -> list[dict[str, str]]:
        is_album_info = True
        album_info: dict[str, str] = {}
        tracks_info = []
        current_track: dict[str, any] = None

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

