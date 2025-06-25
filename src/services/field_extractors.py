from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import re

from ..utils.logger import get_logger

logger = get_logger("field_extractors")


class FieldExtractor(ABC):
    """字段提取器抽象基类"""

    @abstractmethod
    def extract(self, email_data: Dict[str, Any]) -> str:
        """
        从邮件数据中提取字段值

        Args:
            email_data: 邮件数据字典

        Returns:
            提取的字段值字符串
        """
        pass

    def _safe_get(self, email_data: Dict[str, Any], key: str, default: str = "") -> str:
        """
        安全获取字段值，处理空值和异常

        Args:
            email_data: 邮件数据字典
            key: 字段名
            default: 默认值

        Returns:
            字段值字符串
        """
        try:
            value = email_data.get(key)
            if value is None:
                return default

            # 如果是字符串，直接返回
            if isinstance(value, str):
                return value.strip()

            # 如果是其他类型，转换为字符串
            return str(value).strip()

        except Exception as e:
            logger.warning(f"获取字段 {key} 失败: {e}")
            return default

    def _handle_encoding_error(self, text: str) -> str:
        """
        处理编码错误，提供容错机制

        Args:
            text: 原始文本

        Returns:
            处理后的文本
        """
        try:
            # 如果文本包含特殊字符，尝试修复
            if text and isinstance(text, str):
                # 移除控制字符
                cleaned_text = re.sub(
                    r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
                return cleaned_text.strip()
            return text
        except Exception as e:
            logger.warning(f"处理编码错误失败: {e}")
            return text if text else ""


class SenderExtractor(FieldExtractor):
    """发件人字段提取器"""

    def extract(self, email_data: Dict[str, Any]) -> str:
        """
        提取发件人信息

        Args:
            email_data: 邮件数据字典

        Returns:
            发件人邮箱地址或显示名称
        """
        try:
            sender = self._safe_get(email_data, 'sender', '')

            if not sender:
                logger.debug("发件人字段为空")
                return ""

            # 处理编码问题
            sender = self._handle_encoding_error(sender)

            # 提取邮箱地址（如果包含显示名称）
            # 格式可能是: "显示名称 <email@example.com>" 或 "email@example.com"
            email_match = re.search(r'<([^>]+)>', sender)
            if email_match:
                # 如果有尖括号，提取括号内的邮箱地址
                extracted_email = email_match.group(1).strip()
                logger.debug(f"从发件人字段提取邮箱: {extracted_email}")
                return extracted_email

            # 如果没有尖括号，检查是否是有效的邮箱格式
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, sender.strip()):
                logger.debug(f"发件人字段是有效邮箱: {sender}")
                return sender.strip()

            # 如果不是标准邮箱格式，返回原始值（可能是显示名称）
            logger.debug(f"发件人字段非标准格式: {sender}")
            return sender.strip()

        except Exception as e:
            logger.error(f"提取发件人失败: {e}")
            return ""


class SubjectExtractor(FieldExtractor):
    """邮件主题字段提取器"""

    def extract(self, email_data: Dict[str, Any]) -> str:
        """
        提取邮件主题

        Args:
            email_data: 邮件数据字典

        Returns:
            邮件主题字符串
        """
        try:
            subject = self._safe_get(email_data, 'subject', '')

            if not subject:
                logger.debug("邮件主题字段为空")
                return ""

            # 处理编码问题
            subject = self._handle_encoding_error(subject)

            # 移除主题中的多余空白字符
            subject = re.sub(r'\s+', ' ', subject).strip()

            logger.debug(
                f"提取邮件主题: {subject[:50]}{'...' if len(subject) > 50 else ''}")
            return subject

        except Exception as e:
            logger.error(f"提取邮件主题失败: {e}")
            return ""


class FieldExtractorFactory:
    """字段提取器工厂类"""

    _extractors = {
        'sender': SenderExtractor(),
        'subject': SubjectExtractor(),
    }

    @classmethod
    def get_extractor(cls, field_type: str) -> Optional[FieldExtractor]:
        """
        根据字段类型获取对应的提取器

        Args:
            field_type: 字段类型

        Returns:
            字段提取器实例，如果类型不支持返回None
        """
        extractor = cls._extractors.get(field_type.lower())
        if not extractor:
            logger.warning(f"不支持的字段类型: {field_type}")
        return extractor

    @classmethod
    def extract_field(cls, field_type: str, email_data: Dict[str, Any]) -> str:
        """
        便捷方法：直接提取指定类型的字段

        Args:
            field_type: 字段类型
            email_data: 邮件数据字典

        Returns:
            提取的字段值
        """
        extractor = cls.get_extractor(field_type)
        if extractor:
            return extractor.extract(email_data)
        return ""

    @classmethod
    def get_supported_fields(cls) -> List[str]:
        """
        获取支持的字段类型列表

        Returns:
            支持的字段类型列表
        """
        return list(cls._extractors.keys())
