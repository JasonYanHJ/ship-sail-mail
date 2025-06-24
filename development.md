# 邮件规则引擎开发文档

## 1. 概述

本文档描述了在现有邮件微服务基础上添加邮件规则引擎的开发实现方案。规则引擎用于在邮件处理流程中根据预定义的条件执行相应的动作，如跳过特定邮件、修改邮件处理标记等。

## 2. 技术架构

### 2.1 系统架构图

```
邮件同步流程
    ↓
规则引擎入口
    ↓
RuleEngine
├── RulesDatabaseService (规则数据库服务)
├── ConditionEvaluator (条件评估器)
├── ActionExecutor (动作执行器)
└── ErrorHandler (错误处理器)
    ↓
邮件处理流程继续
```

### 2.2 核心组件设计

#### 2.2.1 规则引擎主类 (RuleEngine)
```python
class RuleEngine:
    def __init__(self, db_service: EmailDatabaseService):
        self.rules_database = RulesDatabaseService(db_service)
        self.condition_evaluator = ConditionEvaluator()
        self.action_executor = ActionExecutor()
        self.error_handler = ErrorHandler()
        
    async def apply_rules(self, email_data: Dict, rules: List[EmailRule]) -> RuleResult:
        """对邮件应用规则，返回处理结果"""
        pass
```

#### 2.2.2 规则数据库服务 (RulesDatabaseService)
```python
class RulesDatabaseService:
    def __init__(self, db_service: EmailDatabaseService):
        self.db_service = db_service
    
    async def get_all_active_rules(self) -> List[EmailRule]:
        """获取所有激活的规则，按优先级排序"""
        rules = await self.get_all_rules()
        return sorted(
            [rule for rule in rules if rule.is_active],
            key=lambda x: x.priority,
            reverse=True
        )
```

#### 2.2.3 条件评估器 (ConditionEvaluator)
```python
class ConditionEvaluator:
    def __init__(self):
        self.field_extractors = {
            'sender': SenderExtractor(),
            'subject': SubjectExtractor(),
            'body': BodyExtractor(),
            'header': HeaderExtractor(),
            'attachment': AttachmentExtractor(),
        }
        self.operators = {
            'contains': ContainsOperator(),
            'not_contains': NotContainsOperator(),
            'equals': EqualsOperator(),
            'not_equals': NotEqualsOperator(),
            'regex': RegexOperator(),
            'not_regex': NotRegexOperator(),
            'starts_with': StartsWithOperator(),
            'ends_with': EndsWithOperator(),
        }
    
    def evaluate_rule(self, rule: EmailRule, email_data: Dict) -> bool:
        """评估规则是否匹配"""
        group_results = []
        for group in rule.condition_groups:
            group_result = self.evaluate_group(group, email_data)
            group_results.append(group_result)
        
        # 根据全局逻辑合并结果
        if rule.global_group_logic == 'AND':
            return all(group_results)
        else:  # OR
            return any(group_results)
    
    def evaluate_group(self, group: ConditionGroup, email_data: Dict) -> bool:
        """评估条件组是否匹配"""
        condition_results = []
        for condition in group.conditions:
            condition_result = self.evaluate_condition(condition, email_data)
            condition_results.append(condition_result)
        
        # 根据组内逻辑合并结果
        if group.group_logic == 'AND':
            return all(condition_results)
        else:  # OR
            return any(condition_results)
```

## 3. 数据模型设计

### 3.1 Pydantic 数据模型

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class GroupLogic(str, Enum):
    AND = "AND"
    OR = "OR"

class FieldType(str, Enum):
    SENDER = "sender"
    SUBJECT = "subject"
    BODY = "body"
    HEADER = "header"
    ATTACHMENT = "attachment"

class OperatorType(str, Enum):
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    REGEX = "regex"
    NOT_REGEX = "not_regex"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"

class ActionType(str, Enum):
    SKIP = "skip"
    SET_FIELD = "set_field"

