"""Tests for report formatters."""

import json
import os
import tempfile
import pytest
from dataclasses import dataclass, field
from typing import Dict, List, Any

# We need to create a mock ReviewResult for testing
@dataclass
class MockReviewResult:
    """Mock ReviewResult for testing."""
    task_id: str = "test-task-001"
    artifact_root: str = os.path.join(tempfile.gettempdir(), "artifacts", "test-task-001")
    decision: str = "FAIL"
    terminal_state: str = "completed"
    provider_results: Dict[str, Any] = field(default_factory=dict)
    findings_count: int = 0
    parse_success_count: int = 2
    parse_failure_count: int = 0
    schema_valid_count: int = 5
    dropped_findings_count: int = 0
    findings: List[Dict[str, Any]] = field(default_factory=list)
    token_usage_summary: Dict[str, Any] = None
    synthesis: Dict[str, Any] = None


def create_sample_findings():
    """Create sample findings for testing."""
    return [
        {
            "finding_id": "finding-001",
            "severity": "critical",
            "category": "security",
            "title": "SQL Injection vulnerability",
            "evidence": {
                "file": "src/db/queries.py",
                "line": 42,
                "snippet": "cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')"
            },
            "recommendation": "Use parameterized queries",
            "confidence": 0.95,
            "fingerprint": "abc123",
            "detected_by": ["claude", "codex"]
        },
        {
            "finding_id": "finding-002",
            "severity": "high",
            "category": "bug",
            "title": "Null pointer dereference",
            "evidence": {
                "file": "src/handlers/user.py",
                "line": 15,
                "snippet": "return user.name.upper()"
            },
            "recommendation": "Add null check before accessing user.name",
            "confidence": 0.85,
            "fingerprint": "def456",
            "detected_by": ["claude"]
        },
        {
            "finding_id": "finding-003",
            "severity": "medium",
            "category": "performance",
            "title": "Inefficient loop",
            "evidence": {
                "file": "src/utils/processing.py",
                "line": 100,
                "snippet": "for i in range(len(items)):"
            },
            "recommendation": "Use enumerate() or iterate directly",
            "confidence": 0.7,
            "fingerprint": "ghi789",
            "detected_by": ["codex"]
        },
        {
            "finding_id": "finding-004",
            "severity": "low",
            "category": "maintainability",
            "title": "Missing docstring",
            "evidence": {
                "file": "src/utils/helpers.py",
                "line": 1,
                "snippet": "def process_data(data):"
            },
            "recommendation": "Add docstring to document function purpose",
            "confidence": 0.6,
            "fingerprint": "jkl012",
            "detected_by": ["claude"]
        }
    ]


def create_sample_provider_results():
    """Create sample provider results for testing."""
    return {
        "claude": {
            "success": True,
            "findings_count": 3,
            "wall_clock_seconds": 12.5,
            "parse_ok": True
        },
        "codex": {
            "success": True,
            "findings_count": 2,
            "wall_clock_seconds": 8.3,
            "parse_ok": True
        }
    }


def create_sample_token_usage():
    """Create sample token usage for testing."""
    return {
        "providers_with_usage": 2,
        "provider_count": 2,
        "completeness": "full",
        "totals": {
            "prompt_tokens": 5000,
            "completion_tokens": 2500,
            "total_tokens": 7500
        }
    }


class TestFormatReport:
    """Tests for format_report function."""
    
    def test_format_report_empty_findings(self):
        """Test report with no findings."""
        from aop.report.formatters import format_report
        
        result = MockReviewResult(
            decision="PASS",
            findings=[],
            findings_count=0
        )
        
        report = format_report(result)
        
        assert "AOP Review Report" in report
        assert "test-task-001" in report
        assert "PASS" in report
        # Severity breakdown shows all levels even when zero
        assert "CRITICAL: 0" in report
        assert "HIGH: 0" in report
    
    def test_format_report_with_findings(self):
        """Test report with findings."""
        from aop.report.formatters import format_report
        
        result = MockReviewResult(
            findings=create_sample_findings(),
            findings_count=4,
            provider_results=create_sample_provider_results()
        )
        
        report = format_report(result)
        
        assert "SQL Injection vulnerability" in report
        assert "CRITICAL" in report
        assert "HIGH" in report
        assert "src/db/queries.py" in report
        assert "Use parameterized queries" in report
    
    def test_format_report_with_token_usage(self):
        """Test report includes token usage."""
        from aop.report.formatters import format_report
        
        result = MockReviewResult(
            findings=create_sample_findings(),
            findings_count=4,
            token_usage_summary=create_sample_token_usage()
        )
        
        report = format_report(result)
        
        assert "Token Usage" in report
        assert "5000" in report  # prompt tokens
        assert "7500" in report  # total tokens


