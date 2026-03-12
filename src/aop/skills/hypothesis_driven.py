"""
Hypothesis Driven Development Skill

假设驱动开发技能 - AOP 核心技能之一

借鉴 Superpowers 的 brainstorming 技能设计，
强制在开发 MVP 前进行假设识别和验证规划。
"""

from typing import List, Optional
from pathlib import Path

from .base import SkillBase, SkillMeta, SkillContext, SkillPriority


# 技能提示词（SKILL.md 内容）
SKILL_PROMPT = '''
# 假设驱动开发

## Overview

MVP 的本质是验证假设，不是构建产品。

**核心原则：**
- 每个 MVP 都是对一系列假设的验证
- 没有明确假设的开发是资源浪费
- 假设应该可测试、可度量、可证伪

## When to Use

当出现以下情况时，此技能应该被激活：

- 用户说"我想做一个..."
- 用户描述产品功能想法
- 用户提出创业/项目想法
- 用户说"有个想法..."
- 用户说"开发一个..."
- 用户说"帮我做一个..."

## The Process

### Step 1: 提取假设

一次问一个问题，避免信息过载：

1. "这个想法最核心的价值主张是什么？"
2. "用户为什么需要这个？你认为他们现在怎么解决这个问题？"
3. "如果这个假设是错的，你怎么知道？"

### Step 2: 假设优先级排序

使用影响-成本矩阵：

| 影响大 + 验证成本低 | 优先验证 |
|---------------------|----------|
| 影响大 + 验证成本高 | 寻找替代验证方法 |
| 影响小 + 验证成本低 | 快速验证 |
| 影响小 + 验证成本高 | 暂缓 |

### Step 3: 设计验证方法

| 假设类型 | 验证方法 | 时间 | 成本 |
|---------|---------|------|------|
| 需求假设 | 落地页测试、用户访谈 | 1-2天 | 低 |
| 解决方案假设 | 原型测试、A/B测试 | 3-5天 | 中 |
| 增长假设 | 病毒系数测试、渠道测试 | 1-2周 | 中 |
| 商业模式假设 | 付费意愿测试、定价测试 | 1周 | 中 |

### Step 4: 获得用户确认

**确认格式：**
```
核心假设：
1. [假设1] - 验证方法: [方法] - 预计时间: [时间]
2. [假设2] - 验证方法: [方法] - 预计时间: [时间]

优先验证: [假设X]
原因: [影响大 + 验证成本低]

是否同意这个验证计划？
```

<HARD-GATE>
在用户确认核心假设和验证方法之前，不得进入开发阶段。
</HARD-GATE>
'''


class HypothesisDrivenSkill(SkillBase):
    """
    假设驱动开发技能
    
    Iron Law: "NO MVP DEVELOPMENT WITHOUT IDENTIFIED HYPOTHESES"
    
    当用户提出 MVP 想法时，强制进行假设识别和验证规划，
    避免在没有明确假设的情况下盲目开发。
    """
    
    def get_meta(self) -> SkillMeta:
        return SkillMeta(
            name="hypothesis-driven",
            description="假设驱动开发 - 在开发 MVP 前强制进行假设识别和验证规划",
            triggers=[
                "我想做一个",
                "有个想法",
                "开发一个",
                "帮我做一个",
                "做一个",
                "我想开发",
                "我想创建",
                "有个项目",
                "创业想法",
                "产品想法",
            ],
            priority=SkillPriority.CRITICAL,  # 最高优先级，强制执行
            tags=["mvp", "hypothesis", "validation", "startup"],
        )
    
    def matches(self, context: SkillContext) -> bool:
        """检查是否匹配当前上下文"""
        meta = self.get_meta()
        
        # 检查任务描述中是否包含触发词
        task_lower = context.task.lower()
        for trigger in meta.triggers:
            if trigger.lower() in task_lower:
                return True
        
        # 检查阶段：如果是需求澄清阶段，也应该激活
        if context.phase in ["clarifying", "hypothesis"]:
            return True
        
        return False
    
    def get_prompt(self) -> str:
        """获取技能的完整提示词"""
        return SKILL_PROMPT
    
    def get_iron_law(self) -> Optional[str]:
        """获取铁律"""
        return "NO MVP DEVELOPMENT WITHOUT IDENTIFIED HYPOTHESES"
    
    def get_red_flags(self) -> List[str]:
        """获取反模式列表"""
        return [
            "先做出来再说",
            "用户会喜欢的",
            "这个功能很重要",
            "竞品都在做",
            "我觉得用户需要",
            "市场很大",
            "技术很成熟",
            "这个想法很好",
            "没有时间验证",
            "验证太花时间",
        ]
    
    def get_checklist(self) -> List[str]:
        """获取检查清单"""
        return [
            "识别了至少 3 个核心假设",
            "对假设进行了优先级排序",
            "为每个假设设计了验证方法",
            "用户确认了验证计划",
            "假设可以测试和度量",
            "定义了成功/失败的标准",
        ]
