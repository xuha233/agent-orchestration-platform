"""
跨项目知识库
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from uuid import uuid4


@dataclass
class SharedLearning:
    """共享学习经验"""
    learning_id: str
    pattern: str
    context: dict
    solution: str
    success_rate: float = 0.0
    projects: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.learning_id:
            self.learning_id = f"learn_{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SharedLearning":
        return cls(**data)
    
    def matches_context(self, context: dict) -> float:
        if not context or not self.context:
            return 0.0
        matches = sum(1 for k, v in context.items() if k in self.context and self.context[k] == v)
        return matches / len(context) if context else 0.0


class KnowledgeBase:
    """跨项目知识库"""
    
    def __init__(self, storage_path: str = "~/.aop/knowledge"):
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.storage_path / "learnings.json"
        self.learnings: Dict[str, SharedLearning] = {}
        self._load()
    
    def add_learning(self, learning: SharedLearning) -> None:
        self.learnings[learning.learning_id] = learning
        self._save()
    
    def create_learning(self, pattern: str, context: dict, solution: str, tags: List[str] | None = None, project: str | None = None) -> SharedLearning:
        learning = SharedLearning(pattern=pattern, context=context, solution=solution, tags=tags or [], projects=[project] if project else [])
        self.add_learning(learning)
        return learning
    
    def get_learning(self, learning_id: str) -> Optional[SharedLearning]:
        return self.learnings.get(learning_id)
    
    def find_similar(self, context: dict, limit: int = 5) -> List[SharedLearning]:
        scored = [(l.matches_context(context) * 0.7 + l.success_rate * 0.3, l) for l in self.learnings.values()]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [l for _, l in scored[:limit] if _ > 0]
    
    def get_patterns_for(self, task_type: str) -> List[SharedLearning]:
        return sorted([l for l in self.learnings.values() if task_type in l.tags], key=lambda l: l.success_rate, reverse=True)
    
    def get_by_project(self, project: str) -> List[SharedLearning]:
        return [l for l in self.learnings.values() if project in l.projects]
    
    def get_by_tag(self, tag: str) -> List[SharedLearning]:
        return [l for l in self.learnings.values() if tag in l.tags]
    
    def update_success_rate(self, learning_id: str, success: bool) -> None:
        if learning_id in self.learnings:
            self.learnings[learning_id].success_rate = self.learnings[learning_id].success_rate * 0.9 + (1.0 if success else 0.0) * 0.1
            self._save()
    
    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "learnings": [l.to_dict() for l in self.learnings.values()]}, f, ensure_ascii=False, indent=2)
    
    def import_from(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for item in data.get("learnings", []):
            learning = SharedLearning.from_dict(item)
            if learning.learning_id not in self.learnings:
                self.learnings[learning.learning_id] = learning
                count += 1
        self._save()
        return count
    
    def get_statistics(self) -> dict:
        total = len(self.learnings)
        return {"total": total, "avg_success_rate": sum(l.success_rate for l in self.learnings.values()) / total if total > 0 else 0}
    
    def _load(self) -> None:
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.get("learnings", []):
                    learning = SharedLearning.from_dict(item)
                    self.learnings[learning.learning_id] = learning
            except Exception:
                pass
    
    def _save(self) -> None:
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "learnings": [l.to_dict() for l in self.learnings.values()]}, f, ensure_ascii=False, indent=2)
