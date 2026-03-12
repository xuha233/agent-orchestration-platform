"""
创业知识库模块

提供创业模式、反模式和学习存储功能。
"""

from .base import KnowledgeBase, KnowledgeEntry
from .patterns import StartupPattern, StartupPatternLibrary
from .anti_patterns import AntiPattern, AntiPatternLibrary
from .learning_store import LearningStore, LearningEntry

__all__ = [
    "KnowledgeBase",
    "KnowledgeEntry",
    "StartupPattern",
    "StartupPatternLibrary",
    "AntiPattern",
    "AntiPatternLibrary",
    "LearningStore",
    "LearningEntry",
]
