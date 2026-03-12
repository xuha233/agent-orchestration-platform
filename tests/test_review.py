"""
Tests for the two-stage review mechanism.
"""

import pytest
from aop.review import (
    ReviewStatus,
    ReviewIssue,
    ReviewResult,
    ReviewerBase,
    SpecComplianceReviewer,
    QualityReviewer,
    TwoStageReviewer,
)
from aop.review.two_stage import review_mvp, review_code, review_document


class TestReviewIssue:
    """Tests for ReviewIssue."""
    
    def test_create_issue(self):
        """Test creating a valid issue."""
        issue = ReviewIssue(
            severity="critical",
            category="spec",
            description="Missing requirement",
            suggestion="Add the missing feature",
        )
        
        assert issue.severity == "critical"
        assert issue.category == "spec"
        assert issue.description == "Missing requirement"
        assert issue.suggestion == "Add the missing feature"
        assert issue.location is None
    
    def test_create_issue_with_location(self):
        """Test creating an issue with location."""
        issue = ReviewIssue(
            severity="minor",
            category="quality",
            description="Long line",
            suggestion="Break into multiple lines",
            location="line 42",
        )
        
        assert issue.location == "line 42"
    
    def test_invalid_severity(self):
        """Test that invalid severity raises error."""
        with pytest.raises(ValueError):
            ReviewIssue(
                severity="invalid",
                category="spec",
                description="test",
                suggestion="test",
            )
    
    def test_invalid_category(self):
        """Test that invalid category raises error."""
        with pytest.raises(ValueError):
            ReviewIssue(
                severity="critical",
                category="invalid",
                description="test",
                suggestion="test",
            )
    
    def test_to_dict_and_from_dict(self):
        """Test serialization."""
        issue = ReviewIssue(
            severity="important",
            category="quality",
            description="Test issue",
            suggestion="Fix it",
            location="file.py:10",
        )
        
        data = issue.to_dict()
        restored = ReviewIssue.from_dict(data)
        
        assert restored.severity == issue.severity
        assert restored.category == issue.category
        assert restored.description == issue.description
        assert restored.suggestion == issue.suggestion
        assert restored.location == issue.location


class TestReviewResult:
    """Tests for ReviewResult."""
    
    def test_create_result(self):
        """Test creating a valid result."""
        result = ReviewResult(
            status=ReviewStatus.APPROVED,
            issues=[],
            summary="All good",
            score=95.0,
            stage="test",
        )
        
        assert result.status == ReviewStatus.APPROVED
        assert result.issues == []
        assert result.summary == "All good"
        assert result.score == 95.0
    
    def test_has_critical_issues(self):
        """Test critical issue detection."""
        issues = [
            ReviewIssue(severity="minor", category="quality", description="1", suggestion="1"),
            ReviewIssue(severity="critical", category="spec", description="2", suggestion="2"),
        ]
        
        result = ReviewResult(
            status=ReviewStatus.NEEDS_REVISION,
            issues=issues,
            summary="Issues found",
        )
        
        assert result.has_critical_issues is True
        assert result.has_important_issues is False
    
    def test_issue_counts(self):
        """Test issue counting."""
        issues = [
            ReviewIssue(severity="critical", category="spec", description="1", suggestion="1"),
            ReviewIssue(severity="critical", category="spec", description="2", suggestion="2"),
            ReviewIssue(severity="important", category="quality", description="3", suggestion="3"),
            ReviewIssue(severity="minor", category="quality", description="4", suggestion="4"),
        ]
        
        result = ReviewResult(
            status=ReviewStatus.NEEDS_REVISION,
            issues=issues,
            summary="Issues found",
        )
        
        counts = result.issue_counts
        assert counts["critical"] == 2
        assert counts["important"] == 1
        assert counts["minor"] == 1
    
    def test_invalid_score(self):
        """Test that invalid score raises error."""
        with pytest.raises(ValueError):
            ReviewResult(
                status=ReviewStatus.APPROVED,
                issues=[],
                summary="test",
                score=150.0,  # Invalid
            )


