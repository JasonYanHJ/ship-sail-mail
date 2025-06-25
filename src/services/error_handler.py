import logging
from typing import List, Dict, Any, Optional
import traceback
import time

from ..utils.logger import get_logger

logger = get_logger("error_handler")


class ErrorHandler:
    """统一的错误处理器，负责规则引擎中的错误处理和恢复"""
    
    def __init__(self):
        """初始化错误处理器"""
        self.error_messages: List[str] = []
        self.error_statistics = {
            'total_errors': 0,
            'rule_errors': 0,
            'condition_errors': 0,
            'action_errors': 0,
            'database_errors': 0,
            'system_errors': 0
        }
    
    def handle_rule_error(self, rule_name: str, rule_id: Optional[int], error: Exception) -> bool:
        """
        处理规则执行错误
        
        Args:
            rule_name: 规则名称
            rule_id: 规则ID
            error: 异常对象
            
        Returns:
            是否应该继续处理后续规则（True=继续，False=停止）
        """
        try:
            error_msg = f"规则 '{rule_name}' (ID: {rule_id}) 执行失败: {str(error)}"
            self.error_messages.append(error_msg)
            self.error_statistics['rule_errors'] += 1
            self.error_statistics['total_errors'] += 1
            
            logger.error(error_msg, exc_info=True)
            
            # 记录详细的错误堆栈
            stack_trace = traceback.format_exc()
            logger.debug(f"规则错误堆栈: {stack_trace}")
            
            # 规则执行失败时跳过该规则但继续处理其他规则
            return True
            
        except Exception as e:
            # 错误处理器本身出错时的兜底处理
            logger.critical(f"错误处理器自身异常: {str(e)}")
            return True
    
    def handle_condition_error(self, condition_info: str, error: Exception) -> bool:
        """
        处理条件评估错误
        
        Args:
            condition_info: 条件描述信息
            error: 异常对象
            
        Returns:
            条件评估结果（失败时返回False）
        """
        try:
            error_msg = f"条件评估失败: {condition_info}, 错误: {str(error)}"
            self.error_messages.append(error_msg)
            self.error_statistics['condition_errors'] += 1
            self.error_statistics['total_errors'] += 1
            
            logger.error(error_msg, exc_info=True)
            
            # 条件评估失败时返回False，表示条件不匹配
            return False
            
        except Exception as e:
            logger.critical(f"条件错误处理异常: {str(e)}")
            return False
    
    def handle_action_error(self, action_info: str, error: Exception) -> bool:
        """
        处理动作执行错误
        
        Args:
            action_info: 动作描述信息
            error: 异常对象
            
        Returns:
            是否应该继续执行后续动作（True=继续，False=停止）
        """
        try:
            error_msg = f"动作执行失败: {action_info}, 错误: {str(error)}"
            self.error_messages.append(error_msg)
            self.error_statistics['action_errors'] += 1
            self.error_statistics['total_errors'] += 1
            
            logger.error(error_msg, exc_info=True)
            
            # 动作执行失败时继续执行其他动作
            return True
            
        except Exception as e:
            logger.critical(f"动作错误处理异常: {str(e)}")
            return True
    
    def handle_database_error(self, operation: str, error: Exception) -> bool:
        """
        处理数据库错误
        
        Args:
            operation: 数据库操作描述
            error: 异常对象
            
        Returns:
            是否应该继续处理（True=继续，False=停止）
        """
        try:
            error_msg = f"数据库操作失败: {operation}, 错误: {str(error)}"
            self.error_messages.append(error_msg)
            self.error_statistics['database_errors'] += 1
            self.error_statistics['total_errors'] += 1
            
            logger.error(error_msg, exc_info=True)
            
            # 数据库错误通常是严重问题，但仍然继续处理以避免丢失邮件
            logger.warning("数据库错误，将跳过规则引擎处理")
            return False
            
        except Exception as e:
            logger.critical(f"数据库错误处理异常: {str(e)}")
            return False
    
    def handle_system_error(self, operation: str, error: Exception) -> bool:
        """
        处理系统级错误
        
        Args:
            operation: 系统操作描述
            error: 异常对象
            
        Returns:
            是否应该继续处理（True=继续，False=停止）
        """
        try:
            error_msg = f"系统错误: {operation}, 错误: {str(error)}"
            self.error_messages.append(error_msg)
            self.error_statistics['system_errors'] += 1
            self.error_statistics['total_errors'] += 1
            
            logger.error(error_msg, exc_info=True)
            
            # 系统错误可能影响整体功能，建议停止处理
            return False
            
        except Exception as e:
            logger.critical(f"系统错误处理异常: {str(e)}")
            return False
    
    def add_warning(self, warning_message: str):
        """
        添加警告信息
        
        Args:
            warning_message: 警告消息
        """
        logger.warning(warning_message)
        # 警告信息不计入错误统计，但记录在日志中
    
    def get_errors(self) -> List[str]:
        """
        获取所有错误信息
        
        Returns:
            错误信息列表
        """
        return self.error_messages.copy()
    
    def get_error_statistics(self) -> Dict[str, int]:
        """
        获取错误统计信息
        
        Returns:
            错误统计字典
        """
        return self.error_statistics.copy()
    
    def clear_errors(self):
        """清空错误信息和统计"""
        self.error_messages.clear()
        for key in self.error_statistics:
            self.error_statistics[key] = 0
        
        logger.debug("错误处理器已重置")
    
    def has_critical_errors(self) -> bool:
        """
        检查是否有严重错误
        
        Returns:
            是否存在严重错误
        """
        # 数据库错误和系统错误被认为是严重错误
        return (self.error_statistics['database_errors'] > 0 or 
                self.error_statistics['system_errors'] > 0)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        获取错误摘要
        
        Returns:
            包含错误统计和概要的字典
        """
        total_errors = self.error_statistics['total_errors']
        
        summary = {
            'total_errors': total_errors,
            'has_errors': total_errors > 0,
            'has_critical_errors': self.has_critical_errors(),
            'error_statistics': self.get_error_statistics(),
            'error_count': len(self.error_messages),
            'latest_errors': self.error_messages[-5:] if self.error_messages else []  # 最近5个错误
        }
        
        return summary
    
    def log_error_summary(self):
        """记录错误摘要到日志"""
        summary = self.get_error_summary()
        
        if summary['has_errors']:
            logger.warning(
                f"错误处理摘要: 总错误数={summary['total_errors']}, "
                f"规则错误={self.error_statistics['rule_errors']}, "
                f"条件错误={self.error_statistics['condition_errors']}, "
                f"动作错误={self.error_statistics['action_errors']}, "
                f"数据库错误={self.error_statistics['database_errors']}, "
                f"系统错误={self.error_statistics['system_errors']}"
            )
            
            if summary['has_critical_errors']:
                logger.error("检测到严重错误，建议检查系统状态")
        else:
            logger.debug("无错误发生")


# 全局错误处理器实例
error_handler = ErrorHandler()