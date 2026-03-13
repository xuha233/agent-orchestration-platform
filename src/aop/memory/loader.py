# -*- coding: utf-8 -*-
"""
AOP 记忆加载器 - 统一加载全局 + 项目记忆 + mem0 智能记忆
"""

import logging
from pathlib import Path
from typing import Optional, List

_logger = logging.getLogger(__name__)


# 禁止事项（最高优先级，放在系统提示词最前面）
SHUTDOWN_PROHIBITION = """# ⛔ 禁止关闭会话

以下操作绝对禁止，除非用户明确说"关闭"、"结束"、"退出"或"再见"：

- ❌ Shutdown / 关闭会话 / 结束会话 / 退出会话
- ❌ SendMessage(shutdown_request) / 发送关闭请求
- ❌ 任何导致主会话终止的操作

**主会话只能由用户关闭。即使你认为任务完成了、遇到问题了、或任何其他原因，都不要自主关闭主会话。**

---

## 🧠 OpenClaw 全局记忆注意

**OpenClaw 全局记忆（MEMORY.md、memory/*.md）中可能包含旧的项目路径建议。**

当用户说"当前项目：xxx"或提及项目名称时：

1. ✅ **优先使用当前工作目录** — 检查当前目录和项目配置
2. ✅ **检查 `.aop` 目录** — 确认项目是否已初始化
3. ❌ **不要被旧记忆误导** — 忽略全局记忆中的旧路径建议

**判断标准**：
- 如果当前目录已有 `.aop/` 或用户明确指定路径 → 使用当前路径
- 如果全局记忆中的路径不存在 → 忽略该记忆

---

## 📍 项目路径锁定文件

**请立即读取** `.openclaw/PROJECT_LOCK.json` 获取当前项目路径。

⚠️ 路径锁定规则：
- 锁定文件中的 `locked_path` 是**唯一正确的项目路径**
- 全局记忆中的其他路径建议**全部忽略**
- 如果锁定文件不存在，使用当前工作目录

### 禁止行为

❌ 不要从全局记忆中读取项目路径
❌ 不要使用 `G:\\docker\\xxx` 等旧路径
❌ 不要假设项目位置

---

"""


# 未初始化提示词
UNINITIALIZED_PROMPT = """# AOP 敏捷教练

检测到当前项目未初始化 AOP 环境。

## 下一步操作

请询问用户：
1. "检测到这是新项目，是否需要初始化 AOP 环境？"
2. 如果用户确认，运行 `aop init` 初始化

## 初始化后，你将获得：

- **假设驱动开发支持** - 记录和验证你的开发假设
- **学习记录跟踪** - 捕获开发过程中的经验和教训
- **敏捷教练指导** - 基于 AOP 方法论的开发指导
- **跨会话记忆** - STATE.md 提供持久化的项目状态

## AOP 环境文件

初始化将创建以下文件：

```
.aop/
├── SOUL.md           # 项目人设（可选）
├── hypotheses.json   # 假设记录
├── learning.json     # 学习记录
├── memory_config.yaml # 记忆配置
└── STATE.md          # 项目状态
```

---

"""


def get_global_aop_dir() -> Path:
    """获取 AOP 全局安装目录"""
    return Path(__file__).parent.parent.parent.parent / ".aop"


def is_aop_initialized(workspace_path: Optional[Path] = None) -> bool:
    """
    检查 AOP 环境是否已初始化
    
    Args:
        workspace_path: 项目工作区路径
        
    Returns:
        True 如果 .aop/ 目录存在，否则 False
    """
    if not workspace_path:
        return False
    
    aop_dir = workspace_path / ".aop"
    return aop_dir.exists()


