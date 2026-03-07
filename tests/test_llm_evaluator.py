# -*- coding: utf-8 -*-
"""Tests for LLM-as-Judge Evaluator"""

import pytest
from unittest.mock import MagicMock, patch

from src.aop.agent.llm_evaluator import (
    LLMEvaluator,
    EvaluationScore,
    EvaluationResult,
    EvaluationVerdict,
    CodeArtifact,
    HumanAICollaboration,
)


class TestEvaluationScore:
    """Tests for EvaluationScore"""
    
    def test_default_scores(self):
        """Test default score values"""
        score = EvaluationScore()
        assert score.functional_correctness == 0.0
        assert score.code_quality == 0.0
        assert score.architecture == 0.0
        assert score.security == 0.0
        assert score.maintainability == 0.0
    
    def test_overall_calculation(self):
        """Test overall score calculation"""
        score = EvaluationScore(
            functional_correctness=8.0,
            code_quality=7.0,
            architecture=9.0,
            security=8.0,
            maintainability=7.0,
        )
        assert score.overall == pytest.approx(7.8, rel=0.01)
    
    def test_overall_all_zeros(self):
        """Test overall with all zeros"""
        score = EvaluationScore()
        assert score.overall == 0.0


class TestEvaluationResult:
    """Tests for EvaluationResult"""
    
    def test_result_creation(self):
        """Test creating evaluation result"""
        result = EvaluationResult(
            scores=EvaluationScore(functional_correctness=8.0),
            overall_score=7.5,
            strengths=["Good code"],
            weaknesses=["Needs docs"],
            recommendations=["Add comments"],
            verdict=EvaluationVerdict.ACCEPT,
            verdict_reason="Good quality",
        )
        assert result.overall_score == 7.5
        assert result.verdict == EvaluationVerdict.ACCEPT
    
    def test_is_acceptable(self):
        """Test is_acceptable method"""
        result = EvaluationResult(
            scores=EvaluationScore(),
            overall_score=8.0,
            strengths=[],
            weaknesses=[],
            recommendations=[],
            verdict=EvaluationVerdict.ACCEPT,
            verdict_reason="",
        )
        assert result.is_acceptable(7.0) is True
        assert result.is_acceptable(9.0) is False


class TestCodeArtifact:
    """Tests for CodeArtifact"""
    
    def test_artifact_creation(self):
        """Test creating code artifact"""
        artifact = CodeArtifact(
            file_path="test.py",
            content="print('hello')",
            language="python",
            description="Test file",
        )
        assert artifact.file_path == "test.py"
        assert artifact.content == "print('hello')"
    
    def test_defaults(self):
        """Test default values"""
        artifact = CodeArtifact(
            file_path="test.py",
            content="print('hello')",
        )
        assert artifact.language == "python"
        assert artifact.description == ""


class TestLLMEvaluator:
    """Tests for LLMEvaluator"""
    
    def test_evaluator_creation(self):
        """Test creating evaluator"""
        evaluator = LLMEvaluator()
        assert evaluator.llm is None
        assert evaluator.model == "claude-sonnet-4-20250514"
    
    def test_heuristic_evaluation_simple(self):
        """Test heuristic evaluation with simple code"""
        evaluator = LLMEvaluator()
        result = evaluator.evaluate(
            code="def hello():\n    print('hello')",
            objective="Implement hello world",
        )
        
        assert isinstance(result, EvaluationResult)
        assert result.overall_score >= 0
        assert result.verdict in [
            EvaluationVerdict.ACCEPT,
            EvaluationVerdict.NEEDS_REVISION,
            EvaluationVerdict.REJECT,
        ]
    
    def test_heuristic_evaluation_with_todo(self):
        """Test heuristic evaluation detects TODO"""
        evaluator = LLMEvaluator()
        result = evaluator.evaluate(
            code="# TODO: implement this\npass",
            objective="Implement feature",
        )
        
        assert any("TODO" in w for w in result.weaknesses)
    
    def test_heuristic_evaluation_with_security_issue(self):
        """Test heuristic evaluation detects security issues"""
        evaluator = LLMEvaluator()
        result = evaluator.evaluate(
            code="result = eval(user_input)",
            objective="Execute user code",
        )
        
        assert result.scores.security < 7.0
        assert any("eval" in w for w in result.weaknesses)
    
    def test_evaluate_with_artifact(self):
        """Test evaluation with CodeArtifact"""
        evaluator = LLMEvaluator()
        artifact = CodeArtifact(
            file_path="main.py",
            content="def main():\n    pass",
        )
        result = evaluator.evaluate(
            code=artifact,
            objective="Main function",
        )
        
        assert isinstance(result, EvaluationResult)
    
    def test_evaluate_with_multiple_artifacts(self):
        """Test evaluation with multiple artifacts"""
        evaluator = LLMEvaluator()
        artifacts = [
            CodeArtifact(file_path="a.py", content="def a(): pass"),
            CodeArtifact(file_path="b.py", content="def b(): pass"),
        ]
        result = evaluator.evaluate(
            code=artifacts,
            objective="Multiple files",
        )
        
        assert isinstance(result, EvaluationResult)
    
    def test_evaluate_with_success_criteria(self):
        """Test evaluation with success criteria"""
        evaluator = LLMEvaluator()
        result = evaluator.evaluate(
            code="def add(a, b): return a + b",
            objective="Add two numbers",
            success_criteria=["Function returns sum"],
        )
        
        assert isinstance(result, EvaluationResult)
    
    def test_evaluate_batch(self):
        """Test batch evaluation"""
        evaluator = LLMEvaluator()
        items = [
            {"code": "def a(): pass", "objective": "Function a"},
            {"code": "def b(): pass", "objective": "Function b"},
        ]
        results = evaluator.evaluate_batch(items)
        
        assert len(results) == 2
        assert all(isinstance(r, EvaluationResult) for r in results)
    
    def test_normalize_string_input(self):
        """Test normalizing string input"""
        evaluator = LLMEvaluator()
        artifacts = evaluator._normalize_code_input("print('hello')")
        
        assert len(artifacts) == 1
        assert artifacts[0].content == "print('hello')"
    
    def test_parse_evaluation_response(self):
        """Test parsing LLM response"""
        evaluator = LLMEvaluator()
        
        response = '''
        ```json
        {
          "scores": {
            "functional_correctness": 8,
            "code_quality": 7,
            "architecture": 8,
            "security": 9,
            "maintainability": 7
          },
          "overall_score": 7.8,
          "strengths": ["Good structure"],
          "weaknesses": ["Needs docs"],
          "recommendations": ["Add comments"],
          "verdict": "accept",
          "verdict_reason": "Good quality"
        }
        ```
        '''
        
        result = evaluator._parse_evaluation_response(response)
        
        assert result.overall_score == 7.8
        assert result.verdict == EvaluationVerdict.ACCEPT
        assert "Good structure" in result.strengths
    
    def test_extract_json_from_text(self):
        """Test extracting JSON from text"""
        evaluator = LLMEvaluator()
        
        text = 'Some text {"scores": {"functional_correctness": 8}} more text'
        json_str = evaluator._extract_json(text)
        
        assert json_str is not None
        assert "scores" in json_str


