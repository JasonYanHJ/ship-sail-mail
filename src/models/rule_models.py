from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum


class FieldType(str, Enum):
    """字段类型枚举"""
    SENDER = "sender"
    SUBJECT = "subject"
    BODY = "body"
    HEADER = "header"
    ATTACHMENT = "attachment"


class OperatorType(str, Enum):
    """操作符类型枚举"""
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    REGEX = "regex"
    NOT_REGEX = "not_regex"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class GroupLogic(str, Enum):
    """条件组逻辑类型枚举"""
    AND = "AND"
    OR = "OR"


class ActionType(str, Enum):
    """动作类型枚举"""
    SKIP = "skip"
    SET_FIELD = "set_field"


class RuleCondition(BaseModel):
    """规则条件数据模型"""
    id: Optional[int] = None
    group_id: int
    field_type: FieldType
    operator: OperatorType
    match_value: str
    case_sensitive: bool = False
    condition_order: int = 1
    created_at: Optional[datetime] = None

    def to_db_dict(self) -> Dict[str, Any]:
        """转换为数据库存储格式"""
        data = {
            'group_id': self.group_id,
            'field_type': self.field_type.value,
            'operator': self.operator.value,
            'match_value': self.match_value,
            'case_sensitive': self.case_sensitive,
            'condition_order': self.condition_order
        }
        if self.id:
            data['id'] = self.id
        return data

    @classmethod
    def from_db_dict(cls, data: Dict[str, Any]) -> 'RuleCondition':
        """从数据库记录创建模型"""
        condition_data = data.copy()
        condition_data['field_type'] = FieldType(condition_data['field_type'])
        condition_data['operator'] = OperatorType(condition_data['operator'])
        return cls(**condition_data)


class ConditionGroup(BaseModel):
    """条件组数据模型"""
    id: Optional[int] = None
    rule_id: int
    group_logic: GroupLogic
    group_order: int = 1
    conditions: List[RuleCondition] = []
    created_at: Optional[datetime] = None

    def to_db_dict(self) -> Dict[str, Any]:
        """转换为数据库存储格式"""
        data = {
            'rule_id': self.rule_id,
            'group_logic': self.group_logic.value,
            'group_order': self.group_order
        }
        if self.id:
            data['id'] = self.id
        return data

    @classmethod
    def from_db_dict(cls, data: Dict[str, Any]) -> 'ConditionGroup':
        """从数据库记录创建模型"""
        group_data = data.copy()
        group_data['group_logic'] = GroupLogic(group_data['group_logic'])
        # conditions 会在服务层单独加载
        group_data['conditions'] = []
        return cls(**group_data)


class RuleAction(BaseModel):
    """规则动作数据模型"""
    id: Optional[int] = None
    rule_id: int
    action_type: ActionType
    action_config: Optional[Dict[str, Any]] = None
    action_order: int = 1
    created_at: Optional[datetime] = None

    def to_db_dict(self) -> Dict[str, Any]:
        """转换为数据库存储格式"""
        import json
        data = {
            'rule_id': self.rule_id,
            'action_type': self.action_type.value,
            'action_config': json.dumps(self.action_config, ensure_ascii=False) if self.action_config else None,
            'action_order': self.action_order
        }
        if self.id:
            data['id'] = self.id
        return data

    @classmethod
    def from_db_dict(cls, data: Dict[str, Any]) -> 'RuleAction':
        """从数据库记录创建模型"""
        import json
        action_data = data.copy()
        action_data['action_type'] = ActionType(action_data['action_type'])
        if action_data.get('action_config'):
            action_data['action_config'] = json.loads(
                action_data['action_config'])
        return cls(**action_data)


class EmailRule(BaseModel):
    """邮件规则数据模型"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    is_active: bool = True
    priority: int = 1
    stop_on_match: bool = False
    global_group_logic: GroupLogic = GroupLogic.AND
    condition_groups: List[ConditionGroup] = []
    actions: List[RuleAction] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_db_dict(self) -> Dict[str, Any]:
        """转换为数据库存储格式"""
        data = {
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'priority': self.priority,
            'stop_on_match': self.stop_on_match,
            'global_group_logic': self.global_group_logic.value
        }
        if self.id:
            data['id'] = self.id
        return data

    @classmethod
    def from_db_dict(cls, data: Dict[str, Any]) -> 'EmailRule':
        """从数据库记录创建模型"""
        rule_data = data.copy()
        rule_data['global_group_logic'] = GroupLogic(
            rule_data['global_group_logic'])
        # condition_groups 和 actions 会在服务层单独加载
        rule_data['condition_groups'] = []
        rule_data['actions'] = []
        return cls(**rule_data)


class RuleResult(BaseModel):
    """规则执行结果数据模型"""
    should_skip: bool = False
    field_modifications: Dict[str, Any] = {}
    matched_rules: List[str] = []
    error_messages: List[str] = []
    execution_time: Optional[float] = None

    def add_error(self, error_message: str):
        """添加错误信息"""
        self.error_messages.append(error_message)

    def add_matched_rule(self, rule_name: str):
        """添加匹配的规则名称"""
        if rule_name not in self.matched_rules:
            self.matched_rules.append(rule_name)

    def set_field(self, field_name: str, field_value: Any):
        """设置字段修改"""
        self.field_modifications[field_name] = field_value

    def merge_with(self, other: 'RuleResult'):
        """合并其他规则结果"""
        if other.should_skip:
            self.should_skip = True

        self.field_modifications.update(other.field_modifications)

        for rule_name in other.matched_rules:
            self.add_matched_rule(rule_name)

        self.error_messages.extend(other.error_messages)
