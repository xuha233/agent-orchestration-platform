"""
MVP Breakdown Skill

MVP 分解技能 - AOP 核心技能之一

将 MVP 想法分解为最小可验证单元，
确保开发资源集中在验证核心假设上。
"""

from typing import List, Optional
from pathlib import Path

from .base import SkillBase, SkillMeta, SkillContext, SkillPriority


# 技能提示词（SKILL.md 内容）
SKILL_PROMPT = '''
# MVP 分解

## Overview

MVP 不是"最小可行产品"，而是"最小可验证产品"。

**核心原则：**
- MVP 的目的是验证假设，不是构建完整产品
- 每个功能都应该服务于验证某个假设
- 去除所有不直接贡献于验证的功能

## When to Use

当出现以下情况时，此技能应该被激活：

- 用户确认了假设验证计划后
- 用户说"开始开发"
- 用户说"实现这个功能"
- 需要将想法转化为开发任务时

## The Process

### Step 1: 识别核心功能

对于每个核心假设，问：

1. "验证这个假设最少需要什么功能？"
2. "有没有更简单的方式验证这个假设？"
3. "哪些功能是'有了更好'而非'必须有'？"

### Step 2: 去除非必要功能

使用 MoSCoW 方法分类：

| 类别 | 说明 | MVP 包含？ |
|------|------|-----------|
| Must Have | 必须有，否则无法验证假设 | ✅ |
| Should Have | 重要，但有替代方案 | ❌ |
| Could Have | 有了更好，没有也行 | ❌ |
| Won't Have | 明确不做 | ❌ |

### Step 3: 定义 MVP 边界

**MVP 边界定义：**
```
目标假设: [要验证的假设]
核心功能: [最小功能集]
用户故事: [用户如何使用 MVP 验证假设]
成功标准: [如何判断假设被验证]
时间限制: [最多多久完成]
```

### Step 4: 分解为开发任务

将每个核心功能分解为可执行的开发任务：

1. 任务粒度：1-3 天可完成
2. 每个任务有明确的验收标准
3. 标注任务之间的依赖关系
4. 优先级排序

<HARD-GATE>
在开始开发前，确保所有 MVP 功能都直接服务于假设验证。
任何不直接贡献于验证的功能都应该被移除。
</HARD-GATE>
'''


class MVPBreakdownSkill(SkillBase):
    """
    MVP 分解技能
    
    将 MVP 想法分解为最小可验证单元，
    确保开发资源集中在验证核心假设上。
    """
    
    def get_meta(self) -> SkillMeta:
        return SkillMeta(
            name="mvp-breakdown",
            description="MVP 分解 - 将 MVP 想法分解为最小可验证单元",
            triggers=[
                "开始开发",
                "实现这个",
                "开发功能",
                "分解任务",
                "实现 MVP",
                "开始做",
                "进入开发",
            ],
            priority=SkillPriority.HIGH,
            tags=["mvp", "breakdown", "planning", "development"],
        )
    
    def matches(self, context: SkillContext) -> bool:
        """检查是否匹配当前上下文"""
        meta = self.get_meta()
        
        # 检查任务描述中是否包含触发词
        task_lower = context.task.lower()
        for trigger in meta.triggers:
            if trigger.lower() in task_lower:
                return True
        
        # 检查阶段：如果是任务分解阶段，也应该激活
        if context.phase in ["execution", "planning"]:
            return True
        
        return False
    
    def get_prompt(self) -> str:
        """获取技能的完整提示词"""
        return SKILL_PROMPT
    
    def get_iron_law(self) -> Optional[str]:
        """获取铁律"""
        return "NO MVP FEATURE WITHOUT HYPOTHESIS VALIDATION PURPOSE"
    
    def get_red_flags(self) -> List[str]:
        """获取反模式列表"""
        return [
            "这个功能很酷",
            "用户可能会用到",
            "竞品有这个功能",
            "以后总会用到的",
            "做完整一点",
            "多加几个功能",
            "一步到位",
            "功能丰富一点",
            "用户友好",
            "体验更好",
        ]
    
    def get_checklist(self) -> List[str]:
        """获取检查清单"""
        return [
            "每个功能都有明确的验证目的",
            "区分了必须有和有了更好",
            "移除了所有非必要功能",
            "定义了 MVP 边界",
            "成功/失败标准明确",
            "任务粒度合理（1-3天）",
            "依赖关系已标注",
        ]
