"""Memory Extractor for Primary Agent.

自动从对话中提取重要信息并记录到项目记忆中。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


# 提取规则配置
EXTRACTION_RULES = {
    "decision": {
        "keywords": ["决定", "选择", "采用", "确定", "方案", "使用", "实现方式"],
        "patterns": [
            r"我们(决定|选择|采用|确定).{1,50}",
            r"(方案|实现)是.{1,30}",
            r"使用.{1,20}(来|进行)",
        ],
        "priority": "高",
    },
    "problem": {
        "keywords": ["问题", "错误", "bug", "失败", "异常", "报错", "修复"],
        "patterns": [
            r"(发现|遇到).{1,10}问题",
            r"(错误|异常|bug).{1,30}",
            r"修复.{1,30}",
        ],
        "priority": "中",
    },
    "progress": {
        "keywords": ["完成", "实现", "添加", "更新", "创建", "部署"],
        "patterns": [
            r"(完成|实现|添加|更新|创建)了?.{1,30}",
            r"已(完成|实现|部署)",
        ],
        "priority": "中",
    },
    "learning": {
        "keywords": ["学习", "发现", "注意", "经验", "最佳实践", "教训"],
        "patterns": [
            r"(学到了|发现|注意到).{1,50}",
            r"最佳实践.{1,30}",
            r"(经验|教训)是",
        ],
        "priority": "低",
    },
}

# 忽略的关键词（避免记录无关内容）
IGNORE_KEYWORDS = [
    "hello",
    "你好",
    "谢谢",
    "thanks",
    "好的",
    "ok",
    "是的",
    "是的",
]


def _extract_content(
    prompt: str, response: str, extract_type: str
) -> Optional[Tuple[str, str]]:
    """从对话中提取特定类型的内容。

    Args:
        prompt: 用户输入
        response: Agent 响应
        extract_type: 提取类型 (decision/problem/progress/learning)

    Returns:
        (简短描述, 详细内容) 或 None
    """
    rules = EXTRACTION_RULES.get(extract_type)
    if not rules:
        return None

    # 检查关键词
    combined_text = f"{prompt} {response}"
    has_keyword = any(kw in combined_text for kw in rules["keywords"])

    # 检查模式匹配
    matched_pattern = None
    for pattern in rules["patterns"]:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            matched_pattern = match.group(0)
            break

    if not has_keyword and not matched_pattern:
        return None

    # 提取简短描述
    # 优先使用用户问题的前 50 字符
    short_prompt = prompt.strip()[:50]
    if len(prompt) > 50:
        short_prompt += "..."

    # 提取响应摘要（前 200 字符）
    short_response = response.strip()[:200]
    if len(response) > 200:
        # 尝试在句号处截断
        last_period = short_response.rfind("。")
        if last_period > 50:
            short_response = short_response[: last_period + 1]
        else:
            short_response += "..."

    return (short_prompt, short_response)


def _extract_files(text: str) -> list[str]:
    """从文本中提取相关文件路径。

    Args:
        text: 输入文本

    Returns:
        文件路径列表
    """
    # 匹配常见文件路径模式
    patterns = [
        r"`([^`]+\.[a-z]+)`",  # `file.ext`
        r"([a-zA-Z0-9_\-/]+\.(py|js|ts|md|json|yaml|yml|toml))",  # file.ext
    ]

    files = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            # 过滤太短或太长的匹配
            if 3 < len(match) < 100:
                files.append(match)

    # 去重并限制数量
    return list(dict.fromkeys(files))[:5]


def _should_ignore(prompt: str) -> bool:
    """判断是否应该忽略此对话。

    Args:
        prompt: 用户输入

    Returns:
        是否应该忽略
    """
    prompt_lower = prompt.strip().lower()

    # 忽略太短的输入
    if len(prompt_lower) < 5:
        return True

    # 忽略常见寒暄
    for keyword in IGNORE_KEYWORDS:
        if keyword in prompt_lower and len(prompt_lower) < 20:
            return True

    return False


def _format_memory_entry(
    prompt: str,
    response: str,
    extract_type: str,
    priority: str,
    files: list[str],
) -> str:
    """格式化记忆条目。

    Args:
        prompt: 用户输入
        response: Agent 响应
        extract_type: 类型
        priority: 重要程度
        files: 相关文件

    Returns:
        格式化的 markdown 条目
    """
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M")

    type_names = {
        "decision": "决策",
        "problem": "问题",
        "progress": "进度",
        "learning": "学习",
    }

    entry = f"""
