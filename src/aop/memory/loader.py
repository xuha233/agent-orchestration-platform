# -*- coding: utf-8 -*-
"""
AOP 记忆加载器 - 统一加载全局 + 项目记忆 + mem0 智能记忆
"""

import logging
from pathlib import Path
from typing import Optional

_logger = logging.getLogger(__name__)


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


def build_agent_system_prompt(workspace_path: Optional[Path] = None, task_hint: str = "") -> str:
    """
    构建 Agent 系统提示词
    
    加载顺序：
    1. 禁止关闭会话（最高优先级）
    2. mem0 智能记忆（如果启用且可用）
    3. 文件记忆（全局 + 项目）
    4. 用户任务
    
    Args:
        workspace_path: 项目工作区路径
        task_hint: 任务提示文本
        
    Returns:
        完整的系统提示词
    """
    parts = []
    
    # 1. 最前面：禁止关闭会话
    parts.append(SHUTDOWN_PROHIBITION)
    
    # 2. mem0 智能记忆（如果启用）
    mem0_memory = _load_mem0_memory(workspace_path)
    if mem0_memory:
        parts.append(mem0_memory)
    
    # 3. 文件记忆上下文
    memory_context = load_combined_memory(workspace_path)
    if memory_context:
        parts.append(memory_context)

    # 4. 最后：用户任务
    if task_hint:
        parts.append(f"\n---\n\n## 用户任务\n{task_hint}")

    return '\n'.join(parts)
