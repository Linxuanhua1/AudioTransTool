import re

from lib.organizer.folder_renamer.consts import RENAMER_SUPPORTED_EXTRACT_FIELD


class PatternValidator:
    _pattern_confirmed = False

    @classmethod
    def confirm_pattern(cls, config: dict) -> bool:
        """
        确认重命名配置（首次运行时提示一次）。

        Args:
            config: RenameConfig 实例

        Returns:
            用户是否确认配置
        """
        if cls._pattern_confirmed:
            return True

        PatternValidator.print_config(config)
        
        choice = input("\n是否使用此配置？(y/n，直接回车=y): ").strip().lower()
        if choice and choice != "y":
            print("请修改 config.toml [rename] 后重新运行")
            return False

        cls._pattern_confirmed = True
        return True

    @staticmethod
    def print_config(config: dict) -> None:
        """打印当前配置。"""
        print("\n当前重命名配置（来自 config.toml [rename]）：")
        print(f"  提取正则:   {config['extract_pattern']}")
        print(f"  提取变量:   {config['extract_groups']}")
        print(f"  输出模板:   {config['output_template']}")

        unknown = PatternValidator.validate_template(config)
        if unknown:
            raise Exception(unknown)

    @staticmethod
    def validate_template(config: dict) -> list[str]:
        """验证模板中的变量是否都在支持的字段列表中。"""
        pattern = r'\{(\w+)\}'
        template_vars = set(re.findall(pattern, config['output_template']))
        unknown_vars = template_vars - RENAMER_SUPPORTED_EXTRACT_FIELD
        return list(unknown_vars)
