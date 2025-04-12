import os, re, datetime, logging


def check_input_folder_path(is_double_check=True):
    while True:
        folder_path = input('请输入文件夹：')
        if folder_path == '#':
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
    return folder_path


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


def unfold_catno(s):
    match = re.match(r"([A-Z]+-\d+)\~(\d+)", s)

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


def setup_logger():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H")
    os.makedirs('logs', exist_ok=True)  # 确保目录存在
    log_filename = f'logs/{now_str}.log'
    logger = logging.getLogger(__name__)
    handler = logging.FileHandler(log_filename)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

