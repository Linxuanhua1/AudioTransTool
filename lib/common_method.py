import os, re, datetime, logging, multiprocessing, sys
from concurrent_log_handler import ConcurrentRotatingFileHandler
import logging.handlers
from decimal import Decimal


PRIORITY_ORDER = ['.dsf', '.flac', '.wav', '.m4a', '.mp3', '.ogg']
AUDIO_TYPE_QUALITY = {
    '.dsf': 4,
    '.wav': 3,
    '.flac': 2,
    '.m4a': 1,
    '.mp3': 1,
    '.ogg': 1
}


def custom_safe_filename(name):
    name = name.replace('/', '／')
    name = name.replace('?', '？')
    name = name.replace(':', '：')
    name = name.replace('\\', '＼')
    name = name.replace('*', '＊')
    name = name.replace('"', '＂')
    name = name.replace('<', '＜')
    name = name.replace('>', '＞')
    name = name.replace('|', '｜')
    name = re.sub(r'\s+$', '', name)  # 去除结尾空格
    return name.strip()


def check_input_folder_path(is_double_check=False):
    while True:
        folder_path = input('请输入文件夹：')
        if folder_path in ('#', "$"):
            return folder_path
        if not os.path.isdir(folder_path):
            print('请输入文件夹，而不是文件')
            continue
        if not os.path.exists(folder_path):
            print('文件夹路径不存在，请重新输入文件夹')
            continue

        if is_double_check:
            is_start = input("请输入Y/N来确认是否是该文件夹：")
            if is_start.lower() == 'y':
                print(f'文件夹为：{folder_path}')
                break
        else:
            break
    return folder_path.strip()


def get_root_dir_and_name(file_path) -> tuple[str, str]:
    root, file = os.path.split(file_path)
    name, _ = os.path.splitext(file)
    return root, name


def check_multi_result(result):
    if result['release-count'] > 1:
        for release in result['release-list']:
            if release['medium-list'][0]['format'] == "CD":
                return release['id']
    elif result['release-count'] == 1:
        return result['release-list'][0]['id']
    else:
        return None


def handle_repeat_file_name(root, filename, ext, suffix=1):
    # 先生成基本的文件路径
    file_path = os.path.join(root, f'{filename}.{ext}')
    # 如果文件已存在，递增后缀并递归检查
    while os.path.exists(file_path):
        file_path = os.path.join(root, f'{filename}({suffix}).{ext}')
        suffix += 1  # 递增后缀
    return file_path


def unfold_catno(catno):
    match = re.match(r"([A-Z]+-\d+)[~～](\d+)", catno)
    prefix, start_full, end_suffix = match.group(1), match.group(1).split('-')[1], match.group(2)
    start_num = int(start_full)
    end_suffix = int(end_suffix)

    # 获取起始编号的位数
    digit_len = len(start_full)

    # 补全结束编号
    end_full = int(str(start_num)[:-len(str(end_suffix))] + str(end_suffix))
    # 如果起始编号的后缀比 end_suffix 大，说明是跨位了，例如 15599~01 应该是 15601
    if end_full < start_num:
        end_full += 10 ** len(str(end_suffix))

    # 构建编号列表
    catno_list = [f"{prefix.split('-')[0]}-{str(i).zfill(digit_len)}" for i in range(start_num, end_full + 1)]

    return catno_list


def fold_catno(nums):
    # 提取前缀和编号部分
    prefix_match = re.match(r"([A-Z]+)-(\d+)", nums[0])

    prefix = prefix_match.group(1)
    start_num_str = prefix_match.group(2)
    digit_len = len(start_num_str)
    start_num = int(start_num_str)

    # 取最后一个编号
    end_num = int(re.match(r"[A-Z]+-(\d+)", nums[-1]).group(1))

    # 提取后缀部分（跟开始编号比较）
    start_str = str(start_num)
    end_str = str(end_num)

    # 找末尾不同的部分作为后缀
    for i in range(digit_len):
        if start_str[i] != end_str[i]:
            suffix = end_str[i:]
            break
    else:
        suffix = "0"

    return f"{prefix}-{start_str}~{suffix}"


