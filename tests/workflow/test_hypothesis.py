"""Tests for workflow/hypothesis module."""

import pytest
from pathlib import Path
from aop.core.types import Hypothesis, HypothesisState
from aop.workflow.hypothesis import HypothesisManager


class TestHypothesisManager:
    """Test HypothesisManager class."""
    
    def test_manager_creation(self):
        hm = HypothesisManager()
        assert hm.hypotheses == {}
        assert hm.storage_path is None
    
    def test_manager_with_storage_path(self, tmp_path):
        storage = tmp_path / "hypotheses.json"
        hm = HypothesisManager(storage_path=storage)
        assert hm.storage_path == storage
    
    def test_create_hypothesis(self):
        hm = HypothesisManager()
        h = hm.create(
            statement="Adding cache improves performance",
            validation_method="Benchmark before/after",
            priority="quick_win"
        )
        
        assert h.statement == "Adding cache improves performance"
        assert h.validation_method == "Benchmark before/after"
        assert h.priority == "quick_win"
        assert h.state == HypothesisState.PENDING
        assert h.hypothesis_id.startswith("H-")
        assert h.hypothesis_id in hm.hypotheses
    
    def test_create_multiple_hypotheses(self):
        hm = HypothesisManager()
        h1 = hm.create("Hypothesis 1")
        h2 = hm.create("Hypothesis 2")
        
        assert h1.hypothesis_id != h2.hypothesis_id
        assert len(hm.hypotheses) == 2
    
    def test_update_state(self):
        hm = HypothesisManager()
        h = hm.create("Test hypothesis")
        
        updated = hm.update_state(h.hypothesis_id, HypothesisState.VALIDATING)
        
        assert updated is not None
        assert updated.state == HypothesisState.VALIDATING
        assert hm.hypotheses[h.hypothesis_id].state == HypothesisState.VALIDATING
    
    def test_update_state_nonexistent(self):
        hm = HypothesisManager()
        result = hm.update_state("H-XXXX", HypothesisState.VALIDATED)
        assert result is None
    
    def test_update_state_to_validated(self):
        hm = HypothesisManager()
        h = hm.create("Test")
        
        hm.update_state(h.hypothesis_id, HypothesisState.VALIDATING)
        hm.update_state(h.hypothesis_id, HypothesisState.VALIDATED)
        
        assert hm.hypotheses[h.hypothesis_id].state == HypothesisState.VALIDATED
    
    def test_update_state_to_falsified(self):
        hm = HypothesisManager()
        h = hm.create("Test")
        
        hm.update_state(h.hypothesis_id, HypothesisState.VALIDATING)
        hm.update_state(h.hypothesis_id, HypothesisState.FALSIFIED)
        
        assert hm.hypotheses[h.hypothesis_id].state == HypothesisState.FALSIFIED
    
    def test_list_by_state_all(self):
        hm = HypothesisManager()
        hm.create("H1")
        hm.create("H2")
        
        all_h = hm.list_by_state()
        assert len(all_h) == 2
    
    def test_list_by_state_filtered(self):
        hm = HypothesisManager()
        h1 = hm.create("H1")
        h2 = hm.create("H2")
        
        hm.update_state(h1.hypothesis_id, HypothesisState.VALIDATING)
        
        pending = hm.list_by_state(HypothesisState.PENDING)
        validating = hm.list_by_state(HypothesisState.VALIDATING)
        
        assert len(pending) == 1
        assert len(validating) == 1
        assert pending[0].hypothesis_id == h2.hypothesis_id
        assert validating[0].hypothesis_id == h1.hypothesis_id
    
    def test_list_by_state_empty(self):
        hm = HypothesisManager()
        hm.create("H1")
        
        validated = hm.list_by_state(HypothesisState.VALIDATED)
        assert validated == []
    
    def test_hypothesis_id_uniqueness(self):
        hm = HypothesisManager()
        ids = set()
        
        for i in range(10):
            h = hm.create(f"Hypothesis {i}")
            ids.add(h.hypothesis_id)
        
        assert len(ids) == 10
    
    def test_create_with_default_priority(self):
        hm = HypothesisManager()
        h = hm.create("Test")
        assert h.priority == "quick_win"
    
    def test_create_with_custom_priority(self):
        hm = HypothesisManager()
        h = hm.create("Test", priority="strategic")
        assert h.priority == "strategic"
