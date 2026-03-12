"""
STATE.md 跨会话记忆系统

借鉴 GSD 的 STATE.md 模式，提供跨会话的记忆持久化。
"""

from .manager import StateManager
from .templates import STATE_TEMPLATE, DECISION_TEMPLATE, BLOCKER_TEMPLATE, LEARNING_TEMPLATE

__all__ = [
    "StateManager",
    "STATE_TEMPLATE",
    "DECISION_TEMPLATE",
    "BLOCKER_TEMPLATE",
    "LEARNING_TEMPLATE",
]
