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
    status = {
        "has_log": False,
        "has_pic": False,
        "has_iso": False,
        "has_bdmv": False,
        "has_mp4": False,
        "has_mkv": False
    }

    audio_files = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)

            if ext == '.jxl':
                status["has_pic"] = True
            elif ext == '.log':
                status["has_log"] = True
            elif ext in ['.iso', '.vob']:
                status["has_iso"] = True
            elif ext == '.bdmv':
                status["has_bdmv"] = True
            elif ext == '.mkv':
                status["has_mkv"] = True
            elif ext == '.mp4':
                status["has_mp4"] = True

            if ext in AUDIO_TYPE_QUALITY:
                audio_files.append((ext, full_path))

    return status, audio_files


def get_best_audio_info(audio_files):
    """选出优先级最高、音质最好的音频文件"""
    # 按 PRIORITY_ORDER 排序
    audio_files.sort(key=lambda x: PRIORITY_ORDER.index(x[0]))
    found_formats = {ext for ext, _ in audio_files}

    best_info = ("N/A", "N/A")

    best_audio_ext, file_path = audio_files[0]
    info = AudioProbe.probe(file_path)
    match best_audio_ext:
        case '.flac':
            sample_rate = f"{Decimal(int(info['sample_rate'])) / 1000}kHz"
            bit_depth = f"{int(info['bits_per_raw_sample'])}bit"
            best_info = (bit_depth, sample_rate)
        case '.wav':
            sample_rate = f"{Decimal(int(info['sample_rate'])) / 1000}kHz"
            bit_depth = f"{int(info['bits_per_sample'])}bit"
            best_info = (bit_depth, sample_rate)
        case '.m4a', '.mp3', '.ogg':
            bitrate = f"{round(Decimal(int(info['bit_rate'])) / 1000)}k"
            best_info = ("N/A", bitrate)
        case '.dsf':
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

    return best_info, found_formats


def build_suffix(found_formats, status):
    """拼接文件格式后缀"""
    suffix = "[" + "+".join(
        sorted([fmt[1:] for fmt in found_formats], key=lambda x: PRIORITY_ORDER.index("." + x))
    )
    for key, tag in [("has_mp4", "mp4"), ("has_mkv", "mkv"), ("has_bdmv", "bdmv"), ("has_iso", "iso"), ("has_pic", "jxl")]:
        if status[key]:
            suffix += "+" + tag
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
    """只解析必要文件"""
    for file in os.listdir(folder_path):
        ext = file.lower()
        file_path = os.path.join(folder_path, file)

        if ext.endswith(('.wma', '.mp3', '.ogg', '.m4a')):
            return "WEB"

        if not ext.endswith(('.wav', '.flac', '.dsf')):
            continue

        audio = mutagen.File(file_path)
        if not audio or not audio.tags:
            return "WEB"

        comment_map = {
            "JASRAC /": "MORA",
            "OTOTOY": "OTOTOY",
            "bandcamp": "Bandcamp",
        }

        if ext.endswith('.dsf'):
            try:
                comment = str(audio.tags.getall('COMM')[0])
            except IndexError:
                comment = ""
        else:
            comment = audio.tags.get('COMMENT', [''])[0]
            qbz_tid = audio.tags.get('QBZ:TID', [None])[0]
            dizzy_lab = audio.tags.get('COMMENTS', [''])[0]
            url = audio.tags.get('URL', [''])[0]
            merchant_name = audio.tags.get('MERCHANTNAME', [''])[0]

            if qbz_tid:
                return "Qobuz"
            if "tidal" in url.lower():
                return "Tidal"
            if "amazon" in merchant_name.lower():
                return "Amazon"
            if 'dizzy' in dizzy_lab.lower():
                return "DIZZYLAB"

        for key, value in comment_map.items():
            if key.lower() in comment.lower():
                return value

        if ext.endswith('.dsf'):
            return "ISO转DSF"

        return "WEB"


def analyze_folder_file(folder_path: str):
    """统一入口函数"""
    status, audio_files = scan_folder(folder_path)
    best_info, found_formats = get_best_audio_info(audio_files)
    suffix = build_suffix(found_formats, status)
    label = determine_label(status, best_info, folder_path)
    return suffix, label, best_info