class TestHumanAICollaboration:
    """Tests for HumanAICollaboration"""
    
    def test_should_request_human_review_low_score(self):
        """Test requesting review for low score"""
        collab = HumanAICollaboration()
        
        result = EvaluationResult(
            scores=EvaluationScore(),
            overall_score=6.5,  # In gray zone
            strengths=[],
            weaknesses=[],
            recommendations=[],
            verdict=EvaluationVerdict.NEEDS_REVISION,
            verdict_reason="",
        )
        
        assert collab.should_request_human_review(result) is True
    
    def test_should_request_human_review_security(self):
        """Test requesting review for security issues"""
        collab = HumanAICollaboration()
        
        result = EvaluationResult(
            scores=EvaluationScore(security=5.0),
            overall_score=7.0,
            strengths=[],
            weaknesses=[],
            recommendations=[],
            verdict=EvaluationVerdict.ACCEPT,
            verdict_reason="",
        )
        
        assert collab.should_request_human_review(result) is True
    
    def test_should_not_request_review_high_score(self):
        """Test not requesting review for high score"""
        collab = HumanAICollaboration()
        
        result = EvaluationResult(
            scores=EvaluationScore(
                functional_correctness=9.0,
                code_quality=9.0,
                architecture=9.0,
                security=9.0,
                maintainability=9.0,
            ),
            overall_score=9.0,
            strengths=["Excellent"],
            weaknesses=[],
            recommendations=[],
            verdict=EvaluationVerdict.ACCEPT,
            verdict_reason="Excellent",
        )
        
        assert collab.should_request_human_review(result) is False
    
    def test_create_review_request(self):
        """Test creating review request"""
        collab = HumanAICollaboration()
        
        auto_result = EvaluationResult(
            scores=EvaluationScore(),
            overall_score=6.5,
            strengths=["Good"],
            weaknesses=["Bad"],
            recommendations=["Fix"],
            verdict=EvaluationVerdict.NEEDS_REVISION,
            verdict_reason="",
        )
        
        request = collab.create_review_request(
            auto_result=auto_result,
            llm_result=None,
            context={"task": "test"},
        )
        
        assert request["type"] == "human_review_request"
        assert request["auto_evaluation"]["score"] == 6.5
        assert len(request["questions"]) > 0
    
    def test_generate_review_questions(self):
        """Test generating review questions"""
        collab = HumanAICollaboration()
        
        auto_result = EvaluationResult(
            scores=EvaluationScore(security=5.0),
            overall_score=7.0,
            strengths=[],
            weaknesses=[],
            recommendations=[],
            verdict=EvaluationVerdict.ACCEPT,
            verdict_reason="",
        )
        
        questions = collab._generate_review_questions(auto_result, None)
        
        assert any("安全" in q for q in questions)


class TestEvaluationVerdict:
    """Tests for EvaluationVerdict enum"""
    
    def test_verdict_values(self):
        """Test verdict enum values"""
        assert EvaluationVerdict.ACCEPT.value == "accept"
        assert EvaluationVerdict.NEEDS_REVISION.value == "needs_revision"
        assert EvaluationVerdict.REJECT.value == "reject"
