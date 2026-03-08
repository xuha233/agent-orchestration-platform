# -*- coding: utf-8 -*-
"""
AOP 记忆加载器 - 统一加载全局 + 项目记忆
"""

from pathlib import Path
from typing import Optional


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
        # 只加载核心文件，不加载 TEAM.md 和 WORKFLOW.md（避免干扰 Claude Code Team 功能）
        global_files = [
            ('SOUL.md', '敏捷教练人设'),
            ('PROJECT_MEMORY.md', '全局项目记忆'),
        ]
        for filename, desc in global_files:
            filepath = global_dir / filename
            if filepath.exists():
                try:
                    content = filepath.read_text(encoding='utf-8').strip()
                    if content:
                        context_parts.append(f"=== {desc} (全局) ===\n{content}\n")
                except Exception:
                    pass

    # 2. 加载项目记忆
    if workspace_path:
        project_dir = workspace_path / '.aop'
        if project_dir.exists():
            # 项目级也只加载核心文件
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
                        context_parts.append(f"=== 假设记录 (项目) ===\n{json.dumps(hypotheses, ensure_ascii=False, indent=2)}\n")
                except Exception:
                    pass

            learning_file = project_dir / 'learning.json'
            if learning_file.exists():
                try:
                    import json
                    with open(learning_file, 'r', encoding='utf-8') as f:
                        learning = json.load(f)
                    with open(learning_file, 'r', encoding='utf-8') as f:
                        learning = json.load(f)
                    if learning:
                        context_parts.append(f"=== 学习记录 (项目) ===\n{json.dumps(learning, ensure_ascii=False, indent=2)}\n")
                except Exception:
                    pass

    return '\n'.join(context_parts)


def build_agent_system_prompt(workspace_path: Optional[Path] = None, task_hint: str = "") -> str:
    """构建 Agent 系统提示词（轻量版，不干扰 Claude Code Team 功能）"""
    memory_context = load_combined_memory(workspace_path)
    parts = []

    if memory_context:
        parts.append("# AOP 敏捷教练上下文\n")
        parts.append(memory_context)
        parts.append("\n---\n")

    # 极简版工作指引
    parts.append("""# 工作方式

**探索 → 构建 → 验证 → 学习**

1. 探索 - 理解问题，搜索代码库
2. 构建 - 实现解决方案
3. 验证 - 运行测试，检查结果
4. 学习 - 总结经验，更新记忆

## 团队协作

当用户说 `use team` 或 `创建团队` 时，使用 Claude Code 内置的 Team 功能：
- TeamCreate(team_name="...", members=[...])
- Task(agent="...", prompt="... 立即开始执行 ...")
- TaskOutput(task_id="...")

**重要**：不要预设团队，让用户自然触发。

---

记住：保持轻量，帮助用户高效完成开发任务。""")

    if task_hint:
        parts.append(f"\n\n## 用户任务\n{task_hint}")

    return '\n'.join(parts)
