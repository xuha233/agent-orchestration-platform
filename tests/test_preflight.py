# -*- coding: utf-8 -*-
"""Tests for Pre-flight Validation"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.aop.agent.preflight import (
    PreFlightValidator,
    PreFlightStatus,
    PreFlightCheck,
    PreFlightResult,
    run_preflight,
)


class TestPreFlightCheck:
    """Tests for PreFlightCheck"""
    
    def test_check_creation(self):
        """Test creating a preflight check"""
        check = PreFlightCheck(
            name="Test Check",
            description="A test check",
            status=PreFlightStatus.READY,
            message="All good",
        )
        assert check.name == "Test Check"
        assert check.status == PreFlightStatus.READY
    
    def test_check_with_details(self):
        """Test check with details"""
        check = PreFlightCheck(
            name="File Check",
            description="Check files",
            status=PreFlightStatus.ALREADY_DONE,
            message="File exists",
            details={"files": ["test.py"]},
            recommendation="Skip task",
        )
        assert check.details == {"files": ["test.py"]}
        assert check.recommendation == "Skip task"


class TestPreFlightResult:
    """Tests for PreFlightResult"""
    
    def test_result_creation(self):
        """Test creating a result"""
        result = PreFlightResult(
            overall_status=PreFlightStatus.READY,
            checks=[],
            can_proceed=True,
        )
        assert result.overall_status == PreFlightStatus.READY
        assert result.can_proceed is True
    
    def test_summary(self):
        """Test summary generation"""
        checks = [
            PreFlightCheck(
                name="Check 1",
                description="First check",
                status=PreFlightStatus.READY,
                message="OK",
            ),
            PreFlightCheck(
                name="Check 2",
                description="Second check",
                status=PreFlightStatus.WARNING,
                message="Warning",
            ),
        ]
        result = PreFlightResult(
            overall_status=PreFlightStatus.WARNING,
            checks=checks,
            can_proceed=True,
        )
        summary = result.summary()
        assert "Check 1" in summary
        assert "Check 2" in summary


class TestPreFlightValidator:
    """Tests for PreFlightValidator"""
    
    def test_validator_creation(self, tmp_path):
        """Test creating a validator"""
        validator = PreFlightValidator(tmp_path)
        assert validator.repo_root == tmp_path
    
    def test_validate_empty_task(self, tmp_path):
        """Test validating an empty task"""
        validator = PreFlightValidator(tmp_path)
        result = validator.validate({})
        assert isinstance(result, PreFlightResult)
    
    def test_validate_task_with_objective(self, tmp_path):
        """Test validating a task with objective"""
        validator = PreFlightValidator(tmp_path)
        result = validator.validate({
            "objective": "Create a new module",
        })
        assert result.overall_status in [
            PreFlightStatus.READY,
            PreFlightStatus.WARNING,
        ]
    
    def test_code_exists_check(self, tmp_path):
        """Test code existence check"""
        # Create a test file
        test_file = tmp_path / "test_module.py"
        test_file.write_text("# test module")
        
        validator = PreFlightValidator(tmp_path)
        result = validator.validate({
            "objective": "Create test_module",
        })
        
        # Should detect that file exists
        code_check = next(
            (c for c in result.checks if c.name == "代码存在检查"),
            None
        )
        assert code_check is not None
    
    def test_working_directory_check(self, tmp_path):
        """Test working directory check"""
        validator = PreFlightValidator(tmp_path)
        result = validator.validate({})
        
        dir_check = next(
            (c for c in result.checks if c.name == "工作目录检查"),
            None
        )
        assert dir_check is not None
    
    def test_extract_file_keywords(self, tmp_path):
        """Test keyword extraction"""
        validator = PreFlightValidator(tmp_path)
        
        keywords = validator._extract_file_keywords(
            "创建 auth 模块并实现 login 功能"
        )
        assert "auth" in keywords or "login" in keywords
    
    def test_check_criterion_with_file(self, tmp_path):
        """Test criterion checking with file"""
        # Create a test file
        test_file = tmp_path / "feature.py"
        test_file.write_text("def my_function(): pass")
        
        validator = PreFlightValidator(tmp_path)
        
        # Check if function exists
        result = validator._check_criterion("实现 my_function 函数")
        assert result is True
    
    def test_blocking_issue_prevents_proceed(self, tmp_path):
        """Test that blocking issue prevents proceeding"""
        # Use non-existent directory
        validator = PreFlightValidator("/non/existent/path")
        result = validator.validate({})
        
        assert result.can_proceed is False
        assert result.overall_status == PreFlightStatus.BLOCKING_ISSUE


class TestPreFlightStatus:
    """Tests for PreFlightStatus enum"""
    
    def test_status_values(self):
        """Test status enum values"""
        assert PreFlightStatus.READY.value == "ready"
        assert PreFlightStatus.ALREADY_DONE.value == "already_done"
        assert PreFlightStatus.SKIP_RECOMMENDED.value == "skip"
        assert PreFlightStatus.BLOCKING_ISSUE.value == "blocked"
        assert PreFlightStatus.WARNING.value == "warning"


class TestRunPreflight:
    """Tests for run_preflight convenience function"""
    
    def test_run_preflight(self, tmp_path):
        """Test run_preflight function"""
        result = run_preflight({"objective": "Test"}, tmp_path)
        assert isinstance(result, PreFlightResult)
    
    def test_run_preflight_with_string_path(self, tmp_path):
        """Test run_preflight with string path"""
        result = run_preflight({}, str(tmp_path))
        assert isinstance(result, PreFlightResult)