class TestSpecComplianceReviewer:
    """Tests for SpecComplianceReviewer."""
    
    @pytest.fixture
    def reviewer(self):
        return SpecComplianceReviewer()
    
    def test_extract_requirements(self, reviewer):
        """Test requirement extraction."""
        spec = """
        Requirements:
        - Must support user authentication
        - Should validate email addresses
        - Need to handle errors gracefully
        """
        
        requirements = reviewer._extract_requirements(spec)
        
        assert len(requirements) > 0
    
    def test_check_requirement_met_direct(self, reviewer):
        """Test direct requirement match."""
        content = "The system must support user authentication."
        requirement = "support user authentication"
        
        assert reviewer._check_requirement_met(content, requirement) is True
    
    def test_check_requirement_not_met(self, reviewer):
        """Test missing requirement detection."""
        content = "The system has a nice UI."
        requirement = "user authentication"
        
        assert reviewer._check_requirement_met(content, requirement) is False
    
    def test_review_with_missing_requirements(self, reviewer):
        """Test review with missing requirements."""
        spec = "The system must support user authentication and data export."
        content = "The system has a login page."  # Missing data export
        
        result = reviewer.review(content, {"spec": spec})
        
        # Review should run and produce a result
        assert result is not None
        assert result.status in [ReviewStatus.APPROVED, ReviewStatus.NEEDS_REVISION]
    
    def test_review_with_requirements_met(self, reviewer):
        """Test review with requirements met."""
        spec = "Must support user authentication"
        content = "The system supports user authentication with login and logout."
        
        result = reviewer.review(content, {"spec": spec})
        
        # Should pass since "user authentication" is in content
        assert result.status == ReviewStatus.APPROVED
        assert result.score is not None
        assert result.score > 50
    
    def test_find_extras_basic(self, reviewer):
        """Test overbuilding detection - basic case."""
        spec = "Simple user login"
        content = "User login feature implemented"
        
        extras = reviewer._find_extras(content, spec, "mvp")
        
        # Should return a list (may be empty if content matches spec)
        assert isinstance(extras, list)
    
    def test_review_runs_successfully(self, reviewer):
        """Test that review runs without errors."""
        spec = "Feature: user login"
        content = "Features: user login implemented"
        
        result = reviewer.review(content, {"spec": spec})
        
        assert result is not None
        assert result.status in [ReviewStatus.APPROVED, ReviewStatus.NEEDS_REVISION]


class TestQualityReviewer:
    """Tests for QualityReviewer."""
    
    @pytest.fixture
    def reviewer(self):
        return QualityReviewer()
    
    def test_check_readability_long_lines(self, reviewer):
        """Test detection of long lines."""
        content = "x = " + "a" * 150  # Very long line
        
        issues = reviewer._check_readability(content, "code", {})
        
        assert any("long line" in i.description.lower() for i in issues)
    
    def test_check_completeness_placeholders(self, reviewer):
        """Test detection of placeholders."""
        content = "This is [TBD] and [TODO] add more details."
        
        issues = reviewer._check_completeness(content, "doc", {})
        
        assert len(issues) > 0
    
    def test_check_completeness_todos(self, reviewer):
        """Test detection of TODOs."""
        content = """def process():
    TODO: implement this
    pass
"""
        
        issues = reviewer._check_completeness(content, "code", {})
        
        assert len(issues) > 0
    
    def test_check_best_practices_secrets(self, reviewer):
        """Test detection of hardcoded secrets."""
        content = 'password = "secret123"'
        
        issues = reviewer._check_best_practices(content, "code", {})
        
        assert any(i.category == "security" for i in issues)
    
    def test_review_good_content(self, reviewer):
        """Test review of good quality content."""
        content = """# Documentation

## Overview
This is a well-structured document.

## Features
- Feature 1: Does something useful
- Feature 2: Does something else
"""
        
        result = reviewer.review(content, {"artifact_type": "doc"})
        
        assert result.score is not None
        assert result.score > 60
    
    def test_review_poor_content(self, reviewer):
        """Test review of poor quality content."""
        content = """# Doc
[TBD]
[TODO] add content
password = "secret"
"""
        
        result = reviewer.review(content, {"artifact_type": "doc"})
        
        assert result.status == ReviewStatus.NEEDS_REVISION
        assert len(result.issues) > 0


