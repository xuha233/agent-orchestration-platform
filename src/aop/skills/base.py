"""
Skill Base - 技能基类

定义技能的标准接口和元信息结构。
借鉴 Superpowers 的 SKILL.md 设计模式。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from enum import Enum


class SkillPriority(Enum):
    """技能优先级"""
    CRITICAL = 100  # 强制执行，如假设驱动开发
    HIGH = 80       # 重要但非强制
    MEDIUM = 50     # 默认优先级
    LOW = 20        # 可选增强


@dataclass
class SkillMeta:
    """
    技能元信息
    
    每个技能必须提供这些基本信息，用于匹配和调度。
    """
    name: str                           # 技能唯一标识，如 "hypothesis-driven"
    description: str                    # 简短描述
    triggers: List[str] = field(default_factory=list)  # 触发条件关键词
    priority: SkillPriority = SkillPriority.MEDIUM     # 优先级
    version: str = "1.0.0"              # 技能版本
    author: str = "AOP"                 # 作者
    tags: List[str] = field(default_factory=list)      # 标签，用于分类


@dataclass
class SkillContext:
    """
    技能执行上下文
    
    包含技能执行时需要的所有信息。
    """
    task: str                           # 当前任务描述
    phase: str = "unknown"              # 当前阶段：clarifying, hypothesis, execution, validation
    user_input: str = ""                # 用户原始输入
    project_path: Optional[Path] = None # 项目路径
    session_id: str = ""                # 会话ID
    additional_data: Dict[str, Any] = field(default_factory=dict)  # 额外数据


class SkillBase(ABC):
    """
    技能基类
    
    所有 AOP 技能必须继承此类并实现抽象方法。
    
    设计原则（借鉴 Superpowers）：
    1. 每个技能有明确的触发条件
    2. 每个技能可以定义 Iron Law（铁律）强制执行某些规则
    3. 每个技能可以定义 Red Flags（反模式）阻止常见错误
    4. 技能的 prompt 使用 Markdown 格式存储，便于人类阅读和编辑
    
    使用示例：
        class HypothesisDrivenSkill(SkillBase):
            def get_meta(self) -> SkillMeta:
                return SkillMeta(
                    name="hypothesis-driven",
                    description="假设驱动开发",
                    triggers=["我想做一个", "有个想法", "开发一个"],
                )
            
            def matches(self, context: SkillContext) -> bool:
                return any(t in context.task for t in self.get_meta().triggers)
            
            def get_prompt(self) -> str:
                return Path("skills/hypothesis_driven/SKILL.md").read_text()
    """
    
    @abstractmethod
    def get_meta(self) -> SkillMeta:
        """
        获取技能元信息
        
        Returns:
            SkillMeta: 技能的元信息
        """
        pass
    
    @abstractmethod
    def matches(self, context: SkillContext) -> bool:
        """
        检查是否匹配当前上下文
        
        Args:
            context: 当前执行上下文
            
        Returns:
            bool: 是否应该激活此技能
        """
        pass
    
    @abstractmethod
    def get_prompt(self) -> str:
        """
        获取技能的完整提示词（SKILL.md 内容）
        
        这个提示词会被注入到 Agent 的上下文中，
        指导 Agent 按照技能定义的流程执行任务。
        
        Returns:
            str: Markdown 格式的技能提示词
        """
        pass
    
    def get_red_flags(self) -> List[str]:
        """
        获取反模式列表
        
        反模式是应该避免的常见错误思维或行为。
        当检测到这些模式时，应该警告用户或阻止操作。
        
        Returns:
            List[str]: 反模式列表，如 ["先做出来再说", "用户会喜欢的"]
        """
        return []
    
    def get_iron_law(self) -> Optional[str]:
        """
        获取铁律
        
        铁律是强制执行的规则，违反铁律的操作应该被阻止。
        
        Returns:
            Optional[str]: 铁律文本，如 "NO MVP DEVELOPMENT WITHOUT IDENTIFIED HYPOTHESES"
        """
        return None
    
    def get_checklist(self) -> List[str]:
        """
        获取检查清单
        
        检查清单用于验证任务是否正确完成。
        
        Returns:
            List[str]: 检查项列表
        """
        return []
    
    def check_red_flags(self, text: str) -> List[str]:
        """
        检查文本中是否包含反模式
        
        Args:
            text: 要检查的文本
            
        Returns:
            List[str]: 匹配到的反模式列表
        """
        matched = []
        for flag in self.get_red_flags():
            if flag.lower() in text.lower():
                matched.append(flag)
        return matched
    
    def __repr__(self) -> str:
        meta = self.get_meta()
        return f"Skill({meta.name}, priority={meta.priority.name})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SkillBase):
            return False
        return self.get_meta().name == other.get_meta().name
    
    def __hash__(self) -> int:
        return hash(self.get_meta().name)
