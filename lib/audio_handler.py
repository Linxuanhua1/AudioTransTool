import subprocess, json, os, io,re, logging
import wave
import mutagen
from mutagen.flac import Picture
from mutagen.id3._specs import PictureType
from PIL import Image
from lib.metadata_mapping import ID3v24_TO_VORBIS, APEV2_TO_VORBIS, MP4_TO_VORBIS
from lib.common_method import *

logger = logging.getLogger(__name__)

os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.getcwd() + '/encoders/'

ALLOWED_SAMPLE_FMT = ['s32', 's32p', 's16', 's16p']

EXCLUDED_DIRS = ['bk', 'booklet', 'scan', 'scans', 'artwork', 'artworks', 'jacket']

class AudioHandler:
    @staticmethod
    def common_cmd2flac(cmd, file_path, root, name):
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f'成功将{file_path}转换为wav')
        logger.info(f'正在将{os.path.join(root, name)}.wav转换为flac')
        AudioHandler.convert_wav_to_flac(f'{os.path.join(root, name)}.wav', root, name)
        logger.info(f'成功将{os.path.join(root, name)}.wav转换为flac')
        os.remove(f'{os.path.join(root, name)}.wav')
        logger.info(f'删除缓存的{os.path.join(root, name)}.wav')

    @staticmethod
    def convert_wav_to_flac(file_path, root, name):  # 缓存文件转换为flac
        target_file_path = handle_repeat_file_name(root, name, 'flac')
        try:
            cmd = ['flac', file_path, '--best', '--threads=16', '-o', target_file_path]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(e.stdout)
            raise Exception('还没搞异常处理，暂时打印出来')

    @staticmethod
    def tmp_file_save_to_wav(root, track, channels, bits_per_sample, sample_rate, raw):
        filename = f"{track['TRACKNUMBER']} - {track['TITLE']}"
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        file_path = handle_repeat_file_name(root, filename, 'wav')
        logger.debug(f'将分轨文件暂存到{file_path}')
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(channels)  # 设置为立体声（两个通道）
            wf.setsampwidth(bits_per_sample // 8)  # 每个采样点2字节（16位）
            wf.setframerate(sample_rate)  # 设置采样率
            wf.writeframes(raw)
        logger.debug(f'分轨文件暂存完成')
        return file_path

    @staticmethod
    def is_audio_allowed_to_convert(file_path):
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_entries', 'stream=sample_fmt,codec_name', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            print(e.stderr)
            raise Exception('还没搞异常处理，暂时打印出来')
        data = json.loads(result.stdout)
        sample_fmt = data['streams'][0]['sample_fmt']
        codec_name = data['streams'][0]['codec_name']
        if codec_name == 'aac':
            logger.info(f'有损音频不会转换，文件{file_path}')
            return False
        if sample_fmt in ALLOWED_SAMPLE_FMT:
            return True
        else:
            logger.info(f'不支持的编码格式，编码格式为{sample_fmt}')
            return False

    @staticmethod
    def wav2flac(file_path, is_delete_origin_audio):  # 源文件是wav的转换为flac
        root, name = get_file_name_and_root(file_path)
        logger.info(f'正在将{file_path}转换为flac')
        AudioHandler.convert_wav_to_flac(file_path, root, name)
        logger.info(f'成功将{file_path}转换为flac')
        MetaHandler.id3_tag_to_vorbis(file_path, root, name)
        logger.info(f'成功将{file_path}的元数据转移到{os.path.join(root, name)}.flac')
        if is_delete_origin_audio:
            os.remove(file_path)
            logger.info(f'删除源文件{file_path}')

    @staticmethod
    def m4a2flac(file_path, is_delete_origin_audio):
        logger.info(f'正在将{file_path}暂时转换为wav，为后续处理')
        root, name = get_file_name_and_root(file_path)
        cmd = ['refalac', '-D', file_path, '-o', f'{os.path.join(root, name)}.wav']
        AudioHandler.common_cmd2flac(cmd, file_path, root, name)
        MetaHandler.mp4_to_vorbis(file_path, root, name)
        logger.info(f'成功将{file_path}的元数据转移到{os.path.join(root, name)}.flac')
        if is_delete_origin_audio:
            os.remove(file_path)
            logger.info(f'删除源文件{file_path}')

    @staticmethod
    def ape2flac(file_path, is_delete_origin_audio):
        logger.info(f'正在将{file_path}暂时转换为wav，为后续处理')
        root, name = get_file_name_and_root(file_path)
        cmd = ['mac', file_path, f'{os.path.join(root, name)}.wav', '-d', '-threads=16']
        AudioHandler.common_cmd2flac(cmd, file_path, root, name)
        MetaHandler.apev2_to_vorbis(file_path, root, name)
        logger.info(f'成功将{file_path}的元数据转移到{os.path.join(root, name)}.flac')
        if is_delete_origin_audio:
            os.remove(file_path)
            logger.info(f'删除源文件{file_path}')

    @staticmethod
    def tak2flac(file_path, is_delete_origin_audio):
        logger.info(f'正在将{file_path}暂时转换为wav，为后续处理')
        root, name = get_file_name_and_root(file_path)
        cmd = ['Takc', '-d', file_path, f'{os.path.join(root, name)}.wav']
        AudioHandler.common_cmd2flac(cmd, file_path, root, name)
        MetaHandler.apev2_to_vorbis(file_path, root, name)
        logger.info(f'成功将{file_path}的元数据转移到{os.path.join(root, name)}.flac')
        if is_delete_origin_audio:
            os.remove(file_path)
            logger.info(f'删除源文件{file_path}')

    @staticmethod
    def tta2flac(file_path, is_delete_origin_audio):
        logger.info(f'正在将{file_path}暂时转换为wav，为后续处理')
        root, name = get_file_name_and_root(file_path)
        cmd = ['ttaenc', '-d', file_path, f'{os.path.join(root, name)}.wav']
        AudioHandler.common_cmd2flac(cmd, file_path, root, name)
        MetaHandler.id3_tag_to_vorbis(file_path, root, name)
        logger.info(f'成功将{file_path}的元数据转移到{os.path.join(root, name)}.flac')
        if is_delete_origin_audio:
            os.remove(file_path)
            logger.info(f'删除源文件{file_path}')


HANDLERS = {
    '.wav': AudioHandler.wav2flac,
    '.m4a': AudioHandler.m4a2flac,
    '.ape': AudioHandler.ape2flac,
    '.tak': AudioHandler.tak2flac,
    '.tta': AudioHandler.tta2flac,
}


class MetaHandler:
    @staticmethod
    def get_catno_from_file(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith(('.log', '.txt')):
                    _, name = get_file_name_and_root(os.path.join(folder_path, file))
                    return name

    @staticmethod
    def id3_pic_to_vorbis(tag, target_audio) -> None:
        pic = Picture()
        pic.data = tag.data
        pic.mime = tag.mime
        pic.desc = tag.desc
        pic.type = tag.type
        target_audio.add_picture(pic)

    @staticmethod
    def id3_mapping_to_vorbis(field, version) -> str or list[str, str]:
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
                    vorbis_field = ID3v24_TO_VORBIS[field]
                else:
                    raise Exception(f"未成功检测到id3的版本")
            except KeyError:
                raise KeyError(f'未知的元数据字段{field}')
        return vorbis_field

    @staticmethod
    def id3_tag_to_vorbis(file_path, root, name) -> None:
        source_audio = mutagen.File(file_path)
        target_audio = mutagen.File(f'{os.path.join(root, name)}.flac')
        try:
            version = source_audio.tags.version[1]
        except AttributeError:
            logger.info(f'{file_path}没有元数据，无需传递')
            return
        for field, tag in source_audio.tags.items():
            vorbis_field = MetaHandler.id3_mapping_to_vorbis(field, version)
            if isinstance(vorbis_field, list):
                metadatas = tag.text[0].split("/")
                for field, metadata in zip(vorbis_field, metadatas):
                    target_audio[field] = metadata
            else:
                if vorbis_field.startswith('APIC:'):
                    MetaHandler.id3_pic_to_vorbis(tag, target_audio)
                elif 'RATING' in vorbis_field:
                    target_audio[vorbis_field] = [str(tag.rating)]
                else:
                    target_audio[vorbis_field] = [str(i) for i in tag.text]
        target_audio.save()

    @staticmethod
    def apev2_pic_to_vorbis(tag, field, target_audio) -> None:
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

    @staticmethod
    def apev2_to_vorbis(file_path, root, name) -> None:
        source_audio = mutagen.File(file_path)
        target_audio = mutagen.File(f'{os.path.join(root, name)}.flac')
        if source_audio.tags:
            for field, tag in source_audio.tags.items():
                if field.startswith('Cover Art'):
                    MetaHandler.apev2_pic_to_vorbis(tag, field, target_audio)
                    continue
                elif field in APEV2_TO_VORBIS:
                    vorbis_field = APEV2_TO_VORBIS[field]
                else:
                    vorbis_field = field
                target_audio[vorbis_field] = [i.decode() for i in tag.value.encode().split(b'\0')]
            target_audio.save()

    @staticmethod
    def mp4_mapping_to_vorbis(field) -> str or list[str, str]:
        if field.startswith('----'):
            if 'musicbrainz' in field.lower():
                vorbis_field = ('MUSICBRAINZ_' + field.replace('----:com.apple.iTunes:MusicBrainz', '').replace(' ',
                                                                                                                '')).upper()
            elif 'acoustid' in field.lower():
                vorbis_field = field.replace('----:com.apple.iTunes:', '').replace(' ', "_").upper()
            else:
                vorbis_field = field.replace('----:com.apple.iTunes:', '').replace(' ', "").upper()
        elif field == 'covr':
            vorbis_field = field
        elif field.startswith('xid'):
             vorbis_field = 'xid'
        else:
            vorbis_field = MP4_TO_VORBIS[field]
        return vorbis_field

    @staticmethod
    def mp4_pic_to_vorbis(tag, target_audio) -> None:
        for p in tag:
            pic = Picture()
            img = Image.open(io.BytesIO(p))
            pic.data = p
            pic.mime = "image/{0}".format(img.format.lower())
            pic.type = PictureType.COVER_FRONT
            target_audio.add_picture(pic)

    @staticmethod
    def mp4_to_vorbis(file_path, root, name):
        source_audio = mutagen.File(file_path)
        target_audio = mutagen.File(f'{os.path.join(root, name)}.flac')
        if source_audio.tags:
            for field, tag in source_audio.tags.items():
                vorbis_field = MetaHandler.mp4_mapping_to_vorbis(field)

                if isinstance(vorbis_field, list):
                    for field, metadata in zip(vorbis_field, tag[0]):
                        target_audio[field] = str(metadata)
                elif vorbis_field == 'xid':
                    for t in tag:
                        t = t.split(":")
                        target_audio["CONTENTPROVIDER"] = t[0]
                        target_audio[t[1]] = t[2]
                elif vorbis_field == '©too':
                    continue
                else:
                    if vorbis_field == 'covr':
                        MetaHandler.mp4_pic_to_vorbis(tag, target_audio)
                    else:
                        tag = [str(i.decode()) if isinstance(i, bytes) else str(i) for i in tag]
                        target_audio[vorbis_field] = tag
            target_audio.save()

    @staticmethod
    def get_catno_from_folder_name(folder_name, reg_exp):
        results = re.match(reg_exp, folder_name)
        if results:
            catno = results.group(1)
            return catno
        else:
            return None

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
    def get_audio_data(file_path):
        cmd = ['ffprobe.exe', '-v', 'quiet', '-print_format', 'json', '-show_entries',
               'stream=bits_per_raw_sample,channels,sample_rate', file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)['streams'][0]
        sample_rate, channels, bits_per_sample = int(data['sample_rate']), int(data['channels']), int(
            data['bits_per_raw_sample'])

        return sample_rate, channels, bits_per_sample

    @staticmethod
    def split_flac_with_cue(file_path, is_delete_single_track):
        source_root, source_name = get_file_name_and_root(file_path)
        if os.path.exists(f'{os.path.join(source_root, source_name)}.cue'):
            tracks = CueParser.paser_cue_data(f'{os.path.join(source_root, source_name)}.cue')
            sample_rate, channels, bits_per_sample = Splitter.get_audio_data(file_path)
            logger.info(f"正在将{file_path}转换为pcm数据缓存到内存中")
            process_decode = subprocess.Popen(['flac.exe', '-d', '--stdout', file_path], stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            pcm_data, _ = process_decode.communicate()
            logger.info(f"成功转换{file_path}为pcm数据")
            for i, track in enumerate(tracks):
                try:
                    logger.info(f'正在分割第{i+1}首曲目，曲目名为{track["TITLE"]}')
                except KeyError:
                    logger.info(f'正在分割第{i + 1}首曲目，该音频无曲目名')

                start_frame = track['INDEX01']
                end_frame = tracks[i + 1]['INDEX01'] if i < len(tracks) - 1 else None
                raw = Splitter.extract_pcm_segment_frame(pcm_data, sample_rate, bits_per_sample, channels, start_frame,
                                                         end_frame)

                logger.info('正在将曲目转换成wav缓存到硬盘')
                split_audio_path_wav = AudioHandler.tmp_file_save_to_wav(source_root, track, channels, bits_per_sample,
                                                                     sample_rate, raw)
                logger.info('缓存成功')
                split_audio_root, split_audio_name = get_file_name_and_root(split_audio_path_wav)
                logger.info('正在将曲目转换成flac')
                AudioHandler.convert_wav_to_flac(split_audio_path_wav, split_audio_root, split_audio_name)
                logger.info('成功转换为flac')
                split_audio_path_flac = f"{os.path.join(split_audio_root, split_audio_name)}.flac"
                split_audio_flac = mutagen.File(split_audio_path_flac)
                for field, tag in track.items():
                    if field != 'INDEX01':
                        split_audio_flac[field] = str(tag)
                split_audio_flac.save()
                logger.info('成功将cuesheet的元数据写入分轨音频')
                os.remove(split_audio_path_wav)
                logger.info('成功删除缓存的wav')
            if is_delete_single_track:
                os.remove(f'{os.path.join(source_root, source_name)}.cue')
                os.remove(file_path)
                logger.info('成功删除源文件和源文件的cue')
            logger.info(f'{file_path}分轨完成')
            print('-'*50)
        else:
            logger.debug(f'{file_path}没有cue文件')


class CueParser:
    @staticmethod
    def strQ2B(ustring):
        """全角转半角"""
        rstring = ""
        for uchar in ustring:
            inside_code = ord(uchar)
            if inside_code == 12288:  # 全角空格直接转换
                inside_code = 32
            elif 65281 <= inside_code <= 65374:  # 全角字符（除空格）根据关系转化
                inside_code -= 65248
            rstring += chr(inside_code)
        return rstring

    @staticmethod
    def paser_cue_data(file_path):
        with open(file_path, encoding='utf-8') as f:
            lines = [CueParser.strQ2B(line.strip()) for line in f.readlines()]

        album_info_flag = True
        album_info = {}
        tracks_info = []
        current_track = None

        for line in lines:
            cmd, _, args = line.partition(' ')
            args = args.strip(' "')

            if cmd == 'REM':
                field, _, tag = args.partition(' ')
                tag = tag.strip(' "')
                if tag != '':
                    if album_info_flag:
                        album_info[field] = tag
                    else:
                        current_track[field] = tag

            elif cmd == 'FILE':
                continue
                # fpath, _ = args.rsplit(' ', 1)
                # fpath = fpath.strip(' "')
                # album_info['FILE'] = fpath

            elif cmd == 'TRACK':
                album_info_flag = False
                num, _, __ = args.partition(' ')
                if current_track:
                    tracks_info.append(current_track)
                current_track = {'TRACKNUMBER': str(int(args.split(' ')[0]))}  # 只取编号

            elif cmd == 'INDEX':
                num, _, pos = args.partition(' ')
                if num == '01':
                    minute, sec, frame = pos.split(':')
                    frames = (int(minute) * 60 + int(sec)) * 75 + int(frame)
                    current_track['INDEX01'] = frames

            else:
                field, tag = cmd, args
                if album_info_flag:
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

        tracks_info.append(current_track)
        album_info["TOTALTRACKS"] = str(len(tracks_info))
        tracks_info = [i | album_info for i in tracks_info]
        return tracks_info