"""
STATE.md 模板

定义 STATE.md 的 Markdown 格式模板，确保人类可读性。
"""

from datetime import datetime
from typing import List, Dict, Any, Optional


# 主模板
STATE_TEMPLATE = '''# STATE.md

> 最后更新: {timestamp}
> 会话: {session_id}

## 当前状态

- **正在工作**: {current_task}
- **最后行动**: {last_action}
- **下一步**: {next_step}

## 假设追踪

| ID | 假设 | 状态 | 验证方法 | 结果 |
|----|------|------|----------|------|
{hypotheses_table}

## 决策记录

{decisions}

## 阻塞项

{blockers}

## 学习笔记

{learnings}

## 上下文

{context}
'''

# 决策模板
DECISION_TEMPLATE = '''- **[{date}]** {decision}
  - 原因: {reason}'''

# 阻塞项模板
BLOCKER_TEMPLATE = '''- [{status}] {blocker}
  - 添加时间: {added_at}
  - 解决时间: {resolved_at}'''

# 学习笔记模板
LEARNING_TEMPLATE = '''- **[{date}]** {category}
  - 内容: {content}
  - 来源: {source}'''


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """格式化时间戳"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_hypotheses_table(hypotheses: List[Dict[str, Any]]) -> str:
    """格式化假设表格"""
    if not hypotheses:
        return "| - | - | - | - | - |"
    
    rows = []
    for h in hypotheses:
        h_id = h.get("hypothesis_id", h.get("id", "?"))
        statement = h.get("statement", h.get("hypothesis", ""))
        # 截断长语句
        if len(statement) > 50:
            statement = statement[:47] + "..."
        status = h.get("state", h.get("status", "pending"))
        validation = h.get("validation_method", h.get("validation", ""))
        if len(validation) > 30:
            validation = validation[:27] + "..."
        result = h.get("result", "")
        if len(result) > 30:
            result = result[:27] + "..."
        
        rows.append(f"| {h_id} | {statement} | {status} | {validation} | {result} |")
    
    return "\n".join(rows)


def format_decisions(decisions: List[Dict[str, Any]]) -> str:
    """格式化决策记录"""
    if not decisions:
        return "_暂无决策记录_"
    
    lines = []
    for d in decisions:
        date = d.get("date", "未知日期")
        decision = d.get("decision", "")
        reason = d.get("reason", "未说明")
        lines.append(f"- **[{date}]** {decision}")
        lines.append(f"  - 原因: {reason}")
    
    return "\n".join(lines)


def format_blockers(blockers: List[Dict[str, Any]]) -> str:
    """格式化阻塞项"""
    if not blockers:
        return "_暂无阻塞项_"
    
    lines = []
    for b in blockers:
        status = "x" if b.get("resolved", False) else " "
        blocker_text = b.get("blocker", b.get("text", ""))
        added_at = b.get("added_at", "未知时间")
        resolved_at = b.get("resolved_at", "")
        
        lines.append(f"- [{status}] {blocker_text}")
        lines.append(f"  - 添加时间: {added_at}")
        if resolved_at:
            lines.append(f"  - 解决时间: {resolved_at}")
    
    return "\n".join(lines)


def format_learnings(learnings: List[Dict[str, Any]]) -> str:
    """格式化学习笔记"""
    if not learnings:
        return "_暂无学习笔记_"
    
    lines = []
    for l in learnings:
        date = l.get("date", "未知日期")
        category = l.get("category", "通用")
        content = l.get("content", l.get("learning", ""))
        source = l.get("source", "未知来源")
        
        lines.append(f"- **[{date}]** {category}")
        lines.append(f"  - 内容: {content}")
        lines.append(f"  - 来源: {source}")
    
    return "\n".join(lines)
