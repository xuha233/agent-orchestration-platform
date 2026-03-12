"""Tests for ValidationPathPlanner."""

import pytest
from src.aop.validation.path_planner import (
    ValidationPathPlanner,
    ValidationStep,
    ValidationPath,
    PlannerConfig,
    ValidationMethod,
    CostLevel,
)


class TestValidationPathPlanner:
    """Test cases for ValidationPathPlanner."""
    
    def test_plan_empty_hypotheses(self):
        """Test planning with empty hypotheses."""
        planner = ValidationPathPlanner()
        path = planner.plan([])
        
        assert path.steps == []
        assert path.total_days == 0
        assert path.total_cost == "low"
    
    def test_plan_single_hypothesis(self):
        """Test planning with single hypothesis."""
        planner = ValidationPathPlanner()
        hypotheses = [
            {"hypothesis_id": "H-001", "statement": "Users will pay", "type": "business"}
        ]
        path = planner.plan(hypotheses)
        
        assert len(path.steps) == 1
        assert path.steps[0].hypothesis_id == "H-001"
        assert path.total_days > 0
    
    def test_plan_multiple_hypotheses(self):
        """Test planning with multiple hypotheses."""
        planner = ValidationPathPlanner()
        hypotheses = [
            {"hypothesis_id": "H-001", "statement": "Demand validation", "type": "demand"},
            {"hypothesis_id": "H-002", "statement": "Solution validation", "type": "solution"},
            {"hypothesis_id": "H-003", "statement": "Pricing validation", "type": "pricing"},
        ]
        path = planner.plan(hypotheses)
        
        assert len(path.steps) == 3
    
    def test_suggest_validation_method_demand(self):
        """Test suggesting validation method for demand hypothesis."""
        planner = ValidationPathPlanner()
        
        hypothesis = {"type": "demand"}
        method = planner.suggest_validation_method(hypothesis)
        
        assert method in ["landing_page", "fake_door", "waitlist"]
    
    def test_suggest_validation_method_solution(self):
        """Test suggesting validation method for solution hypothesis."""
        planner = ValidationPathPlanner()
        
        hypothesis = {"type": "solution"}
        method = planner.suggest_validation_method(hypothesis)
        
        assert method in ["prototype", "concierge", "wizard_of_oz"]
    
    def test_identify_parallel_opportunities(self):
        """Test identifying parallel execution opportunities."""
        planner = ValidationPathPlanner()
        steps = [
            ValidationStep(
                step_id="step_1",
                hypothesis_id="H-001",
                method="landing_page",
                description="Test 1",
                estimated_days=2,
                estimated_cost="low",
                dependencies=[],
                success_criteria="Pass",
            ),
            ValidationStep(
                step_id="step_2",
                hypothesis_id="H-002",
                method="survey",
                description="Test 2",
                estimated_days=1,
                estimated_cost="low",
                dependencies=[],
                success_criteria="Pass",
            ),
        ]
        
        groups = planner.identify_parallel_opportunities(steps)
        
        # Both steps have no dependencies, should be in same group
        assert len(groups) >= 1
        assert "step_1" in groups[0] or "step_2" in groups[0]
    
    def test_calculate_critical_path(self):
        """Test calculating critical path."""
        planner = ValidationPathPlanner()
        steps = [
            ValidationStep(
                step_id="step_1",
                hypothesis_id="H-001",
                method="landing_page",
                description="Test 1",
                estimated_days=2,
                estimated_cost="low",
                dependencies=[],
                success_criteria="Pass",
            ),
            ValidationStep(
                step_id="step_2",
                hypothesis_id="H-002",
                method="prototype",
                description="Test 2",
                estimated_days=5,
                estimated_cost="medium",
                dependencies=["step_1"],
                success_criteria="Pass",
            ),
        ]
        
        critical_path = planner.calculate_critical_path(steps)
        
        # step_2 is on critical path (depends on step_1)
        assert "step_2" in critical_path
    
    def test_custom_config_max_parallel(self):
        """Test custom config for max parallel steps."""
        config = PlannerConfig(max_parallel_steps=5)
        planner = ValidationPathPlanner(config=config)
        
        hypotheses = [
            {"hypothesis_id": f"H-00{i}", "statement": f"Test {i}", "type": "demand"}
            for i in range(1, 6)
        ]
        path = planner.plan(hypotheses)
        
        # All hypotheses should be planned
        assert len(path.steps) == 5
    
    def test_validation_path_summary(self):
        """Test ValidationPath summary generation."""
        path = ValidationPath(
            steps=[
                ValidationStep(
                    step_id="step_1",
                    hypothesis_id="H-001",
                    method="landing_page",
                    description="Test demand",
                    estimated_days=2,
                    estimated_cost="low",
                    dependencies=[],
                    success_criteria="Pass",
                ),
            ],
            total_days=2,
            total_cost="low",
            parallel_opportunities=[["step_1"]],
            critical_path=["step_1"],
        )
        
        summary = path.get_summary()
        
        assert "# 验证路径规划" in summary
        assert "2 天" in summary
        assert "Test demand" in summary
    
    def test_validation_step_to_dict(self):
        """Test ValidationStep serialization."""
        step = ValidationStep(
            step_id="step_1",
            hypothesis_id="H-001",
            method="landing_page",
            description="Test",
            estimated_days=2,
            estimated_cost="low",
            dependencies=[],
            success_criteria="Pass",
        )
        
        d = step.to_dict()
        
        assert d["step_id"] == "step_1"
        assert d["method"] == "landing_page"
        assert d["estimated_days"] == 2
    
    def test_validation_path_to_dict(self):
        """Test ValidationPath serialization."""
        path = ValidationPath(
            steps=[],
            total_days=0,
            total_cost="low",
            parallel_opportunities=[],
            critical_path=[],
        )
        
        d = path.to_dict()
        
        assert d["total_days"] == 0
        assert d["total_cost"] == "low"
    
    def test_dependencies_handling(self):
        """Test handling of step dependencies."""
        planner = ValidationPathPlanner()
        hypotheses = [
            {"hypothesis_id": "H-001", "statement": "First", "type": "demand"},
            {"hypothesis_id": "H-002", "statement": "Second", "type": "solution", "dependencies": ["H-001"]},
        ]
        path = planner.plan(hypotheses)
        
        # Check that hypothesis ID dependencies are converted to step ID dependencies
        step_2 = next(s for s in path.steps if s.hypothesis_id == "H-002")
        assert len(step_2.dependencies) > 0
        assert step_2.dependencies[0].startswith("step_")
