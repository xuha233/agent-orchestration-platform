# -*- coding: utf-8 -*-
"""
模型配置 - 统一管理默认模型

支持通过环境变量覆盖默认模型：
- AOP_LLM_MODEL: 默认 LLM 模型
- AOP_EMBEDDING_MODEL: 默认嵌入模型
"""

import os

# 默认 LLM 模型
DEFAULT_LLM_MODEL = os.environ.get("AOP_LLM_MODEL", "claude-sonnet-4-20250514")

# 默认嵌入模型
DEFAULT_EMBEDDING_MODEL = os.environ.get("AOP_EMBEDDING_MODEL", "text-embedding-ada-002")


__all__ = [
    "DEFAULT_LLM_MODEL",
    "DEFAULT_EMBEDDING_MODEL",
]
