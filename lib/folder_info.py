import os, mutagen
from decimal import Decimal
from lib.audio_handler import AudioProbe


PRIORITY_ORDER = ['.dsf', '.flac', '.wav', '.m4a', '.mp3', '.ogg']
AUDIO_TYPE_QUALITY = {
    '.dsf': 4,
    '.wav': 3,
    '.flac': 2,
    '.m4a': 1,
    '.mp3': 1,
    '.ogg': 1
}


def scan_folder(folder_path: str):
    """扫描文件夹，返回文件状态和音频列表"""
    has_log = False
    has_pic = False
    has_iso = False
    has_bdmv = False
    has_mp4 = False
    has_mkv = False

    audio_files = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)

            if ext == '.jxl':
                has_pic = True
            elif ext == '.log':
                has_log = True
            elif ext in ['.iso', '.vob']:
                has_iso = True
            elif ext == '.bdmv':
                has_bdmv = True
            elif ext == '.mkv':
                has_mkv = True
            elif ext == '.mp4':
                has_mp4 = True

            if ext in AUDIO_TYPE_QUALITY:
                audio_files.append((ext, full_path))

    status = {
        "has_log": has_log,
        "has_pic": has_pic,
        "has_iso": has_iso,
        "has_bdmv": has_bdmv,
        "has_mp4": has_mp4,
        "has_mkv": has_mkv
    }
    return status, audio_files


def get_best_audio_info(audio_files):
    """根据优先级和音质选出最佳音频信息"""
    best_quality = -1
    best_info = ("N/A", "N/A")
    found_formats = set()

    for ext in PRIORITY_ORDER:
        for file_ext, file_path in audio_files:
            if file_ext != ext:
                continue

            found_formats.add(file_ext)
            if AUDIO_TYPE_QUALITY[file_ext] > best_quality:
                info = AudioProbe.probe(file_path)

                if ext == '.flac':
                    sample_rate = f"{Decimal(int(info['sample_rate'])) / 1000}kHz"
                    bit_depth = f"{int(info['bits_per_raw_sample'])}bit"
                    best_info = (bit_depth, sample_rate)
                elif ext == '.wav':
                    sample_rate = f"{Decimal(int(info['sample_rate'])) / 1000}kHz"
                    bit_depth = f"{int(info['bits_per_sample'])}bit"
                    best_info = (bit_depth, sample_rate)
                elif ext in ['.m4a', '.mp3', '.ogg']:
                    bitrate = f"{round(Decimal(int(info['bit_rate'])) / 1000)}k"
                    best_info = ("N/A", bitrate)
                elif ext == '.dsf':
                    sample_rate = str(Decimal(int(info['bit_rate'])) / 2000000)
                    match sample_rate:
                        case '2.8224':
                            sample_rate = 'DSD64'
                        case '5.6448':
                            sample_rate = 'DSD128'
                        case '11.2896':
                            sample_rate = 'DSD256'
                        case '22.5792':
                            sample_rate = 'DSD512'
                        case '45.1584':
                            sample_rate = 'DSD1024'
                    best_info = ("N/A", sample_rate)

                best_quality = AUDIO_TYPE_QUALITY[file_ext]
            break

    return best_info, found_formats


def build_suffix(found_formats, status):
    """拼接文件格式后缀"""
    suffix = "[" + "+".join(
        sorted([fmt[1:] for fmt in found_formats], key=lambda x: PRIORITY_ORDER.index("." + x))
    )
    if status["has_mp4"]:
        suffix += "+mp4"
    if status["has_mkv"]:
        suffix += "+mkv"
    if status["has_bdmv"]:
        suffix += "+bdmv"
    if status["has_iso"]:
        suffix += "+iso"
    if status["has_pic"]:
        suffix += "+jxl"
    suffix += "]"
    return suffix


def determine_label(status, best_info, folder_path):
    """判断音频来源标签"""
    if status["has_log"]:
        return "EAC"
    elif best_info[0] == "32bit":
        return "e-onkyo"
    else:
        return detect_source(folder_path)


def detect_source(folder_path: str) -> str:
    for file in os.listdir(folder_path):
        ext = file.lower()
        file_path = os.path.join(folder_path, file)

        # 直接根据扩展名处理
        if ext.endswith(('.wma', '.mp3', '.ogg', '.m4a')):
            return "WEB"

        if not ext.endswith(('.wav', '.flac', '.dsf')):
            continue

        # 处理 wav / flac
        audio = mutagen.File(file_path)
        if not audio or not audio.tags:
            return "WEB"

        # 标签取值（缺省用空字符串 / None）
        if ext.endswith('.dsf'):
            try:
                comment = str(audio.tags.getall('COMM')[0])
            except IndexError:
                comment = ""
        else:
            comment = audio.tags.get('COMMENT', [''])[0]
            qbz_tid = audio.tags.get('QBZ:TID', [None])[0]
            url = audio.tags.get('URL', [''])[0]
            merchant_name = audio.tags.get('MERCHANTNAME', [''])[0]

            # 优先级判断
            if qbz_tid:
                return "Qobuz"
            if "tidal" in url.lower():
                return "Tidal"
            if "amazon" in merchant_name.lower():
                return "Amazon"

        # 用映射表简化 COMMENT 判断
        comment_map = {
            "JASRAC /": "MORA",
            "OTOTOY": "OTOTOY",
            "bandcamp": "Bandcamp",
        }
        for key, value in comment_map.items():
            if key.lower() in comment.lower():
                return value

        if ext.endswith('.dsf'):  # 最后判断，因为部分dsf来源于mora，ototoy和e-onkyo
            return "ISO转DSF"

        return "WEB"

def analyze_folder_file(folder_path: str):
    """统一入口函数"""
    status, audio_files = scan_folder(folder_path)
    best_info, found_formats = get_best_audio_info(audio_files)
    suffix = build_suffix(found_formats, status)
    label = determine_label(status, best_info, folder_path)
    return suffix, label, best_info
