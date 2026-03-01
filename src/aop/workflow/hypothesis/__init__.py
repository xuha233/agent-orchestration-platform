"""Hypothesis management."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ...core.types import Hypothesis, HypothesisState


class HypothesisManager:
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        self.hypotheses: Dict[str, Hypothesis] = {}
    
    def create(self, statement: str, validation_method: str = "", priority: str = "quick_win") -> Hypothesis:
        hid = f"H-{hashlib.sha256(f'{statement}{datetime.now()}'.encode()).hexdigest()[:4].upper()}"
        h = Hypothesis(
            hypothesis_id=hid, statement=statement,
            validation_method=validation_method, priority=priority
        )
        self.hypotheses[hid] = h
        return h
    
    def update_state(self, hid: str, state: HypothesisState, confidence: float = 0.0) -> Optional[Hypothesis]:
        if hid not in self.hypotheses:
            return None
        h = self.hypotheses[hid]
        self.hypotheses[hid] = Hypothesis(
            hypothesis_id=h.hypothesis_id, statement=h.statement,
            validation_method=h.validation_method, success_criteria=h.success_criteria,
            state=state, priority=h.priority, findings=h.findings
        )
        return self.hypotheses[hid]
    
    def list_by_state(self, state: Optional[HypothesisState] = None) -> List[Hypothesis]:
        hlist = list(self.hypotheses.values())
        return [h for h in hlist if h.state == state] if state else hlist