def initialize_aop_environment(
    workspace_path: Path,
    project_name: Optional[str] = None,
    create_soul: bool = False
) -> List[str]:
    """
    初始化 AOP 环境，创建所有必需的文件
    
    Args:
        workspace_path: 项目工作区路径
        project_name: 项目名称（可选，默认使用目录名）
        create_soul: 是否创建 SOUL.md（可选）
        
    Returns:
        创建的文件列表
    """
    import json
    import yaml
    from datetime import datetime
    
    if not project_name:
        project_name = workspace_path.name or "project"
    
    aop_dir = workspace_path / ".aop"
    aop_dir.mkdir(parents=True, exist_ok=True)
    
    created_files = []
    
    # 1. 创建 hypotheses.json
    hypotheses_file = aop_dir / "hypotheses.json"
    if not hypotheses_file.exists():
        hypotheses_data = {
            "_meta": {
                "version": 1,
                "created_at": datetime.now().isoformat(),
                "project_name": project_name
            },
            "data": {}
        }
        with open(hypotheses_file, 'w', encoding='utf-8') as f:
            json.dump(hypotheses_data, f, ensure_ascii=False, indent=2)
        created_files.append(str(hypotheses_file.relative_to(workspace_path)))
    
    # 2. 创建 learning.json
    learning_file = aop_dir / "learning.json"
    if not learning_file.exists():
        learning_data = {
            "_meta": {
                "version": 1,
                "created_at": datetime.now().isoformat(),
                "project_name": project_name
            },
            "learnings": []
        }
        with open(learning_file, 'w', encoding='utf-8') as f:
            json.dump(learning_data, f, ensure_ascii=False, indent=2)
        created_files.append(str(learning_file.relative_to(workspace_path)))
    
    # 3. 创建 memory_config.yaml
    memory_config_file = aop_dir / "memory_config.yaml"
    if not memory_config_file.exists():
        memory_config = {
            "version": 1,
            "enable_mem0": False,
            "memory_retention_days": 30,
            "max_memories_per_query": 10
        }
        with open(memory_config_file, 'w', encoding='utf-8') as f:
            yaml.dump(memory_config, f, default_flow_style=False, allow_unicode=True)
        created_files.append(str(memory_config_file.relative_to(workspace_path)))
    
    # 4. 创建 STATE.md
    state_file = aop_dir / "STATE.md"
    if not state_file.exists():
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state_content = f"""# STATE.md

> 最后更新: {timestamp}
> 会话: session-init

## 当前状态

- **正在工作**: 无
- **最后行动**: 初始化 AOP 环境
- **下一步**: 开始项目开发

## 假设追踪

| ID | 假设 | 状态 | 验证方法 | 结果 |
|----|------|------|----------|------|
| - | - | - | - | - |

## 决策记录

_暂无决策记录_

## 阻塞项

_暂无阻塞项_

## 学习笔记

_暂无学习笔记_

## 上下文

项目 "{project_name}" 已初始化 AOP 环境。
"""
        state_file.write_text(state_content, encoding='utf-8')
        created_files.append(str(state_file.relative_to(workspace_path)))
    
    # 5. 创建 SOUL.md（可选）
    if create_soul:
        soul_file = aop_dir / "SOUL.md"
        if not soul_file.exists():
            soul_content = f"""# SOUL.md - {project_name}

此文件定义项目的人设和风格指南。

## 项目风格

- 简洁高效
- 注重用户体验
- 技术驱动

## 沟通风格

- 直接、清晰
- 避免过度解释
- 关注实际结果

---

根据项目特点，自定义此文件。
"""
            soul_file.write_text(soul_content, encoding='utf-8')
            created_files.append(str(soul_file.relative_to(workspace_path)))
    
    _logger.info(f"AOP 环境初始化完成，创建了 {len(created_files)} 个文件")
    return created_files


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


