# -*- coding: utf-8 -*-
"""
AOP 记忆加载器 - 统一加载全局 + 项目记忆
"""

from pathlib import Path
from typing import Optional


# 禁止事项（最高优先级，放在系统提示词最前面）
SHUTDOWN_PROHIBITION = """# ⛔ 禁止关闭会话

以下操作绝对禁止，除非用户明确说"关闭"、"结束"、"退出"或"再见"：

- ❌ Shutdown / 关闭会话 / 结束会话 / 退出会话
- ❌ SendMessage(shutdown_request) / 发送关闭请求
- ❌ 任何导致主会话终止的操作

**主会话只能由用户关闭。即使你认为任务完成了、遇到问题了、或任何其他原因，都不要自主关闭主会话。**

---

"""


def get_global_aop_dir() -> Path:
    """获取 AOP 全局安装目录"""
    return Path(__file__).parent.parent.parent.parent / ".aop"


def load_combined_memory(workspace_path: Optional[Path] = None) -> str:
    """
    统一加载全局 + 项目记忆
    """
    context_parts = []

    # 1. 加载全局记忆
    global_dir = get_global_aop_dir()
    if global_dir.exists():
        global_files = [
            ('SOUL.md', '敏捷教练人设'),
            ('TEAM.md', '团队角色'),
            ('PROJECT_MEMORY.md', '全局项目记忆'),
        ]
        for filename, desc in global_files:
            filepath = global_dir / filename
            if filepath.exists():
                try:
                    content = filepath.read_text(encoding='utf-8').strip()
                    if content:
                        context_parts.append(f"=== {desc} ===\n{content}\n")
                except Exception:
                    pass

    # 2. 加载项目记忆
    if workspace_path:
        project_dir = workspace_path / '.aop'
        if project_dir.exists():
            project_files = [
                ('PROJECT_MEMORY.md', '项目记忆'),
            ]
            for filename, desc in project_files:
                filepath = project_dir / filename
                if filepath.exists():
                    try:
                        content = filepath.read_text(encoding='utf-8').strip()
                        if content:
                            context_parts.append(f"=== {desc} (项目) ===\n{content}\n")
                    except Exception:
                        pass

            # 加载假设和学习记录
            hypotheses_file = project_dir / 'hypotheses.json'
            if hypotheses_file.exists():
                try:
                    import json
                    with open(hypotheses_file, 'r', encoding='utf-8') as f:
                        hypotheses = json.load(f)
                    if hypotheses:
                        context_parts.append(f"=== 假设记录 ===\n{json.dumps(hypotheses, ensure_ascii=False, indent=2)}\n")
                except Exception:
                    pass

            learning_file = project_dir / 'learning.json'
            if learning_file.exists():
                try:
                    import json
                    with open(learning_file, 'r', encoding='utf-8') as f:
                        learning = json.load(f)
                    if learning:
                        context_parts.append(f"=== 学习记录 ===\n{json.dumps(learning, ensure_ascii=False, indent=2)}\n")
                except Exception:
                    pass

    return '\n'.join(context_parts)


def build_agent_system_prompt(workspace_path: Optional[Path] = None, task_hint: str = "") -> str:
    """构建 Agent 系统提示词"""
    parts = []
    
    # 1. 最前面：禁止关闭会话
    parts.append(SHUTDOWN_PROHIBITION)
    
    # 2. 中间：记忆上下文
    memory_context = load_combined_memory(workspace_path)
    if memory_context:
        parts.append(memory_context)

    # 3. 最后：用户任务
    if task_hint:
        parts.append(f"\n---\n\n## 用户任务\n{task_hint}")

    return '\n'.join(parts)
