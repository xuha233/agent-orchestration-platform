"""Tests for core/types module."""

import pytest
from aop.core.types import (
    TaskState, HypothesisState, ProjectType,
    Evidence, NormalizedFinding, TaskInput, TaskResult,
    Hypothesis, LearningCapture, ComplexityAssessment, TeamConfig,
    ProviderId
)


class TestEnums:
    """Test enum values."""
    
    def test_task_state_values(self):
        assert TaskState.DRAFT.value == "draft"
        assert TaskState.QUEUED.value == "queued"
        assert TaskState.RUNNING.value == "running"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
    
    def test_hypothesis_state_values(self):
        assert HypothesisState.PENDING.value == "pending"
        assert HypothesisState.VALIDATING.value == "validating"
        assert HypothesisState.VALIDATED.value == "validated"
        assert HypothesisState.FALSIFIED.value == "falsified"
    
    def test_project_type_values(self):
        assert ProjectType.EXPLORATORY.value == "exploratory"
        assert ProjectType.OPTIMIZATION.value == "optimization"
        assert ProjectType.TRANSFORMATION.value == "transformation"
        assert ProjectType.COMPLIANCE_SENSITIVE.value == "compliance_sensitive"


class TestEvidence:
    """Test Evidence dataclass."""
    
    def test_evidence_creation(self):
        e = Evidence(file="test.py", line=42, snippet="def foo():")
        assert e.file == "test.py"
        assert e.line == 42
        assert e.snippet == "def foo():"
    
    def test_evidence_optional_line(self):
        e = Evidence(file="test.py", snippet="code")
        assert e.line is None
    
    def test_evidence_frozen(self):
        e = Evidence(file="test.py")
        with pytest.raises(AttributeError):
            e.file = "other.py"


class TestNormalizedFinding:
    """Test NormalizedFinding dataclass."""
    
    def test_finding_creation(self):
        e = Evidence(file="test.py", line=10)
        f = NormalizedFinding(
            finding_id="F-001",
            severity="high",
            category="bug",
            title="Test finding",
            evidence=e,
            recommendation="Fix it",
            detected_by=["claude"]
        )
        assert f.finding_id == "F-001"
        assert f.severity == "high"
        assert f.category == "bug"
        assert f.detected_by == ["claude"]
    
    def test_finding_default_detected_by(self):
        e = Evidence(file="test.py")
        f = NormalizedFinding(
            finding_id="F-002",
            severity="low",
            category="maintainability",
            title="Style issue",
            evidence=e,
            recommendation="Refactor"
        )
        assert f.detected_by == []


class TestTaskInput:
    """Test TaskInput dataclass."""
    
    def test_task_input_defaults(self):
        t = TaskInput(task_id="T-001", prompt="Review code")
        assert t.task_id == "T-001"
        assert t.prompt == "Review code"
        assert t.repo_root == "."
        assert t.timeout_seconds == 600
    
    def test_task_input_custom(self):
        t = TaskInput(
            task_id="T-002",
            prompt="Analyze",
            repo_root="/path/to/repo",
            timeout_seconds=300
        )
        assert t.repo_root == "/path/to/repo"
        assert t.timeout_seconds == 300


class TestTaskResult:
    """Test TaskResult dataclass."""
    
    def test_task_result_success(self):
        r = TaskResult(
            task_id="T-001",
            provider="claude",
            success=True,
            output="Analysis complete"
        )
        assert r.success is True
        assert r.output == "Analysis complete"
        assert r.error is None
        assert r.findings == []
    
    def test_task_result_failure(self):
        r = TaskResult(
            task_id="T-002",
            provider="codex",
            success=False,
            error="Connection timeout"
        )
        assert r.success is False
        assert r.error == "Connection timeout"


class TestHypothesis:
    """Test Hypothesis dataclass."""
    
    def test_hypothesis_creation(self):
        h = Hypothesis(
            hypothesis_id="H-001",
            statement="Adding cache improves performance",
            validation_method="Benchmark before/after",
            success_criteria=["Response time"],
            state=HypothesisState.PENDING,
            priority="quick_win"
        )
        assert h.hypothesis_id == "H-001"
        assert h.state == HypothesisState.PENDING
        assert h.priority == "quick_win"
    
    def test_hypothesis_defaults(self):
        h = Hypothesis(
            hypothesis_id="H-002",
            statement="Test hypothesis"
        )
        assert h.validation_method == ""
        assert h.success_criteria == []
        assert h.state == HypothesisState.PENDING


class TestLearningCapture:
    """Test LearningCapture dataclass."""
    
    def test_learning_capture_creation(self):
        lc = LearningCapture(
            phase="exploration",
            what_worked=["Daily standups", "Code reviews"],
            what_failed=["Long meetings"],
            insights=["Short cycles work better"]
        )
        assert lc.phase == "exploration"
        assert len(lc.what_worked) == 2
        assert "Long meetings" in lc.what_failed
    
    def test_learning_capture_defaults(self):
        lc = LearningCapture(phase="planning")
        assert lc.what_worked == []
        assert lc.what_failed == []
        assert lc.insights == []


class TestComplexityAssessment:
    """Test ComplexityAssessment dataclass."""
    
    def test_assessment_defaults(self):
        a = ComplexityAssessment()
        assert a.problem_clarity == "medium"
        assert a.data_availability == "medium"
        assert a.tech_novelty == "medium"
        assert a.business_risk == "medium"
    
    def test_to_project_type_exploratory(self):
        a = ComplexityAssessment(
            tech_novelty="high",
            data_availability="low"
        )
        assert a.to_project_type() == ProjectType.EXPLORATORY
    
    def test_to_project_type_compliance(self):
        a = ComplexityAssessment(business_risk="high")
        assert a.to_project_type() == ProjectType.COMPLIANCE_SENSITIVE
    
    def test_to_project_type_optimization(self):
        a = ComplexityAssessment(problem_clarity="high")
        assert a.to_project_type() == ProjectType.OPTIMIZATION
    
    def test_to_project_type_transformation(self):
        a = ComplexityAssessment(
            problem_clarity="medium",
            tech_novelty="medium",
            data_availability="medium",
            business_risk="medium"
        )
        assert a.to_project_type() == ProjectType.TRANSFORMATION


class TestTeamConfig:
    """Test TeamConfig dataclass."""
    
    def test_team_config_creation(self):
        tc = TeamConfig(
            project_type=ProjectType.OPTIMIZATION,
            agents=["po", "dev", "qa"],
            iteration_length="1 week",
            priority="speed"
        )
        assert tc.project_type == ProjectType.OPTIMIZATION
        assert tc.agents == ["po", "dev", "qa"]
    
    def test_from_project_type_exploratory(self):
        tc = TeamConfig.from_project_type(ProjectType.EXPLORATORY)
        assert tc.project_type == ProjectType.EXPLORATORY
        assert "product_owner" in tc.agents
        assert "data" in tc.agents
        assert "ml" in tc.agents
    
    def test_from_project_type_optimization(self):
        tc = TeamConfig.from_project_type(ProjectType.OPTIMIZATION)
        assert "dev" in tc.agents
        assert "devops" in tc.agents
    
    def test_from_project_type_transformation(self):
        tc = TeamConfig.from_project_type(ProjectType.TRANSFORMATION)
        assert "ux" in tc.agents
    
    def test_from_project_type_compliance(self):
        tc = TeamConfig.from_project_type(ProjectType.COMPLIANCE_SENSITIVE)
        assert "ethics" in tc.agents
