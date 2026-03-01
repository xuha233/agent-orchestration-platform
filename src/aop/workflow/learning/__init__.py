"""Learning capture."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ...core.types import LearningCapture


class LearningLog:
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        self.learnings: List[LearningCapture] = []
    
    def capture(self, phase: str, what_worked: Optional[List[str]] = None,
                what_failed: Optional[List[str]] = None, insights: Optional[List[str]] = None) -> LearningCapture:
        l = LearningCapture(
            phase=phase,
            what_worked=what_worked or [],
            what_failed=what_failed or [],
            insights=insights or []
        )
        self.learnings.append(l)
        return l
    
    def get_lessons_learned(self) -> Dict[str, List[str]]:
        worked, failed, insights = [], [], []
        for l in self.learnings:
            worked.extend(l.what_worked)
            failed.extend(l.what_failed)
            insights.extend(l.insights)
        return {"what_worked": list(set(worked)), "what_failed": list(set(failed)), "insights": list(set(insights))}
