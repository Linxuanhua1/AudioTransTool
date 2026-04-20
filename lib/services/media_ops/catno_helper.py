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
        例：["ABCD-15599", "ABCD-15600", "ABCD-15601"] → "ABCD-15599~01"
        """
        prefix_match = re.match(r"([A-Z]+)-(\d+)", nums[0])
        prefix    = prefix_match.group(1)
        start_str = prefix_match.group(2)
        digit_len = len(start_str)

        end_str = re.match(r"[A-Z]+-(\d+)", nums[-1]).group(1)

        # 找最后不同的部分作为后缀
        suffix = "0"
        for i in range(digit_len):
            if start_str[i] != end_str[i]:
                suffix = end_str[i:]
                break

        return f"{prefix}-{start_str}~{suffix}"
