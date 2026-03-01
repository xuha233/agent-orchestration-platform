"""Tests for workflow/team module."""

import pytest
from aop.core.types import ProjectType, ComplexityAssessment, TeamConfig
from aop.workflow.team import TeamOrchestrator


class TestTeamOrchestrator:
    """Test TeamOrchestrator class."""
    
    def test_orchestrator_creation(self):
        to = TeamOrchestrator()
        assert to.assessment is None
        assert to.team_config is None
    
    def test_assess_project_defaults(self):
        to = TeamOrchestrator()
        assessment = to.assess_project()
        
        assert assessment is not None
        assert to.assessment == assessment
        assert assessment.problem_clarity == "medium"
        assert assessment.data_availability == "medium"
        assert assessment.tech_novelty == "medium"
        assert assessment.business_risk == "medium"
    
    def test_assess_project_custom(self):
        to = TeamOrchestrator()
        assessment = to.assess_project(
            problem_clarity="high",
            data_availability="high",
            tech_novelty="low",
            business_risk="low"
        )
        
        assert assessment.problem_clarity == "high"
        assert assessment.data_availability == "high"
        assert assessment.tech_novelty == "low"
        assert assessment.business_risk == "low"
    
    def test_assess_project_creates_team_config(self):
        to = TeamOrchestrator()
        to.assess_project()
        
        assert to.team_config is not None
    
    def test_get_team_config_before_assessment(self):
        to = TeamOrchestrator()
        config = to.get_team_config()
        assert config is None
    
    def test_get_team_config_after_assessment(self):
        to = TeamOrchestrator()
        to.assess_project()
        config = to.get_team_config()
        
        assert config is not None
        assert isinstance(config, TeamConfig)
    
    def test_project_type_exploratory(self):
        to = TeamOrchestrator()
        to.assess_project(tech_novelty="high", data_availability="low")
        
        assert to.assessment.to_project_type() == ProjectType.EXPLORATORY
        assert to.team_config.project_type == ProjectType.EXPLORATORY
    
    def test_project_type_optimization(self):
        to = TeamOrchestrator()
        to.assess_project(problem_clarity="high")
        
        assert to.assessment.to_project_type() == ProjectType.OPTIMIZATION
        assert to.team_config.project_type == ProjectType.OPTIMIZATION
    
    def test_project_type_compliance_sensitive(self):
        to = TeamOrchestrator()
        to.assess_project(business_risk="high")
        
        assert to.assessment.to_project_type() == ProjectType.COMPLIANCE_SENSITIVE
        assert to.team_config.project_type == ProjectType.COMPLIANCE_SENSITIVE
    
    def test_project_type_transformation(self):
        to = TeamOrchestrator()
        to.assess_project()
        
        assert to.assessment.to_project_type() == ProjectType.TRANSFORMATION
    
    def test_get_strategy_exploratory(self):
        to = TeamOrchestrator()
        to.assess_project(tech_novelty="high", data_availability="low")
        strategy = to.get_strategy()
        
        assert strategy["approach"] == "fast-fail"
        assert strategy["focus"] == "learning"
    
    def test_get_strategy_optimization(self):
        to = TeamOrchestrator()
        to.assess_project(problem_clarity="high")
        strategy = to.get_strategy()
        
        assert strategy["approach"] == "predictable"
        assert strategy["focus"] == "delivery"
    
    def test_get_strategy_transformation(self):
        to = TeamOrchestrator()
        to.assess_project()
        strategy = to.get_strategy()
        
        assert strategy["approach"] == "value_gates"
        assert strategy["focus"] == "balanced"
    
    def test_get_strategy_compliance(self):
        to = TeamOrchestrator()
        to.assess_project(business_risk="high")
        strategy = to.get_strategy()
        
        assert strategy["approach"] == "strict"
        assert strategy["focus"] == "compliance"
    
    def test_get_strategy_before_assessment(self):
        to = TeamOrchestrator()
        strategy = to.get_strategy()
        
        assert strategy == {}
    
    def test_team_agents_match_project_type(self):
        to = TeamOrchestrator()
        
        # Exploratory
        to.assess_project(tech_novelty="high", data_availability="low")
        assert "product_owner" in to.team_config.agents
        assert "data" in to.team_config.agents
        
        # Compliance
        to.assess_project(business_risk="high")
        assert "ethics" in to.team_config.agents
    
    def test_multiple_assessments_overwrite(self):
        to = TeamOrchestrator()
        
        to.assess_project(problem_clarity="high")
        assert to.team_config.project_type == ProjectType.OPTIMIZATION
        
        to.assess_project(business_risk="high")
        assert to.team_config.project_type == ProjectType.COMPLIANCE_SENSITIVE
