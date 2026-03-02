"""Hypothesis management with persistence support."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.types import Hypothesis, HypothesisState
from ..persistence import PersistenceManager, get_persistence_manager


class HypothesisManager:
    """Manages hypotheses with optional persistence.
    
    Attributes:
        storage_path: Optional path for persistence
        hypotheses: Dictionary of hypothesis ID to Hypothesis
        _persistence: Optional persistence manager
    """
    
    def __init__(self, storage_path: Path | None = None):
        """Initialize the hypothesis manager.
        
        Args:
            storage_path: Optional path for JSON file persistence
        """
        self.storage_path = storage_path
        self.hypotheses: Dict[str, Hypothesis] = {}
        self._persistence: PersistenceManager | None = None
        
        if storage_path:
            sp = Path(storage_path) if isinstance(storage_path, str) else storage_path
            self._persistence = PersistenceManager(sp)
            self._load_from_storage()
    
    def _load_from_storage(self) -> None:
        """Load hypotheses from storage if available."""
        if not self._persistence:
            return
        
        data = self._persistence.load("hypotheses")
        if data:
            for hid, h_data in data.items():
                if hid.startswith("_"):
                    continue
                self.hypotheses[hid] = Hypothesis(
                    hypothesis_id=h_data.get("hypothesis_id", hid),
                    statement=h_data.get("statement", ""),
                    validation_method=h_data.get("validation_method", ""),
                    success_criteria=h_data.get("success_criteria", []),
                    state=HypothesisState(h_data.get("state", "pending")),
                    priority=h_data.get("priority", "quick_win"),
                    findings=h_data.get("findings", []),
                )
    
    def create(self, statement: str, validation_method: str = "", priority: str = "quick_win") -> Hypothesis:
        """Create a new hypothesis.
        
        Args:
            statement: The hypothesis statement
            validation_method: How to validate this hypothesis
            priority: Priority level (quick_win or deep_dive)
            
        Returns:
            The created Hypothesis object
        """
        hid = f"H-{hashlib.sha256(f'{statement}{datetime.now()}'.encode()).hexdigest()[:8].upper()}"
        h = Hypothesis(
            hypothesis_id=hid, 
            statement=statement,
            validation_method=validation_method, 
            priority=priority
        )
        self.hypotheses[hid] = h
        return h
    
    def update_state(self, hid: str, state: HypothesisState, confidence: float = 0.0) -> Hypothesis | None:
        """Update the state of a hypothesis.
        
        Args:
            hid: Hypothesis ID
            state: New state
            confidence: Confidence level (0.0-1.0)
            
        Returns:
            Updated Hypothesis or None if not found
        """
        if hid not in self.hypotheses:
            return None
        h = self.hypotheses[hid]
        self.hypotheses[hid] = Hypothesis(
            hypothesis_id=h.hypothesis_id, 
            statement=h.statement,
            validation_method=h.validation_method, 
            success_criteria=h.success_criteria,
            state=state, 
            priority=h.priority, 
            findings=h.findings
        )
        return self.hypotheses[hid]
    
    def list_by_state(self, state: HypothesisState | None = None) -> List[Hypothesis]:
        """List hypotheses, optionally filtered by state.
        
        Args:
            state: Optional state filter
            
        Returns:
            List of matching hypotheses
        """
        hlist = list(self.hypotheses.values())
        return [h for h in hlist if h.state == state] if state else hlist
    
    def save(self) -> Path | None:
        """Save hypotheses to persistent storage.
        
        Returns:
            Path to saved file, or None if no persistence configured
        """
        if not self._persistence:
            return None
        
        data = {}
        for hid, h in self.hypotheses.items():
            data[hid] = {
                "hypothesis_id": h.hypothesis_id,
                "statement": h.statement,
                "validation_method": h.validation_method,
                "success_criteria": h.success_criteria,
                "state": h.state.value if isinstance(h.state, HypothesisState) else h.state,
                "priority": h.priority,
                "findings": [],  # findings might be complex objects
            }
        
        return self._persistence.save("hypotheses", data)
    
    def load(self) -> bool:
        """Load hypotheses from persistent storage.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self._persistence:
            return False
        
        self.hypotheses = {}  # Clear existing before loading
        self._load_from_storage()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Export hypotheses as a dictionary.
        
        Returns:
            Dictionary of hypothesis data
        """
        result = {}
        for hid, h in self.hypotheses.items():
            result[hid] = {
                "hypothesis_id": h.hypothesis_id,
                "statement": h.statement,
                "validation_method": h.validation_method,
                "success_criteria": h.success_criteria,
                "state": h.state.value if isinstance(h.state, HypothesisState) else h.state,
                "priority": h.priority,
            }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], storage_path: Path | None = None) -> "HypothesisManager":
        """Create a HypothesisManager from a dictionary.
        
        Args:
            data: Dictionary of hypothesis data
            storage_path: Optional storage path
            
        Returns:
            New HypothesisManager instance
        """
        manager = cls(storage_path=storage_path)
        for hid, h_data in data.items():
            if hid.startswith("_"):
                continue
            manager.hypotheses[hid] = Hypothesis(
                hypothesis_id=h_data.get("hypothesis_id", hid),
                statement=h_data.get("statement", ""),
                validation_method=h_data.get("validation_method", ""),
                success_criteria=h_data.get("success_criteria", []),
                state=HypothesisState(h_data.get("state", "pending")),
                priority=h_data.get("priority", "quick_win"),
            )
        return manager
