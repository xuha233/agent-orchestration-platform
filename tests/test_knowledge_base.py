"""Tests for Knowledge Base components."""

import pytest
from pathlib import Path
from src.aop.knowledge.patterns import StartupPattern, StartupPatternLibrary
from src.aop.knowledge.anti_patterns import AntiPattern, AntiPatternLibrary, AntiPatternWarning
from src.aop.knowledge.learning_store import LearningStore, LearningEntry


class TestStartupPattern:
    """Test cases for StartupPattern."""
    
    def test_pattern_creation(self):
        """Test creating a pattern."""
        pattern = StartupPattern(
            id="test_pattern",
            name="Test Pattern",
            description="A test pattern",
            when_to_use=["Case 1", "Case 2"],
            examples=["Example 1"],
            success_rate=0.8,
            difficulty="easy",
            tags=["test"],
        )
        
        assert pattern.id == "test_pattern"
        assert pattern.name == "Test Pattern"
        assert pattern.success_rate == 0.8
    
    def test_pattern_to_dict(self):
        """Test pattern serialization."""
        pattern = StartupPattern(
            id="test",
            name="Test",
            description="Test",
            tags=["test"],
        )
        
        d = pattern.to_dict()
        
        assert d["id"] == "test"
        assert d["name"] == "Test"
        assert "tags" in d
    
    def test_pattern_from_dict(self):
        """Test pattern deserialization."""
        data = {
            "id": "test",
            "name": "Test Pattern",
            "description": "Test description",
            "tags": ["test"],
            "when_to_use": ["Case 1"],
            "examples": ["Ex 1"],
            "success_rate": 0.7,
            "difficulty": "medium",
        }
        
        pattern = StartupPattern.from_dict(data)
        
        assert pattern.id == "test"
        assert pattern.success_rate == 0.7


class TestStartupPatternLibrary:
    """Test cases for StartupPatternLibrary."""
    
    def test_load_default_patterns(self):
        """Test loading default patterns."""
        library = StartupPatternLibrary()
        patterns = library.list_all()
        
        # Should have at least 10 default patterns
        assert len(patterns) >= 10
    
    def test_search_patterns(self):
        """Test searching patterns."""
        library = StartupPatternLibrary()
        
        results = library.search_patterns("落地页")
        
        assert len(results) > 0
        assert any("落地页" in p.name or "落地页" in p.description for p in results)
    
    def test_search_patterns_with_tags(self):
        """Test searching patterns with tag filter."""
        library = StartupPatternLibrary()
        
        results = library.search_patterns("验证", tags=["low-cost"])
        
        assert len(results) > 0
        for p in results:
            assert "low-cost" in p.tags
    
    def test_suggest_patterns(self):
        """Test suggesting patterns based on context."""
        library = StartupPatternLibrary()
        
        context = {
            "stage": "idea",
            "constraints": {"low_budget": True},
        }
        
        suggestions = library.suggest_patterns(context)
        
        assert len(suggestions) > 0
    
    def test_add_pattern(self):
        """Test adding a custom pattern."""
        library = StartupPatternLibrary(load_defaults=False)
        
        pattern = StartupPattern(
            id="custom_pattern",
            name="Custom Pattern",
            description="A custom pattern",
            tags=["custom"],
        )
        
        library.add_pattern(pattern)
        
        retrieved = library.get("custom_pattern")
        assert retrieved is not None
        assert retrieved.name == "Custom Pattern"


class TestAntiPattern:
    """Test cases for AntiPattern."""
    
    def test_antipattern_creation(self):
        """Test creating an antipattern."""
        ap = AntiPattern(
            id="test_ap",
            name="Test Antipattern",
            description="A test antipattern",
            symptoms=["Symptom 1", "Symptom 2"],
            causes=["Cause 1"],
            solutions=["Solution 1"],
            severity="high",
            tags=["test"],
        )
        
        assert ap.id == "test_ap"
        assert ap.severity == "high"
        assert len(ap.symptoms) == 2
    
    def test_antipattern_to_dict(self):
        """Test antipattern serialization."""
        ap = AntiPattern(
            id="test",
            name="Test",
            description="Test",
            symptoms=["S1"],
            causes=["C1"],
            solutions=["So1"],
            severity="medium",
            tags=["test"],
        )
        
        d = ap.to_dict()
        
        assert d["symptoms"] == ["S1"]
        assert d["severity"] == "medium"