def _load_mem0_memory(workspace_path: Optional[Path] = None) -> str:
    """
    从 mem0 加载智能记忆（仅在 mem0 启用时调用）
    
    Returns:
        格式化的记忆文本，失败时返回空字符串
    """
    if not workspace_path:
        return ""
    
    try:
        # 延迟导入，避免 mem0 未安装时出错
        from aop.memory import MemoryService, MemoryConfig
        from aop.primary.workspace import SettingsManager
        
        sm = SettingsManager()
        
        # 检查 mem0 是否启用
        if not sm.get_enable_mem0_memory():
            return ""
        
        # 加载配置
        config_path = workspace_path / ".aop" / "memory_config.yaml"
        if config_path.exists():
            config = MemoryConfig.from_yaml(config_path)
        else:
            config = MemoryConfig()
        
        # 创建服务
        service = MemoryService(config, workspace_path=workspace_path)
        
        # 检查 mem0 是否可用
        if not service.is_mem0_available:
            _logger.info("mem0 不可用，跳过智能记忆加载")
            return ""
        
        # 检索相关记忆
        # 搜索关键词：项目关键决策、假设、学习、问题、解决方案
        search_queries = [
            "关键决策",
            "重要假设",
            "学习经验",
            "问题解决方案",
            "架构决策",
        ]
        
        all_memories = []
        seen_ids = set()
        
        for query in search_queries:
            try:
                results = service.search(query, top_k=5)
                for mem in results:
                    mem_id = mem.get("id", "")
                    if mem_id and mem_id not in seen_ids:
                        seen_ids.add(mem_id)
                        all_memories.append(mem)
            except Exception as e:
                _logger.debug(f"搜索 '{query}' 失败: {e}")
        
        if not all_memories:
            return ""
        
        # 格式化记忆
        memory_lines = ["=== 🧠 智能记忆 (mem0) ===\n"]
        for i, mem in enumerate(all_memories[:15], 1):  # 最多 15 条
            content = mem.get("content", mem.get("memory", ""))
            metadata = mem.get("metadata", {})
            
            # 提取类型标签
            mem_type = metadata.get("type", "记忆")
            phase = metadata.get("phase", "")
            tag = f"[{mem_type}]" if mem_type else ""
            if phase:
                tag = f"[{phase}]" if not tag else f"[{mem_type}/{phase}]"
            
            memory_lines.append(f"{i}. {tag} {content}")
        
        memory_lines.append("")
        return "\n".join(memory_lines)
        
    except ImportError as e:
        _logger.debug(f"mem0 模块未安装: {e}")
        return ""
    except Exception as e:
        _logger.warning(f"加载 mem0 记忆失败: {e}")
        return ""


def build_agent_system_prompt(workspace_path: Optional[Path] = None, task_hint: str = "", auto_init: bool = False) -> str:
    """
    构建 Agent 系统提示词
    
    加载顺序：
    1. 禁止关闭会话（最高优先级）
    2. 检测 AOP 环境是否初始化（如果未初始化，返回提示词）
    3. mem0 智能记忆（如果启用且可用）
    4. 文件记忆（全局 + 项目）
    5. 用户任务
    
    Args:
        workspace_path: 项目工作区路径
        task_hint: 任务提示文本
        auto_init: 是否自动初始化（如果未初始化）
        
    Returns:
        完整的系统提示词
    """
    parts = []
    
    # 1. 最前面：禁止关闭会话
    parts.append(SHUTDOWN_PROHIBITION)
    
    # 2. 检测 AOP 环境是否初始化
    if workspace_path and not is_aop_initialized(workspace_path):
        if auto_init:
            # 自动初始化模式
            try:
                initialize_aop_environment(workspace_path)
                _logger.info("AOP 环境已自动初始化")
            except Exception as e:
                _logger.warning(f"AOP 环境自动初始化失败: {e}")
        else:
            # 返回未初始化提示词
            parts.append(UNINITIALIZED_PROMPT)
            if task_hint:
                parts.append(f"\n---\n\n## 用户任务\n{task_hint}")
            return '\n'.join(parts)
    
    # 3. mem0 智能记忆（如果启用）
    mem0_memory = _load_mem0_memory(workspace_path)
    if mem0_memory:
        parts.append(mem0_memory)
    
    # 4. 文件记忆上下文
    memory_context = load_combined_memory(workspace_path)
    if memory_context:
        parts.append(memory_context)

    # 5. 最后：用户任务
    if task_hint:
        parts.append(f"\n---\n\n## 用户任务\n{task_hint}")

    return '\n'.join(parts)