## 自动记忆 - {timestamp}

**用户**: {prompt}
**Agent**: {response}

**类型**: {type_names.get(extract_type, extract_type)}
**重要程度**: {priority}
"""

    if files:
        entry += f"**相关文件**: {', '.join(files)}\n"

    entry += "\n---\n"

    return entry


def extract_and_save_memory(
    prompt: str,
    response: str,
    workspace_path: Path,
) -> bool:
    """从对话中提取重要信息并保存到项目记忆。

    Args:
        prompt: 用户输入
        response: Agent 响应
        workspace_path: 工作空间路径

    Returns:
        是否成功保存
    """
    # 检查是否应该忽略
    if _should_ignore(prompt):
        return False

    # 按优先级尝试提取不同类型的内容
    extracted = None
    extract_type = None

    for type_name in ["decision", "problem", "progress", "learning"]:
        result = _extract_content(prompt, response, type_name)
        if result:
            extracted = result
            extract_type = type_name
            break

    if not extracted:
        return False

    short_prompt, short_response = extracted
    priority = EXTRACTION_RULES[extract_type]["priority"]

    # 提取相关文件
    combined_text = f"{prompt} {response}"
    files = _extract_files(combined_text)

    # 格式化记忆条目
    entry = _format_memory_entry(
        short_prompt, short_response, extract_type, priority, files
    )

    # 追加到 PROJECT_MEMORY.md
    memory_file = workspace_path / ".aop" / "PROJECT_MEMORY.md"

    try:
        # 确保 .aop 目录存在
        memory_file.parent.mkdir(parents=True, exist_ok=True)

        # 如果文件不存在，创建基本结构
        if not memory_file.exists():
            base_content = """# PROJECT_MEMORY.md - 项目记忆

## 项目概况

**名称:** 待定
**描述:** 项目描述

## 关键决策

## 自动记忆

---
"""
            memory_file.write_text(base_content, encoding="utf-8")

        # 读取现有内容
        existing = memory_file.read_text(encoding="utf-8")

        # 找到 "## 自动记忆" 部分，在其后插入新条目
        # 如果没有这个部分，在文件末尾添加
        if "## 自动记忆" in existing:
            # 在 "## 自动记忆" 后插入
            parts = existing.split("## 自动记忆")
            if len(parts) >= 2:
                # 在第一个 --- 之后插入
                sub_parts = parts[1].split("---", 1)
                if len(sub_parts) >= 2:
                    new_content = (
                        parts[0]
                        + "## 自动记忆"
                        + sub_parts[0]
                        + "---"
                        + entry
                        + sub_parts[1]
                    )
                else:
                    # 没有 --- 分隔符，直接追加
                    new_content = existing.rstrip() + "\n" + entry
            else:
                new_content = existing.rstrip() + "\n" + entry
        else:
            # 在文件末尾添加自动记忆部分
            new_content = existing.rstrip() + "\n\n## 自动记忆\n" + entry

        memory_file.write_text(new_content, encoding="utf-8")
        return True

    except Exception as e:
        print(f"[MemoryExtractor] 保存记忆失败: {e}")
        return False


def get_memory_summary(workspace_path: Path, limit: int = 10) -> list[dict]:
    """获取最近的记忆摘要。

    Args:
        workspace_path: 工作空间路径
        limit: 返回的最大条目数

    Returns:
        记忆条目列表
    """
    memory_file = workspace_path / ".aop" / "PROJECT_MEMORY.md"

    if not memory_file.exists():
        return []

    try:
        content = memory_file.read_text(encoding="utf-8")

        # 解析自动记忆条目
        pattern = r"## 自动记忆 - (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\n\n\*\*用户\*\*: ([^\n]+)"
        matches = re.findall(pattern, content)

        memories = []
        for match in matches[-limit:]:
            memories.append(
                {
                    "timestamp": match[0],
                    "prompt": match[1],
                }
            )

        return memories

    except Exception:
        return []
