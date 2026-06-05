import re


# --------------------------------------------------------------------------- #
# CatNoHelper
# --------------------------------------------------------------------------- #

class CatNoHelper:
    """
    无状态工具类，所有方法为静态方法。

    光盘编号格式示例
    ---------------
    折叠形式：ABCD-15599~01   （表示 ABCD-15599 到 ABCD-15601）
    展开列表：["ABCD-15599", "ABCD-15600", "ABCD-15601"]
    """

    # ------------------------------------------------------------------ #
    # 光盘编号展开 / 折叠
    # ------------------------------------------------------------------ #

    @staticmethod
    def unfold(catno: str) -> list[str]:
        """
        将折叠的编号范围展开为列表。
        例：ABCD-15599~01 → ["ABCD-15599", "ABCD-15600", "ABCD-15601"]
        """
        match = re.match(r"([A-Z]+-\d+)[~～](\d+)", catno)
        if not match:
            return [catno]

        prefix_full = match.group(1)           # "ABCD-15599"
        prefix      = prefix_full.split("-")[0] # "ABCD"
        start_str   = prefix_full.split("-")[1] # "15599"
        end_suffix  = match.group(2)            # "01"

        digit_len = len(start_str)
        start_num = int(start_str)

        # 补全结束编号
        end_full = int(start_str[: digit_len - len(end_suffix)] + end_suffix)
        if end_full < start_num:
            end_full += 10 ** len(end_suffix)

        return [
            f"{prefix}-{str(i).zfill(digit_len)}"
            for i in range(start_num, end_full + 1)
        ]

    @staticmethod
    def fold(nums: list[str]) -> str:
        """
        将连续编号列表折叠回紧凑字符串。
        支持：
        1. ["ABCD-15599", "ABCD-15600", "ABCD-15601"] -> "ABCD-15599~01"
        2. ["FVCG-1339-2", "FVCG-1339-1"] -> "FVCG-1339"
        """
        if len(nums) == 1:
            return nums[0]

        def split_last_num(s: str):
            m = re.match(r"^(.*)-(\d+)$", s)
            if not m:
                raise ValueError(f"编号格式不正确: {s}")
            return m.group(1), int(m.group(2))

        # 先按最后一段数字排序
        nums = sorted(nums, key=lambda x: split_last_num(x)[1])

        # 只对 xxx-数字-数字 这种形式做“直接折叠成前半部分”
        multi_prefixes = []
        all_multi_level = True
        for x in nums:
            m = re.match(r"^(.+-\d+)-(\d+)$", x)
            if not m:
                all_multi_level = False
                break
            multi_prefixes.append(m.group(1))

        if all_multi_level and len(set(multi_prefixes)) == 1:
            return multi_prefixes[0]

        # 普通格式：ABCD-15599 -> ABCD-15599~01
        m_start = re.match(r"^([A-Za-z]+)-(\d+)$", nums[0])
        m_end = re.match(r"^([A-Za-z]+)-(\d+)$", nums[-1])

        if not m_start or not m_end:
            raise ValueError(f"无法按普通编号格式折叠: {nums}")

        prefix = m_start.group(1)
        start_str = m_start.group(2)
        end_str = m_end.group(2)

        digit_len = len(start_str)
        suffix = "0"
        for i in range(digit_len):
            if start_str[i] != end_str[i]:
                suffix = end_str[i:]
                break

        return f"{prefix}-{start_str}~{suffix}"