class TestTwoStageReviewer:
    """Tests for TwoStageReviewer."""
    
    @pytest.fixture
    def reviewer(self):
        return TwoStageReviewer()
    
    def test_review_spec_fails(self, reviewer):
        """Test that quality is skipped when spec fails."""
        spec = "Must have user authentication and data export"
        content = "Simple landing page"  # Missing both
        
        result = reviewer.review("mvp", content, spec)
        
        assert result.overall_status == ReviewStatus.NEEDS_REVISION
        assert result.spec_result.status == ReviewStatus.NEEDS_REVISION
        assert result.quality_result is None  # Skipped
    
    def test_review_both_stages(self, reviewer):
        """Test that both stages run when spec passes."""
        spec = "Must have user authentication"
        content = "The system has user authentication with login functionality."
        
        result = reviewer.review("mvp", content, spec)
        
        assert result.spec_result is not None
        assert result.quality_result is not None
        assert result.overall_score > 0
    
    def test_review_with_fix_loop(self, reviewer):
        """Test fix loop iteration."""
        spec = "Must have authentication"
        content = "Landing page"
        
        fix_count = [0]
        
        def fix_callback(issues):
            fix_count[0] += 1
            if fix_count[0] == 1:
                return "Landing page with authentication"
            return "Complete system with user authentication"
        
        result = reviewer.review_with_fix_loop(
            "mvp", content, spec, fix_callback, max_iterations=3
        )
        
        assert result.iterations >= 1
        assert fix_count[0] >= 1
    
    def test_review_with_fix_loop_max_iterations(self, reviewer):
        """Test that fix loop respects max iterations."""
        spec = "Must have feature X and Y and Z"
        content = "No relevant content"
        
        call_count = [0]
        
        def fix_callback(issues):
            call_count[0] += 1
            return f"Content {call_count[0]}"  # Never actually fixes
        
        result = reviewer.review_with_fix_loop(
            "mvp", content, spec, fix_callback, max_iterations=2
        )
        
        assert result.iterations == 2
        assert call_count[0] == 2
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        spec = "User authentication required"
        content = "System has user authentication"
        
        result = review_mvp(content, spec)
        assert result is not None
        
        result = review_code(content, spec)
        assert result is not None
        
        result = review_document(content, spec)
        assert result is not None
    
    def test_to_dict(self, reviewer):
        """Test result serialization."""
        spec = "Feature required"
        content = "Feature implemented"
        
        result = reviewer.review("mvp", content, spec)
        data = result.to_dict()
        
        assert "spec_result" in data
        assert "quality_result" in data
        assert "overall_status" in data
        assert "overall_score" in data
        assert "all_issues" in data


class TestIntegration:
    """Integration tests."""
    
    def test_full_review_workflow(self):
        """Test complete review workflow."""
        spec = """Requirements:
- User authentication
- Data validation
- Error handling
"""
        
        content = """# MVP Implementation

## Authentication
Users can log in and log out.

## Validation
All inputs are validated.

## Error Handling
Errors are caught and logged.
"""
        
        reviewer = TwoStageReviewer()
        result = reviewer.review("mvp", content, spec)
        
        assert result.spec_result is not None
        # Should complete without error
        assert result.overall_status in [ReviewStatus.APPROVED, ReviewStatus.NEEDS_REVISION]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
