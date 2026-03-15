# -*- coding: utf-8 -*-
"""
模型配置 - 统一管理默认模型

支持通过环境变量覆盖默认模型：
- AOP_LLM_MODEL: 默认 LLM 模型
- AOP_EMBEDDING_MODEL: 默认嵌入模型
- AOP_OPENCODE_MODEL: OpenCode 默认模型（格式：provider/model）
"""

import os

# 默认 LLM 模型
DEFAULT_LLM_MODEL = os.environ.get("AOP_LLM_MODEL", "claude-sonnet-4-20250514")

# 默认嵌入模型
DEFAULT_EMBEDDING_MODEL = os.environ.get("AOP_EMBEDDING_MODEL", "text-embedding-ada-002")

# OpenCode 默认模型（可选，格式：provider/model）
# 如果未设置，opencode.json 中不写入 model 字段，由 OpenCode 自行决定
DEFAULT_OPENCODE_MODEL = os.environ.get("AOP_OPENCODE_MODEL", "")

__all__ = [
    "DEFAULT_LLM_MODEL",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_OPENCODE_MODEL",
]
