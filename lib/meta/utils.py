import re


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