def listener_process(queue):
    logger = logging.getLogger()

    formatter = logging.Formatter('%(asctime)s | %(processName)s | %(levelname)s | %(message)s')

    # 设置终端输出流处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setStream(sys.stdout)
    # 在Windows上可能需要重新配置stdout
    if sys.platform.startswith('win'):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    console_handler.setFormatter(formatter)

# -------------------------------- 一般日志 ------------------------------------------
    # 设置文件滚动输出处理器 (按大小滚动)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    log_filename = f'logs/main_{now_str}.log'
    os.makedirs('logs', exist_ok=True)

    # 使用 RotatingFileHandler，指定最大文件大小和备份文件个数
    max_log_size = 1024 * 500  # 设置文件最大大小为 500k

    file_handler = ConcurrentRotatingFileHandler(
        log_filename, maxBytes=max_log_size, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # 设置文件处理器的日志级别为 DEBUG

# ------------------------------- 错误日志 -------------------------------------------
    error_log_filename = f'logs/error_{now_str}.log'
    error_file_handler = ConcurrentRotatingFileHandler(
        error_log_filename, maxBytes=max_log_size, encoding='utf-8')
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)
    logger.setLevel(logging.DEBUG)  # 设置总体日志级别

    while True:
        record = queue.get()
        if record is None:  # 退出信号
            break
        logger.handle(record)


def setup_logger(manager):
    queue = manager.Queue(-1)
    listener = multiprocessing.Process(target=listener_process, args=(queue,))
    listener.start()

    # 创建主进程的logger，设置QueueHandler
    logger = logging.getLogger(__name__)
    handler = logging.handlers.QueueHandler(queue)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger, queue, listener


# 配置日志处理器，在 worker 中使用QueueHandler
def setup_worker_logger(logger, queue):
    handler = logging.handlers.QueueHandler(queue)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def check_folder_file(folder_full_path: str):
    import sys
    sys.path.append(os.path.dirname(os.getcwd()))
    from lib.audio_handler import AudioHandler

    has_log = False
    has_pic = False
    has_iso = False
    has_bdmv = False
    has_mp4 = False
    has_mkv = False

    audio_files = []

    for root, dirs, files in os.walk(folder_full_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()

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

            # 收集音频文件
            if ext in AUDIO_TYPE_QUALITY:
                full_path = os.path.join(root, file)
                audio_files.append((ext, full_path))

    # 找出最高音质的音频文件
    best_quality = -1
    best_info = ("N/A", "N/A")
    found_formats = set()

    for ext in PRIORITY_ORDER:
        for file_ext, file_path in audio_files:
            if file_ext == ext:
                found_formats.add(file_ext)

                # 如果这个格式更好，就更新 best_info
                if AUDIO_TYPE_QUALITY[file_ext] > best_quality:
                    info = AudioHandler.get_audio_data(file_path)
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
                        sample_rate = f"{Decimal(int(info['bit_rate'])) / 1000000}MHz"
                        best_info = ("N/A", sample_rate)
                    best_quality = AUDIO_TYPE_QUALITY[file_ext]
                break  # 同一种格式只看一个文件就好

    # 拼接格式信息
    suffix = "[" + "+".join(
        sorted([fmt[1:] for fmt in found_formats], key=lambda x: PRIORITY_ORDER.index("." + x))
    )

    if has_mp4:
        suffix += "+mp4"
    if has_mkv:
        suffix += "+mkv"
    if has_bdmv:
        suffix += "+bdmv"
    if has_iso:
        suffix += "+iso"
    if has_pic:
        suffix += "+jxl"
    suffix += "]"

    # 标签
    if has_log:
        label = "EAC"
    elif best_info[0] == "32bit":
        label = 'e-onkyo'
    else:
        label = AudioHandler.check_source(folder_full_path)

    return suffix, label, best_info
