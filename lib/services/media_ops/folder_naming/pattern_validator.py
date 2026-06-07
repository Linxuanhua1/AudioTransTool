import logging

from lib.services.constants import RENAMER_SUPPORTED_EXTRACT_FIELD
from .field_extractor import FieldExtractor
from .folder_scanner.match_rules import SourceMatcher


logger = logging.getLogger("musicbox.services.media_ops.folder_naming.pattern_validator")


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
            logger.info("请修改 config.toml [rename] 后重新运行", extra={"plain": True})
            return False

        cls._pattern_confirmed = True
        return True

    @staticmethod
    def print_config(config: dict) -> None:
        """打印当前配置。"""
        logger.info("\n当前重命名配置（来自 config.toml [rename]）：", extra={"plain": True})
        logger.info(f"  提取正则:   {config['extract_pattern']}", extra={"plain": True})
        logger.info(f"  提取变量:   {config['extract_groups']}", extra={"plain": True})
        logger.info(f"  输出模板:   {config['output_template']}", extra={"plain": True})

        unknown = PatternValidator.validate_template(config)
        if unknown:
            raise Exception(unknown)

        # 打印来源匹配规则（[rename.match_rules]），让用户确认
        needed = FieldExtractor.referenced_fields(config['output_template'])
        if needed & {"SOURCE", "SCORE"}:
            logger.info("\n  来源匹配规则（来自 [rename.match_rules]，按顺序匹配）：", extra={"plain": True})
            for line in SourceMatcher.from_config(config).describe():
                logger.info(line, extra={"plain": True})

    @staticmethod
    def validate_template(config: dict) -> list[str]:
        """验证模板中的变量是否都在支持的字段列表中。"""
        template_vars = FieldExtractor.referenced_fields(config['output_template'])
        unknown_vars = template_vars - RENAMER_SUPPORTED_EXTRACT_FIELD
        return list(unknown_vars)
