"""
AOP Skills System

借鉴 Superpowers 的技能系统架构，提供可组合、可热加载的技能框架。

技能是 AOP Agent 的能力扩展单元，每个技能定义：
- 触发条件（when to use）
- 执行流程（the process）
- 铁律（iron law）
- 反模式（red flags）
"""

from .base import SkillBase, SkillMeta, SkillContext, SkillPriority
from .manager import SkillManager, SkillMatch

# 核心技能
from .hypothesis_driven import HypothesisDrivenSkill
from .mvp_breakdown import MVPBreakdownSkill
from .validation import ValidationBeforeLaunchSkill

__all__ = [
    # 基础类
    "SkillBase",
    "SkillMeta",
    "SkillContext",
    "SkillPriority",
    # 管理器
    "SkillManager",
    "SkillMatch",
    # 核心技能
    "HypothesisDrivenSkill",
    "MVPBreakdownSkill",
    "ValidationBeforeLaunchSkill",
]

# 内置技能列表
BUILTIN_SKILLS = [
    HypothesisDrivenSkill,
    MVPBreakdownSkill,
    ValidationBeforeLaunchSkill,
]


def create_skill_manager(skills_dir=None):
    """
    创建技能管理器并注册内置技能
    
    Args:
        skills_dir: 可选的额外技能目录
        
    Returns:
        SkillManager: 已注册内置技能的管理器
    """
    from pathlib import Path
    
    manager = SkillManager()
    
    # 注册内置技能
    for skill_class in BUILTIN_SKILLS:
        manager.register_skill(skill_class())
    
    # 如果提供了技能目录，加载额外技能
    if skills_dir:
        manager._load_skills(Path(skills_dir))
    
    return manager