class RuleCondition(BaseModel):
    id: Optional[int] = None
    group_id: int
    field_type: FieldType
    operator: OperatorType
    match_value: str
    case_sensitive: bool = False
    condition_order: int = 0

class ConditionGroup(BaseModel):
    id: Optional[int] = None
    rule_id: int
    group_name: Optional[str] = None
    group_logic: GroupLogic = GroupLogic.AND
    group_order: int = 0
    conditions: List[RuleCondition] = []

class RuleAction(BaseModel):
    id: Optional[int] = None
    rule_id: int
    action_type: ActionType
    action_config: Optional[Dict[str, Any]] = None
    action_order: int = 0

class EmailRule(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    global_group_logic: GroupLogic = GroupLogic.AND
    priority: int = 0
    is_active: bool = True
    stop_on_match: bool = False
    condition_groups: List[ConditionGroup] = []
    actions: List[RuleAction] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class RuleResult(BaseModel):
    should_skip: bool = False
    field_modifications: Dict[str, Any] = {}
    matched_rules: List[str] = []
    error_messages: List[str] = []
```

## 4. 数据库操作服务

### 4.1 规则数据库服务 (RulesDatabaseService)

```python
class RulesDatabaseService:
    def __init__(self, db_service: EmailDatabaseService):
        self.db_service = db_service
    
    async def get_all_rules(self) -> List[EmailRule]:
        """获取所有规则及其关联数据"""
        async with self.db_service.get_connection() as conn:
            async with conn.cursor() as cursor:
                # 获取规则基本信息
                await cursor.execute("""
                    SELECT id, name, description, global_group_logic, 
                           priority, is_active, stop_on_match, 
                           created_at, updated_at
                    FROM email_rules
                    ORDER BY priority DESC, id
                """)
                rules_data = await cursor.fetchall()
                
                rules = []
                for rule_data in rules_data:
                    rule = EmailRule(**dict(rule_data))
                    
                    # 获取条件组
                    rule.condition_groups = await self._get_condition_groups(cursor, rule.id)
                    
                    # 获取动作
                    rule.actions = await self._get_rule_actions(cursor, rule.id)
                    
                    rules.append(rule)
                
                return rules
    
    async def _get_condition_groups(self, cursor, rule_id: int) -> List[ConditionGroup]:
        """获取规则的条件组"""
        await cursor.execute("""
            SELECT id, rule_id, group_name, group_logic, group_order
            FROM rule_condition_groups
            WHERE rule_id = %s
            ORDER BY group_order, id
        """, (rule_id,))
        groups_data = await cursor.fetchall()
        
        groups = []
        for group_data in groups_data:
            group = ConditionGroup(**dict(group_data))
            group.conditions = await self._get_group_conditions(cursor, group.id)
            groups.append(group)
        
        return groups
    
    async def _get_group_conditions(self, cursor, group_id: int) -> List[RuleCondition]:
        """获取条件组的条件"""
        await cursor.execute("""
            SELECT id, group_id, field_type, operator, match_value, 
                   case_sensitive, condition_order
            FROM rule_conditions
            WHERE group_id = %s
            ORDER BY condition_order, id
        """, (group_id,))
        conditions_data = await cursor.fetchall()
        
        return [RuleCondition(**dict(condition_data)) for condition_data in conditions_data]
    
    async def _get_rule_actions(self, cursor, rule_id: int) -> List[RuleAction]:
        """获取规则的动作"""
        await cursor.execute("""
            SELECT id, rule_id, action_type, action_config, action_order
            FROM rule_actions
            WHERE rule_id = %s
            ORDER BY action_order, id
        """, (rule_id,))
        actions_data = await cursor.fetchall()
        
        return [RuleAction(**dict(action_data)) for action_data in actions_data]
```

## 5. 字段提取器实现

### 5.1 字段提取器基类

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class FieldExtractor(ABC):
    @abstractmethod
    def extract(self, email_data: Dict[str, Any]) -> str:
        """从邮件数据中提取字段值"""
        pass

class SenderExtractor(FieldExtractor):
    def extract(self, email_data: Dict[str, Any]) -> str:
        return email_data.get('sender', '')

class SubjectExtractor(FieldExtractor):
    def extract(self, email_data: Dict[str, Any]) -> str:
        return email_data.get('subject', '')

class BodyExtractor(FieldExtractor):
    def extract(self, email_data: Dict[str, Any]) -> str:
        # 优先使用文本内容，其次使用HTML内容
        text_content = email_data.get('content_text', '')
        html_content = email_data.get('content_html', '')
        return text_content if text_content else html_content

class HeaderExtractor(FieldExtractor):
    def extract(self, email_data: Dict[str, Any]) -> str:
        return email_data.get('raw_headers', '')

class AttachmentExtractor(FieldExtractor):
    def extract(self, email_data: Dict[str, Any]) -> str:
        # 提取附件文件名列表，用逗号分隔
        attachments = email_data.get('attachments', [])
        filenames = [att.get('original_filename', '') for att in attachments]
        return ','.join(filenames)
```

## 6. 操作符处理器实现

### 6.1 操作符处理器基类

```python
import re
from abc import ABC, abstractmethod

class OperatorHandler(ABC):
    @abstractmethod
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        """执行匹配操作"""
        pass
    
    def _prepare_values(self, field_value: str, match_value: str, case_sensitive: bool):
        """预处理值"""
        if not case_sensitive:
            return field_value.lower(), match_value.lower()
        return field_value, match_value

class ContainsOperator(OperatorHandler):
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        field_val, match_val = self._prepare_values(field_value, match_value, case_sensitive)
        return match_val in field_val

class NotContainsOperator(OperatorHandler):
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        field_val, match_val = self._prepare_values(field_value, match_value, case_sensitive)
        return match_val not in field_val

class EqualsOperator(OperatorHandler):
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        field_val, match_val = self._prepare_values(field_value, match_value, case_sensitive)
        return field_val == match_val

class NotEqualsOperator(OperatorHandler):
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        field_val, match_val = self._prepare_values(field_value, match_value, case_sensitive)
        return field_val != match_val

class RegexOperator(OperatorHandler):
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            return bool(re.search(match_value, field_value, flags))
        except re.error:
            # 正则表达式错误时返回False
            return False

class NotRegexOperator(OperatorHandler):
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            return not bool(re.search(match_value, field_value, flags))
        except re.error:
            # 正则表达式错误时返回True（不匹配）
            return True

class StartsWithOperator(OperatorHandler):
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        field_val, match_val = self._prepare_values(field_value, match_value, case_sensitive)
        return field_val.startswith(match_val)

class EndsWithOperator(OperatorHandler):
    def match(self, field_value: str, match_value: str, case_sensitive: bool = False) -> bool:
        field_val, match_val = self._prepare_values(field_value, match_value, case_sensitive)
        return field_val.endswith(match_val)
```

## 7. 动作执行器实现

### 7.1 动作执行器

```python
from typing import Dict, Any
from abc import ABC, abstractmethod

class ActionHandler(ABC):
    @abstractmethod
    async def execute(self, email_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """执行动作，返回修改结果"""
        pass

class SkipActionHandler(ActionHandler):
    async def execute(self, email_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        return {'should_skip': True}

class SetFieldActionHandler(ActionHandler):
    async def execute(self, email_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        field_modifications = {}
        if config:
            for field_name, field_value in config.items():
                field_modifications[field_name] = field_value
        return {'field_modifications': field_modifications}

class ActionExecutor:
    def __init__(self):
        self.handlers = {
            'skip': SkipActionHandler(),
            'set_field': SetFieldActionHandler(),
        }
    
    async def execute_actions(self, actions: List[RuleAction], email_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行动作列表"""
        result = {
            'should_skip': False,
            'field_modifications': {}
        }
        
        # 按顺序执行动作
        sorted_actions = sorted(actions, key=lambda x: x.action_order)
        for action in sorted_actions:
            handler = self.handlers.get(action.action_type)
            if handler:
                try:
                    action_result = await handler.execute(email_data, action.action_config or {})
                    
                    # 合并结果
                    if action_result.get('should_skip'):
                        result['should_skip'] = True
                    
                    if action_result.get('field_modifications'):
                        result['field_modifications'].update(action_result['field_modifications'])
                        
                except Exception as e:
                    # 动作执行失败时记录错误但不中断流程
                    logger.error(f"Action execution failed: {action.action_type}, error: {str(e)}")
        
        return result
```

## 8. 错误处理策略

### 8.1 错误处理器

```python
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ErrorHandler:
    def __init__(self):
        self.error_messages: List[str] = []
    
    def handle_rule_error(self, rule_name: str, error: Exception) -> bool:
        """处理规则执行错误，返回是否应该继续处理"""
        error_msg = f"Rule '{rule_name}' execution failed: {str(error)}"
        self.error_messages.append(error_msg)
        logger.error(error_msg, exc_info=True)
        
        # 发生错误时跳过规则处理但继续邮件处理
        return True
    
    def handle_condition_error(self, condition_info: str, error: Exception) -> bool:
        """处理条件评估错误，返回条件评估结果（默认为False）"""
        error_msg = f"Condition evaluation failed: {condition_info}, error: {str(error)}"
        self.error_messages.append(error_msg)
        logger.error(error_msg, exc_info=True)
        
        # 条件评估失败时返回False
        return False
    
    def get_errors(self) -> List[str]:
        """获取所有错误信息"""
        return self.error_messages.copy()
    
    def clear_errors(self):
        """清空错误信息"""
        self.error_messages.clear()
```

## 9. 集成到邮件同步流程

### 9.1 修改邮件同步服务

```python
# 在 services/email_sync.py 中添加规则引擎集成

class EmailSyncService:
    def __init__(self, email_reader: EmailReader, 
                 email_database: EmailDatabaseService,
                 file_storage: FileStorageService):
        self.email_reader = email_reader
        self.email_database = email_database
        self.file_storage = file_storage
        # 添加规则引擎
        self.rule_engine = RuleEngine(email_database)
        
    async def sync_emails(self):
        """同步邮件主流程"""
        try:
            # 1. 读取当前激活的规则
            rules = await self.rule_engine.rules_database.get_all_active_rules()
            
            # 2. 获取新邮件
            new_emails = await self.email_reader.get_new_emails()
            
            # 3. 处理每封邮件
            for email_data in new_emails:
                await self._process_single_email(email_data, rules)
                
        except Exception as e:
            logger.error(f"Email sync failed: {str(e)}", exc_info=True)
    
    async def _process_single_email(self, email_data: Dict[str, Any], rules: List[EmailRule]):
        """处理单封邮件"""
        try:
            # 1. 应用规则引擎
            rule_result = await self.rule_engine.apply_rules(email_data, rules)
            
            # 2. 如果规则决定跳过邮件，则直接返回
            if rule_result.should_skip:
                logger.info(f"Email skipped by rules: {email_data.get('message_id')}")
                return
            
            # 3. 应用字段修改
            if rule_result.field_modifications:
                email_data.update(rule_result.field_modifications)
            
            # 4. 继续原有的邮件处理流程
            await self._save_email_to_database(email_data)
            
        except Exception as e:
            logger.error(f"Email processing failed: {str(e)}", exc_info=True)
            # 发生错误时仍然处理邮件，避免丢失
            await self._save_email_to_database(email_data)
```

## 10. 性能优化

### 10.1 数据库查询优化

```python
class RulesDatabaseService:
    async def get_all_active_rules(self) -> List[EmailRule]:
        """获取所有激活的规则，按优先级排序，只查询激活规则减少数据传输"""
        async with self.db_service.get_connection() as conn:
            async with conn.cursor() as cursor:
                # 只查询激活的规则
                await cursor.execute("""
                    SELECT id, name, description, global_group_logic, 
                           priority, is_active, stop_on_match, 
                           created_at, updated_at
                    FROM email_rules
                    WHERE is_active = TRUE
                    ORDER BY priority DESC, id
                """)
                # ... 其余实现
```

### 10.2 短路评估

```python
class ConditionEvaluator:
    def evaluate_group(self, group: ConditionGroup, email_data: Dict) -> bool:
        """评估条件组，支持短路评估"""
        sorted_conditions = sorted(group.conditions, key=lambda x: x.condition_order)
        
        for condition in sorted_conditions:
            try:
                condition_result = self.evaluate_condition(condition, email_data)
                
                # 短路评估
                if group.group_logic == 'AND' and not condition_result:
                    return False
                elif group.group_logic == 'OR' and condition_result:
                    return True
                    
            except Exception as e:
                # 条件评估失败时记录错误
                self.error_handler.handle_condition_error(
                    f"Group {group.id}, Condition {condition.id}", e
                )
                # 条件失败时按False处理
                if group.group_logic == 'AND':
                    return False
        
        # 所有条件都评估完成
        return group.group_logic == 'OR' and len(sorted_conditions) == 0
```

## 11. 配置和部署

### 11.1 环境变量配置

```python
# 在 config/settings.py 中添加规则引擎配置
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 规则引擎配置
    rule_engine_enabled: bool = Field(default=True, description="是否启用规则引擎")
    rule_max_execution_time: int = Field(default=5, description="单个规则最大执行时间（秒）")
```

### 11.2 数据库表创建

```sql
-- 在数据库初始化脚本中添加规则引擎相关表

-- 规则表
CREATE TABLE IF NOT EXISTS email_rules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '规则名称',
    description TEXT COMMENT '规则描述',
    global_group_logic ENUM('AND', 'OR') DEFAULT 'AND' COMMENT '条件组间的全局逻辑',
    priority INT DEFAULT 0 COMMENT '优先级，数字越大优先级越高',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    stop_on_match BOOLEAN DEFAULT FALSE COMMENT '匹配后是否停止执行后续规则',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_priority (priority),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 条件组表
CREATE TABLE IF NOT EXISTS rule_condition_groups (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_id BIGINT NOT NULL,
    group_name VARCHAR(100) COMMENT '条件组语义名称',
    group_logic ENUM('AND', 'OR') DEFAULT 'AND' COMMENT '组内条件逻辑关系',
    group_order INT DEFAULT 0 COMMENT '条件组执行顺序',
    
    FOREIGN KEY (rule_id) REFERENCES email_rules(id) ON DELETE CASCADE,
    INDEX idx_rule_id (rule_id),
    INDEX idx_group_order (group_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 条件表
CREATE TABLE IF NOT EXISTS rule_conditions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    group_id BIGINT NOT NULL,
    field_type ENUM('sender', 'subject', 'body', 'header', 'attachment') NOT NULL COMMENT '检查字段类型',
    operator ENUM('contains', 'not_contains', 'equals', 'not_equals', 'regex', 'not_regex', 'starts_with', 'ends_with') NOT NULL,
    match_value TEXT NOT NULL COMMENT '匹配值',
    case_sensitive BOOLEAN DEFAULT FALSE COMMENT '是否区分大小写',
    condition_order INT DEFAULT 0 COMMENT '条件执行顺序',
    
    FOREIGN KEY (group_id) REFERENCES rule_condition_groups(id) ON DELETE CASCADE,
    INDEX idx_group_id (group_id),
    INDEX idx_condition_order (condition_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 动作表
CREATE TABLE IF NOT EXISTS rule_actions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_id BIGINT NOT NULL,
    action_type ENUM('skip', 'set_field') NOT NULL,
    action_config JSON COMMENT '动作配置参数',
    action_order INT DEFAULT 0 COMMENT '动作执行顺序',
    
    FOREIGN KEY (rule_id) REFERENCES email_rules(id) ON DELETE CASCADE,
    INDEX idx_rule_id (rule_id),
    INDEX idx_action_order (action_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 12. 测试策略

### 12.1 单元测试

```python
import pytest
from unittest.mock import Mock, AsyncMock
from services.rule_engine import RuleEngine, ConditionEvaluator

class TestConditionEvaluator:
    def setup_method(self):
        self.evaluator = ConditionEvaluator()
    
    def test_contains_operator_case_sensitive(self):
        """测试包含操作符（区分大小写）"""
        condition = RuleCondition(
            field_type='sender',
            operator='contains',
            match_value='Admin',
            case_sensitive=True
        )
        
        email_data = {'sender': 'admin@example.com'}
        result = self.evaluator.evaluate_condition(condition, email_data)
        assert result == False
        
        email_data = {'sender': 'Admin@example.com'}
        result = self.evaluator.evaluate_condition(condition, email_data)
        assert result == True
    
    def test_regex_operator_error_handling(self):
        """测试正则表达式错误处理"""
        condition = RuleCondition(
            field_type='subject',
            operator='regex',
            match_value='[unclosed',  # 无效的正则表达式
            case_sensitive=False
        )
        
        email_data = {'subject': 'test subject'}
        result = self.evaluator.evaluate_condition(condition, email_data)
        assert result == False  # 正则错误时应返回False

@pytest.mark.asyncio
class TestRuleEngine:
    async def test_apply_rules_with_skip_action(self):
        """测试跳过邮件的规则"""
        # 构造测试数据和mock对象
        # ...
        
    async def test_rule_cache_refresh(self):
        """测试规则缓存刷新"""
        # ...
```

### 12.2 集成测试

```python
@pytest.mark.asyncio
class TestEmailSyncWithRules:
    async def test_email_sync_with_rule_engine(self):
        """测试邮件同步流程中的规则引擎集成"""
        # 准备测试数据
        # 创建测试规则
        # 模拟邮件数据
        # 验证规则应用结果
        pass
```

## 13. 监控和日志

### 13.1 日志配置

```python
# 在 utils/logger.py 中添加规则引擎相关日志

class RuleEngineLogger:
    def __init__(self, logger_name: str = "rule_engine"):
        self.logger = logging.getLogger(logger_name)
    
    def log_rule_match(self, rule_name: str, email_id: str, actions: List[str]):
        """记录规则匹配日志"""
        self.logger.info(f"Rule matched - Rule: {rule_name}, Email: {email_id}, Actions: {actions}")
    
    def log_rule_execution_time(self, rule_name: str, execution_time: float):
        """记录规则执行时间"""
        if execution_time > 1.0:  # 超过1秒的执行时间值得关注
            self.logger.warning(f"Slow rule execution - Rule: {rule_name}, Time: {execution_time:.2f}s")
    
    def log_rules_loaded(self, rules_count: int):
        """记录规则加载日志"""
        self.logger.info(f"Rules loaded from database - {rules_count} active rules")
```

## 14. 总结

本文档详细描述了邮件规则引擎的技术实现方案，包括：

1. **系统架构**: 模块化设计，职责清晰，无缓存的简化架构
2. **数据模型**: 完整的规则、条件、动作数据结构
3. **核心算法**: 条件评估、短路优化、错误处理
4. **性能优化**: 实时数据库查询、优先级排序、执行时间控制
5. **错误处理**: 宁愿处理不应处理的邮件，也不漏掉应处理的邮件
6. **扩展性**: 预留扩展接口，支持未来功能扩展

该方案采用每次同步时直接从数据库读取规则的策略，避免了缓存管理的复杂性，提供更好的实时性，能够满足每分钟20封邮件、100条规则的性能要求，同时保证系统的稳定性和可维护性。