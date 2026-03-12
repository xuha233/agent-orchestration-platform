"""
知识库基类

提供知识条目的基础数据结构和存储管理。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class KnowledgeEntry:
    """知识条目基类"""
    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEntry":
        """从字典创建"""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )


class KnowledgeBase(ABC):
    """知识库基类"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        初始化知识库
        
        Args:
            storage_path: 存储路径，用于持久化
        """
        self.storage_path = storage_path
        self._entries: Dict[str, KnowledgeEntry] = {}
        
        if storage_path and storage_path.exists():
            self._load()
    
    @abstractmethod
    def search(self, query: str, tags: Optional[List[str]] = None) -> List[KnowledgeEntry]:
        """
        搜索知识条目
        
        Args:
            query: 搜索关键词
            tags: 标签过滤
        
        Returns:
            匹配的知识条目列表
        """
        pass
    
    @abstractmethod
    def suggest(self, context: Dict[str, Any]) -> List[KnowledgeEntry]:
        """
        根据上下文建议知识条目
        
        Args:
            context: 上下文信息
        
        Returns:
            建议的知识条目列表
        """
        pass
    
    def add(self, entry: KnowledgeEntry) -> None:
        """添加知识条目"""
        self._entries[entry.id] = entry
        self._save()
    
    def remove(self, entry_id: str) -> bool:
        """移除知识条目"""
        if entry_id in self._entries:
            del self._entries[entry_id]
            self._save()
            return True
        return False
    
    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """获取知识条目"""
        return self._entries.get(entry_id)
    
    def list_all(self) -> List[KnowledgeEntry]:
        """列出所有知识条目"""
        return list(self._entries.values())
    
    def _load(self) -> None:
        """从存储加载知识条目"""
        if not self.storage_path:
            return
        
        data_file = self.storage_path / "data.json"
        if not data_file.exists():
            return
        
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for entry_data in data.get("entries", []):
                entry = self._create_entry(entry_data)
                if entry:
                    self._entries[entry.id] = entry
        except Exception:
            pass
    
    def _save(self) -> None:
        """保存知识条目到存储"""
        if not self.storage_path:
            return
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        data_file = self.storage_path / "data.json"
        
        data = {
            "entries": [e.to_dict() for e in self._entries.values()],
            "updated_at": datetime.now().isoformat(),
        }
        
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @abstractmethod
    def _create_entry(self, data: Dict[str, Any]) -> Optional[KnowledgeEntry]:
        """创建具体的知识条目"""
        pass
    
    def _text_match(self, text: str, query: str) -> bool:
        """文本匹配（支持模糊匹配）"""
        text_lower = text.lower()
        query_lower = query.lower()
        
        # 支持空格分隔的多关键词
        keywords = query_lower.split()
        return all(kw in text_lower for kw in keywords)
    
    def _tags_match(self, entry_tags: List[str], filter_tags: Optional[List[str]]) -> bool:
        """标签匹配"""
        if not filter_tags:
            return True
        
        entry_tags_lower = [t.lower() for t in entry_tags]
        filter_tags_lower = [t.lower() for t in filter_tags]
        
        return all(ft in entry_tags_lower for ft in filter_tags_lower)