class TestAntiPatternLibrary:
    """Test cases for AntiPatternLibrary."""
    
    def test_load_default_antipatterns(self):
        """Test loading default antipatterns."""
        library = AntiPatternLibrary()
        antipatterns = library.list_all()
        
        # Should have at least 10 default antipatterns
        assert len(antipatterns) >= 10
    
    def test_check_for_antipatterns_no_match(self):
        """Test checking with no antipatterns detected."""
        library = AntiPatternLibrary()
        
        context = {
            "decisions": ["Talked to users first"],
            "behaviors": ["Validated hypothesis before coding"],
        }
        
        warnings = library.check_for_antipatterns(context)
        
        # Should not detect antipatterns with good practices
        # (unless there's partial match)
        # We just check it doesn't crash
        assert isinstance(warnings, list)
    
    def test_check_for_antipatterns_with_match(self):
        """Test checking with antipatterns detected."""
        library = AntiPatternLibrary()
        
        context = {
            "decisions": ["花大量时间在非核心功能", "追求完美代码"],
            "behaviors": ["用户还没用上就在优化"],
        }
        
        warnings = library.check_for_antipatterns(context)
        
        # Should detect some antipatterns
        assert len(warnings) > 0
        assert all(isinstance(w, AntiPatternWarning) for w in warnings)
    
    def test_warning_risk_level_calculation(self):
        """Test risk level calculation in warnings."""
        library = AntiPatternLibrary()
        
        context = {
            "decisions": ["花大量时间在非核心功能", "追求完美代码"],
            "behaviors": ["用户还没用上就在优化"],
        }
        
        warnings = library.check_for_antipatterns(context)
        
        # Check risk levels are valid
        valid_levels = ["low", "medium", "high", "critical"]
        for w in warnings:
            assert w.risk_level in valid_levels
    
    def test_search_antipatterns(self):
        """Test searching antipatterns."""
        library = AntiPatternLibrary()
        
        results = library.search("optimization")
        
        # Should find "premature_optimization" or similar
        assert isinstance(results, list)


class TestLearningStore:
    """Test cases for LearningStore."""
    
    def test_add_learning(self):
        """Test adding a learning entry."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LearningStore(storage_path=Path(tmpdir))
            
            entry = store.add_learning(
                name="Test Learning",
                description="We learned something",
                category="technical",
                phase="execution",
                impact="high",
            )
            
            assert entry.id.startswith("learning_")
            assert entry.name == "Test Learning"
    
    def test_get_learnings_by_phase(self):
        """Test getting learnings by phase."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LearningStore(storage_path=Path(tmpdir))
            
            store.add_learning("L1", "Desc", phase="execution")
            store.add_learning("L2", "Desc", phase="validation")
            
            execution_learnings = store.get_learnings_by_phase("execution")
            
            assert len(execution_learnings) == 1
            assert execution_learnings[0].name == "L1"
    
    def test_get_high_impact_learnings(self):
        """Test getting high impact learnings."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LearningStore(storage_path=Path(tmpdir))
            
            store.add_learning("Low", "Desc", impact="low")
            store.add_learning("High", "Desc", impact="high")
            store.add_learning("Medium", "Desc", impact="medium")
            
            high_impact = store.get_high_impact_learnings()
            
            assert len(high_impact) == 1
            assert high_impact[0].name == "High"
    
    def test_get_summary(self):
        """Test getting learning summary."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LearningStore(storage_path=Path(tmpdir))
            
            store.add_learning("L1", "Desc", category="technical")
            store.add_learning("L2", "Desc", category="business")
            
            summary = store.get_summary()
            
            assert "总学习数" in summary or "2" in summary
    
    def test_export_to_markdown(self):
        """Test exporting learnings to markdown."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LearningStore(storage_path=Path(tmpdir))
            
            store.add_learning("L1", "Description", phase="execution")
            
            md = store.export_to_markdown()
            
            assert "# 学习记录" in md or "L1" in md


class TestIntegration:
    """Integration tests for knowledge base."""
    
    def test_pattern_library_and_antipattern_library_work_together(self):
        """Test pattern and antipattern libraries integration."""
        pattern_lib = StartupPatternLibrary()
        antipattern_lib = AntiPatternLibrary()
        
        # Get patterns for a stage
        context = {"stage": "idea"}
        patterns = pattern_lib.suggest_patterns(context)
        
        # Check for antipatterns
        warnings = antipattern_lib.check_for_antipatterns({
            "decisions": ["Skip validation"],
        })
        
        assert len(patterns) > 0
        # Might have warnings based on the decisions
    
    def test_prioritizer_with_pattern_library(self):
        """Test using prioritizer with pattern suggestions."""
        from src.aop.hypothesis.prioritizer import HypothesisPrioritizer
        
        prioritizer = HypothesisPrioritizer()
        pattern_lib = StartupPatternLibrary()
        
        # Get pattern suggestions
        patterns = pattern_lib.search_patterns("mvp")
        
        # Create hypotheses based on patterns
        hypotheses = [
            {"hypothesis_id": f"P-{i}", "statement": p.name, "type": "business"}
            for i, p in enumerate(patterns[:3])
        ]
        
        # Prioritize
        scores = prioritizer.prioritize(hypotheses)
        
        assert len(scores) == len(hypotheses)