class TestFormatMarkdownPR:
    """Tests for format_markdown_pr function."""
    
    def test_format_markdown_pr_empty_findings(self):
        """Test markdown PR with no findings."""
        from aop.report.formatters import format_markdown_pr
        
        result = MockReviewResult(
            decision="PASS",
            findings=[],
            findings_count=0
        )
        
        markdown = format_markdown_pr(result)
        
        assert "## AOP Review Summary" in markdown
        assert "PASS" in markdown
        assert "No findings reported" in markdown
    
    def test_format_markdown_pr_with_findings(self):
        """Test markdown PR with findings."""
        from aop.report.formatters import format_markdown_pr
        
        result = MockReviewResult(
            findings=create_sample_findings(),
            findings_count=4,
            provider_results=create_sample_provider_results()
        )
        
        markdown = format_markdown_pr(result)
        
        assert "## AOP Review Summary" in markdown
        assert "| Severity | Count |" in markdown
        assert "SQL Injection vulnerability" in markdown
        assert "src/db/queries.py" in markdown
    
    def test_format_markdown_pr_with_token_usage(self):
        """Test markdown PR includes token usage."""
        from aop.report.formatters import format_markdown_pr
        
        result = MockReviewResult(
            findings=create_sample_findings(),
            findings_count=4,
            token_usage_summary=create_sample_token_usage()
        )
        
        markdown = format_markdown_pr(result)
        
        assert "### Token Usage" in markdown
        assert "7500" in markdown  # total tokens


class TestFormatSarif:
    """Tests for format_sarif function."""
    
    def test_format_sarif_empty_findings(self):
        """Test SARIF with no findings."""
        from aop.report.formatters import format_sarif
        
        result = MockReviewResult(
            findings=[],
            findings_count=0
        )
        
        sarif = format_sarif(result)
        
        assert sarif["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"]) == 1
        assert sarif["runs"][0]["tool"]["driver"]["name"] == "AOP"
    
    def test_format_sarif_with_findings(self):
        """Test SARIF with findings."""
        from aop.report.formatters import format_sarif
        
        result = MockReviewResult(
            findings=create_sample_findings(),
            findings_count=4
        )
        
        sarif = format_sarif(result)
        
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"][0]["results"]) == 4
        
        # Check first finding
        first_result = sarif["runs"][0]["results"][0]
        assert "ruleId" in first_result
        assert "level" in first_result
        assert "message" in first_result
    
    def test_format_sarif_severity_mapping(self):
        """Test SARIF severity level mapping."""
        from aop.report.formatters import format_sarif
        
        result = MockReviewResult(
            findings=create_sample_findings(),
            findings_count=4
        )
        
        sarif = format_sarif(result)
        results = sarif["runs"][0]["results"]
        
        levels = {r["level"] for r in results}
        assert "error" in levels  # critical and high
        assert "warning" in levels  # medium
        assert "note" in levels  # low
    
    def test_format_sarif_location(self):
        """Test SARIF location format."""
        from aop.report.formatters import format_sarif
        
        result = MockReviewResult(
            findings=create_sample_findings(),
            findings_count=4
        )
        
        sarif = format_sarif(result)
        
        for r in sarif["runs"][0]["results"]:
            if "locations" in r and r["locations"]:
                loc = r["locations"][0]
                assert "physicalLocation" in loc
                assert "artifactLocation" in loc["physicalLocation"]
                assert "uri" in loc["physicalLocation"]["artifactLocation"]


class TestFormatJson:
    """Tests for format_json function."""
    
    def test_format_json_basic(self):
        """Test JSON output format."""
        from aop.report.formatters import format_json
        
        result = MockReviewResult(
            findings=create_sample_findings(),
            findings_count=4,
            provider_results=create_sample_provider_results()
        )
        
        output = format_json(result)
        
        assert output["task_id"] == "test-task-001"
        assert output["decision"] == "FAIL"
        assert output["findings_count"] == 4
        assert len(output["findings"]) == 4
    
    def test_format_json_serializable(self):
        """Test JSON output is serializable."""
        from aop.report.formatters import format_json
        
        result = MockReviewResult(
            findings=create_sample_findings(),
            findings_count=4,
            token_usage_summary=create_sample_token_usage()
        )
        
        output = format_json(result)
        
        # Should not raise
        json_str = json.dumps(output)
        assert json_str is not None


class TestFormatSummary:
    """Tests for format_summary function."""
    
    def test_format_summary_with_findings(self):
        """Test summary with findings."""
        from aop.report.formatters import format_summary
        
        result = MockReviewResult(
            decision="FAIL",
            findings=create_sample_findings(),
            findings_count=4
        )
        
        summary = format_summary(result)
        
        assert "AOP: FAIL" in summary
        assert "1 critical" in summary
        assert "1 high" in summary
        assert "test-task-001" in summary
    
    def test_format_summary_no_findings(self):
        """Test summary with no findings."""
        from aop.report.formatters import format_summary
        
        result = MockReviewResult(
            decision="PASS",
            findings=[],
            findings_count=0
        )
        
        summary = format_summary(result)
        
        assert "AOP: PASS" in summary
        assert "no findings" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

