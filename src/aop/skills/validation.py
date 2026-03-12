"""
Validation Before Launch Skill

发布前验证技能 - AOP 核心技能之一

确保 MVP 发布前具备验证能力，
避免发布后无法判断假设是否被验证。
"""

from typing import List, Optional
from pathlib import Path

from .base import SkillBase, SkillMeta, SkillContext, SkillPriority


# 技能提示词（SKILL.md 内容）
SKILL_PROMPT = '''
# 发布前验证

## Overview

MVP 发布不是终点，而是验证的起点。

**核心原则：**
- 没有验证标准的发布是浪费
- 数据收集机制必须在发布前就绪
- 回滚计划是必要的安全网

## When to Use

当出现以下情况时，此技能应该被激活：

- 用户说"发布 MVP"
- 用户说"上线"
- 用户说"部署"
- 用户说"可以发布了"
- 完成开发准备上线时

## The Process

### Step 1: 检查验证标准

对于每个核心假设，确保有：

1. **可度量的指标**
   - 具体数值（如转化率 > 5%）
   - 收集方式（如埋点、问卷）
   - 时间范围（如观察一周）

2. **成功/失败定义**
   - 什么结果表示假设成立？
   - 什么结果表示假设失败？
   - 不确定区域如何处理？

### Step 2: 检查数据收集机制

| 数据类型 | 收集方式 | 是否就绪？ |
|---------|---------|-----------|
| 用户行为 | 埋点、日志 | [ ] |
| 用户反馈 | 问卷、访谈 | [ ] |
| 业务指标 | 分析工具 | [ ] |
| 错误日志 | 监控系统 | [ ] |

### Step 3: 检查回滚计划

**回滚计划清单：**

1. 数据库迁移是否可逆？
2. 配置变更是否可回退？
3. 是否有旧版本的备份？
4. 回滚步骤是否文档化？
5. 回滚需要多长时间？

### Step 4: 发布前最终确认

**确认清单：**
```
✅ 验证标准已定义
✅ 数据收集已就绪
✅ 回滚计划已准备
✅ 关键路径已测试
✅ 监控告警已配置
✅ 团队已就位（发布窗口内可响应）
```

<HARD-GATE>
在满足以下条件前不得发布：
1. 每个核心假设都有明确的验证标准
2. 数据收集机制已就绪并测试通过
3. 回滚计划已文档化并演练
</HARD-GATE>
'''


class ValidationBeforeLaunchSkill(SkillBase):
    """
    发布前验证技能
    
    Iron Law: "NO MVP LAUNCH WITHOUT VALIDATION CRITERIA"
    
    确保 MVP 发布前具备验证能力，
    避免发布后无法判断假设是否被验证。
    """
    
    def get_meta(self) -> SkillMeta:
        return SkillMeta(
            name="validation-before-launch",
            description="发布前验证 - 确保 MVP 具备验证能力后再发布",
            triggers=[
                "发布",
                "上线",
                "部署",
                "可以发布了",
                "准备发布",
                "要发布了",
                "MVP 完成",
                "可以上线",
            ],
            priority=SkillPriority.CRITICAL,  # 发布前必须检查
            tags=["mvp", "validation", "launch", "deployment"],
        )
    
    def matches(self, context: SkillContext) -> bool:
        """检查是否匹配当前上下文"""
        meta = self.get_meta()
        
        # 检查任务描述中是否包含触发词
        task_lower = context.task.lower()
        for trigger in meta.triggers:
            if trigger.lower() in task_lower:
                return True
        
        # 检查阶段：如果是验证或发布阶段，也应该激活
        if context.phase in ["validation", "launch", "deployment"]:
            return True
        
        return False
    
    def get_prompt(self) -> str:
        """获取技能的完整提示词"""
        return SKILL_PROMPT
    
    def get_iron_law(self) -> Optional[str]:
        """获取铁律"""
        return "NO MVP LAUNCH WITHOUT VALIDATION CRITERIA"
    
    def get_red_flags(self) -> List[str]:
        """获取反模式列表"""
        return [
            "先上线再说",
            "发布后看看数据",
            "数据以后再说",
            "应该没问题",
            "小范围发布不需要",
            "时间紧迫先上",
            "监控以后再加",
            "回滚到时再说",
            "测试够了",
            "功能完整可以发了",
        ]
    
    def get_checklist(self) -> List[str]:
        """获取检查清单"""
        return [
            "每个核心假设都有验证标准",
            "验证指标具体可度量",
            "数据收集机制已就绪",
            "数据收集已测试通过",
            "回滚计划已文档化",
            "回滚步骤已演练",
            "监控告警已配置",
            "关键路径已测试",
        ]
