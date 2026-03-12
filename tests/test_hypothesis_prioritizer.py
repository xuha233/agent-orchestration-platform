"""Tests for HypothesisPrioritizer."""

import pytest
from src.aop.hypothesis.prioritizer import (
    HypothesisPrioritizer,
    HypothesisScore,
    PrioritizerConfig,
    ImpactLevel,
    CostLevel,
    UncertaintyLevel,
)


class TestHypothesisPrioritizer:
    """Test cases for HypothesisPrioritizer."""
    
    def test_prioritize_empty_list(self):
        """Test prioritizing empty list returns empty."""
        prioritizer = HypothesisPrioritizer()
        result = prioritizer.prioritize([])
        assert result == []
    
    def test_prioritize_single_hypothesis(self):
        """Test prioritizing single hypothesis."""
        prioritizer = HypothesisPrioritizer()
        hypotheses = [
            {"hypothesis_id": "H-001", "statement": "Test hypothesis", "type": "business"}
        ]
        result = prioritizer.prioritize(hypotheses)
        
        assert len(result) == 1
        assert result[0].hypothesis_id == "H-001"
        assert result[0].rank == 1
    
    def test_prioritize_multiple_hypotheses(self):
        """Test prioritizing multiple hypotheses."""
        prioritizer = HypothesisPrioritizer()
        hypotheses = [
            {"hypothesis_id": "H-001", "statement": "Critical business hypothesis", "type": "business"},
            {"hypothesis_id": "H-002", "statement": "Minor usability improvement", "type": "usability"},
            {"hypothesis_id": "H-003", "statement": "Technical optimization", "type": "technical"},
        ]
        result = prioritizer.prioritize(hypotheses)
        
        assert len(result) == 3
        # Check ranks are set
        ranks = [s.rank for s in result]
        assert sorted(ranks) == [1, 2, 3]
        # First should be business (highest impact)
        assert result[0].hypothesis_id == "H-001"
    
    def test_score_hypothesis_with_explicit_scores(self):
        """Test scoring with explicit scores."""
        prioritizer = HypothesisPrioritizer()
        hypothesis = {
            "hypothesis_id": "H-001",
            "statement": "Test",
            "impact": 8,
            "cost": 3,
            "uncertainty": 5,
        }
        score = prioritizer.score_hypothesis(hypothesis)
        
        assert score.impact_score == 8.0
        assert score.cost_score == 3.0
        assert score.uncertainty_score == 5.0
        # Priority = (8*10 - 3*5 - 5*3) / 10 = (80 - 15 - 15) / 10 = 5.0
        assert score.priority_score == pytest.approx(5.0, rel=0.1)
    
    def test_score_hypothesis_infer_from_type(self):
        """Test scoring infers from hypothesis type."""
        prioritizer = HypothesisPrioritizer()
        
        # Business type should have higher impact
        business_h = {"hypothesis_id": "H-001", "statement": "Test", "type": "business"}
        business_score = prioritizer.score_hypothesis(business_h)
        
        # Usability type should have lower impact
        usability_h = {"hypothesis_id": "H-002", "statement": "Test", "type": "usability"}
        usability_score = prioritizer.score_hypothesis(usability_h)
        
        assert business_score.impact_score > usability_score.impact_score
    
    def test_get_ranking_explanation(self):
        """Test generating ranking explanation."""
        prioritizer = HypothesisPrioritizer()
        hypotheses = [
            {"hypothesis_id": "H-001", "statement": "Test hypothesis", "type": "business"},
        ]
        scores = prioritizer.prioritize(hypotheses)
        explanation = prioritizer.get_ranking_explanation(scores)
        
        assert "# 假设优先级排序结果" in explanation
        assert "H-001" in explanation
        assert "优先级公式" in explanation
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = PrioritizerConfig(
            impact_weight=15.0,
            cost_weight=3.0,
            uncertainty_weight=2.0,
        )
        prioritizer = HypothesisPrioritizer(config=config)
        
        hypothesis = {
            "hypothesis_id": "H-001",
            "statement": "Test",
            "impact": 10,
            "cost": 5,
            "uncertainty": 5,
        }
        score = prioritizer.score_hypothesis(hypothesis)
        
        # Priority = (10*15 - 5*3 - 5*2) / 10 = (150 - 15 - 10) / 10 = 12.5
        # Clamped to 10.0
        assert score.priority_score == pytest.approx(10.0, rel=0.1)
    
    def test_high_uncertainty_boost(self):
        """Test that high uncertainty gets boost."""
        config = PrioritizerConfig(boost_uncertain=True, uncertainty_boost_factor=0.5)
        prioritizer = HypothesisPrioritizer(config=config)
        
        hypothesis = {
            "hypothesis_id": "H-001",
            "statement": "Test",
            "impact": 5,
            "cost": 5,
            "uncertainty": 8,  # High uncertainty
        }
        score = prioritizer.score_hypothesis(hypothesis)
        
        # Base priority = (5*10 - 5*5 - 8*3) / 10 = (50 - 25 - 24) / 10 = 0.1
        # With boost = 0.1 + 8 * 0.5 = 4.1
        assert score.priority_score > 0
    
    def test_string_level_parsing(self):
        """Test parsing string levels."""
        prioritizer = HypothesisPrioritizer()
        
        h1 = {"hypothesis_id": "H-001", "statement": "Test", "impact": "high"}
        s1 = prioritizer.score_hypothesis(h1)
        assert s1.impact_score == ImpactLevel.HIGH.value
        
        h2 = {"hypothesis_id": "H-002", "statement": "Test", "cost": "low"}
        s2 = prioritizer.score_hypothesis(h2)
        assert s2.cost_score == CostLevel.LOW.value
        
        h3 = {"hypothesis_id": "H-003", "statement": "Test", "uncertainty": "high"}
        s3 = prioritizer.score_hypothesis(h3)
        assert s3.uncertainty_score == UncertaintyLevel.HIGH.value
    
    def test_hypothesis_score_to_dict(self):
        """Test HypothesisScore serialization."""
        score = HypothesisScore(
            hypothesis_id="H-001",
            statement="Test",
            impact_score=8.0,
            cost_score=3.0,
            uncertainty_score=5.0,
            priority_score=6.5,
            reasoning="Test reasoning",
            rank=1,
        )
        
        d = score.to_dict()
        
        assert d["hypothesis_id"] == "H-001"
        assert d["impact_score"] == 8.0
        assert d["rank"] == 1
