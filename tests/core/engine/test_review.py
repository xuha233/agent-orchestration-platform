"""Tests for ReviewEngine."""

import pytest
from aop.core.engine.review import ReviewEngine, ReviewResult, _merge_findings_across_providers
from aop.core.types import NormalizedFinding, Evidence


class TestMergeFindings:
    def test_merge_empty_findings(self):
        result = _merge_findings_across_providers([])
        assert result == []
    
    def test_merge_single_finding(self):
        evidence = Evidence(file="test.py", line=10, snippet="code")
        finding = NormalizedFinding(
            task_id="T-001",
            provider="claude",
            finding_id="F-001",
            severity="high",
            category="bug",
            title="Test finding",
            evidence=evidence,
            recommendation="Fix it",
            confidence=0.9,
            fingerprint="abc123",
            raw_ref="ref1"
        )
        result = _merge_findings_across_providers([finding])
        assert len(result) == 1
    
    def test_merge_duplicate_findings(self):
        """Test merging duplicate findings keeps highest severity."""
        evidence = Evidence(file="test.py", line=10, snippet="code")
        
        finding1 = NormalizedFinding(
            task_id="T-001",
            provider="claude",
            finding_id="F-001",
            severity="medium",
            category="bug",
            title="Test finding",
            evidence=evidence,
            recommendation="Fix it",
            confidence=0.8,
            fingerprint="abc123",
            raw_ref="ref1"
        )
        
        finding2 = NormalizedFinding(
            task_id="T-001",
            provider="codex",
            finding_id="F-001",
            severity="critical",
            category="bug",
            title="Test finding",
            evidence=evidence,
            recommendation="Fix it now",
            confidence=0.95,
            fingerprint="abc123",
            raw_ref="ref2"
        )
        
        result = _merge_findings_across_providers([finding1, finding2])
        assert len(result) == 1
        assert result[0]["severity"] == "critical"


class TestReviewEngine:
    def test_engine_creation(self):
        engine = ReviewEngine()
        assert engine is not None
        assert engine.default_timeout == 600
    
    def test_engine_with_custom_timeout(self):
        engine = ReviewEngine(default_timeout=300)
        assert engine.default_timeout == 300
    
    def test_engine_with_custom_providers(self):
        engine = ReviewEngine(providers=["claude"])
        assert engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
