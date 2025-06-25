from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import re

from ..utils.logger import get_logger

logger = get_logger("operator_handlers")


class OperatorHandler(ABC):
    """操作符处理器抽象基类"""
    
    @abstractmethod
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """
        执行匹配操作
        
        Args:
            field_value: 字段值
            match_value: 匹配值
            case_sensitive: 是否大小写敏感
            
        Returns:
            匹配结果
        """
        pass
    
    def _prepare_values(self, field_value: str, match_value: str, case_sensitive: bool = False) -> tuple[str, str]:
        """
        预处理值，处理大小写
        
        Args:
            field_value: 字段值
            match_value: 匹配值
            case_sensitive: 是否大小写敏感
            
        Returns:
            处理后的(字段值, 匹配值)元组
        """
        # 确保输入是字符串
        field_str = str(field_value) if field_value is not None else ""
        match_str = str(match_value) if match_value is not None else ""
        
        # 如果不区分大小写，转换为小写
        if not case_sensitive:
            field_str = field_str.lower()
            match_str = match_str.lower()
        
        return field_str, match_str


class ContainsOperator(OperatorHandler):
    """包含操作符"""
    
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """检查字段值是否包含匹配值"""
        try:
            field_str, match_str = self._prepare_values(field_value, match_value, case_sensitive)
            result = match_str in field_str
            logger.debug(f"包含匹配: '{field_str}' contains '{match_str}' = {result}")
            return result
        except Exception as e:
            logger.error(f"包含操作失败: {e}")
            return False


class NotContainsOperator(OperatorHandler):
    """不包含操作符"""
    
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """检查字段值是否不包含匹配值"""
        try:
            field_str, match_str = self._prepare_values(field_value, match_value, case_sensitive)
            result = match_str not in field_str
            logger.debug(f"不包含匹配: '{field_str}' not contains '{match_str}' = {result}")
            return result
        except Exception as e:
            logger.error(f"不包含操作失败: {e}")
            return False


class EqualsOperator(OperatorHandler):
    """完全匹配操作符"""
    
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """检查字段值是否完全等于匹配值"""
        try:
            field_str, match_str = self._prepare_values(field_value, match_value, case_sensitive)
            result = field_str == match_str
            logger.debug(f"完全匹配: '{field_str}' equals '{match_str}' = {result}")
            return result
        except Exception as e:
            logger.error(f"完全匹配操作失败: {e}")
            return False


class NotEqualsOperator(OperatorHandler):
    """不等于操作符"""
    
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """检查字段值是否不等于匹配值"""
        try:
            field_str, match_str = self._prepare_values(field_value, match_value, case_sensitive)
            result = field_str != match_str
            logger.debug(f"不等于匹配: '{field_str}' not equals '{match_str}' = {result}")
            return result
        except Exception as e:
            logger.error(f"不等于操作失败: {e}")
            return False


class StartsWithOperator(OperatorHandler):
    """开始于操作符"""
    
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """检查字段值是否以匹配值开头"""
        try:
            field_str, match_str = self._prepare_values(field_value, match_value, case_sensitive)
            result = field_str.startswith(match_str)
            logger.debug(f"开始于匹配: '{field_str}' starts with '{match_str}' = {result}")
            return result
        except Exception as e:
            logger.error(f"开始于操作失败: {e}")
            return False


class EndsWithOperator(OperatorHandler):
    """结束于操作符"""
    
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """检查字段值是否以匹配值结尾"""
        try:
            field_str, match_str = self._prepare_values(field_value, match_value, case_sensitive)
            result = field_str.endswith(match_str)
            logger.debug(f"结束于匹配: '{field_str}' ends with '{match_str}' = {result}")
            return result
        except Exception as e:
            logger.error(f"结束于操作失败: {e}")
            return False


class RegexOperator(OperatorHandler):
    """正则表达式操作符"""
    
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """使用正则表达式匹配字段值"""
        try:
            field_str = str(field_value) if field_value is not None else ""
            pattern = str(match_value) if match_value is not None else ""
            
            if not pattern:
                logger.warning("正则表达式模式为空")
                return False
            
            # 设置正则表达式标志
            flags = 0 if case_sensitive else re.IGNORECASE
            
            # 编译正则表达式并匹配
            compiled_pattern = re.compile(pattern, flags)
            result = bool(compiled_pattern.search(field_str))
            
            logger.debug(f"正则匹配: '{field_str}' matches pattern '{pattern}' = {result}")
            return result
            
        except re.error as e:
            logger.error(f"正则表达式错误: {e}, pattern: '{match_value}'")
            return False
        except Exception as e:
            logger.error(f"正则匹配操作失败: {e}")
            return False


class NotRegexOperator(OperatorHandler):
    """正则表达式不匹配操作符"""
    
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """使用正则表达式检查字段值不匹配"""
        try:
            field_str = str(field_value) if field_value is not None else ""
            pattern = str(match_value) if match_value is not None else ""
            
            if not pattern:
                logger.warning("正则表达式模式为空")
                return True  # 空模式认为不匹配
            
            # 设置正则表达式标志
            flags = 0 if case_sensitive else re.IGNORECASE
            
            # 编译正则表达式并匹配
            compiled_pattern = re.compile(pattern, flags)
            result = not bool(compiled_pattern.search(field_str))
            
            logger.debug(f"正则不匹配: '{field_str}' not matches pattern '{pattern}' = {result}")
            return result
            
        except re.error as e:
            logger.error(f"正则表达式错误: {e}, pattern: '{match_value}'")
            return True  # 正则错误时认为不匹配
        except Exception as e:
            logger.error(f"正则不匹配操作失败: {e}")
            return True


class OperatorHandlerFactory:
    """操作符处理器工厂类"""
    
    _handlers = {
        'contains': ContainsOperator(),
        'not_contains': NotContainsOperator(),
        'equals': EqualsOperator(),
        'not_equals': NotEqualsOperator(),
        'starts_with': StartsWithOperator(),
        'ends_with': EndsWithOperator(),
        'regex': RegexOperator(),
        'not_regex': NotRegexOperator(),
    }
    
    @classmethod
    def get_handler(cls, operator_type: str) -> Optional[OperatorHandler]:
        """
        根据操作符类型获取对应的处理器
        
        Args:
            operator_type: 操作符类型
            
        Returns:
            操作符处理器实例，如果类型不支持返回None
        """
        handler = cls._handlers.get(operator_type.lower())
        if not handler:
            logger.warning(f"不支持的操作符类型: {operator_type}")
        return handler
    
    @classmethod
    def execute_operation(cls, operator_type: str, field_value: str, 
                         match_value: str, case_sensitive: bool = False) -> bool:
        """
        便捷方法：直接执行操作符匹配
        
        Args:
            operator_type: 操作符类型
            field_value: 字段值
            match_value: 匹配值
            case_sensitive: 是否大小写敏感
            
        Returns:
            匹配结果
        """
        handler = cls.get_handler(operator_type)
        if handler:
            return handler.match(field_value, match_value, case_sensitive)
        return False
    
    @classmethod
    def get_supported_operators(cls) -> list[str]:
        """
        获取支持的操作符类型列表
        
        Returns:
            支持的操作符类型列表
        """
        return list(cls._handlers.keys())
    
    @classmethod
    def validate_regex_pattern(cls, pattern: str) -> tuple[bool, Optional[str]]:
        """
        验证正则表达式模式是否有效
        
        Args:
            pattern: 正则表达式模式
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            re.compile(pattern)
            return True, None
        except re.error as e:
            return False, str(e)