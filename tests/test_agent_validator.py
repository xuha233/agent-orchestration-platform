"""
测试 AutoValidator - 自动验证器

测试自动验证器的核心功能：
- 验证假设
- 检查成功标准
- 收集证据
- 综合判断
"""

from __future__ import annotations

import pytest

from aop.agent.validator import AutoValidator
from aop.agent.types import ValidationVerdict


class TestAutoValidatorBasic:
    """测试 AutoValidator 基础功能"""

    def test_create_validator(self) -> None:
        """测试创建验证器"""
        validator = AutoValidator()

        assert validator.success_patterns is not None
        assert validator.failure_patterns is not None
        assert len(validator.success_patterns) > 0
        assert len(validator.failure_patterns) > 0

    def test_validate_empty_results(self) -> None:
        """测试空执行结果的验证"""
        validator = AutoValidator()

        hypothesis = {
            "hypothesis_id": "h1",
            "statement": "测试假设",
        }

        result = validator.validate(hypothesis, [])

        assert result.hypothesis_id == "h1"
        assert result.verdict == ValidationVerdict.REFUTED
        assert result.state == "refuted"

    def test_validate_successful_execution(self) -> None:
        """测试成功执行的验证"""
        validator = AutoValidator()

        hypothesis = {
            "hypothesis_id": "h1",
            "statement": "功能正常工作",
            "success_criteria": ["测试通过", "无错误"],
        }

        execution_results = [
            {
                "stdout": "All tests passed\nSuccess: 10 tests passed",
                "stderr": "",
                "exit_code": 0,
            }
        ]

        result = validator.validate(hypothesis, execution_results)

        assert result.hypothesis_id == "h1"
        assert result.verdict == ValidationVerdict.VALIDATED
        assert result.confidence >= 0.5
        assert len(result.evidence) > 0

    def test_validate_failed_execution(self) -> None:
        """测试失败执行的验证"""
        validator = AutoValidator()

        hypothesis = {
            "hypothesis_id": "h1",
            "statement": "功能正常工作",
            "success_criteria": ["测试通过"],
        }

        execution_results = [
            {
                "stdout": "Running tests...\nFAILED: 3 tests failed",
                "stderr": "Error: Test failure",
                "exit_code": 1,
            }
        ]

        result = validator.validate(hypothesis, execution_results)

        assert result.hypothesis_id == "h1"
        assert result.verdict == ValidationVerdict.REFUTED
        assert len(result.counter_evidence) > 0


class TestAutoValidatorSuccessCriteria:
    """测试成功标准检查"""

    def test_check_success_criteria_empty(self) -> None:
        """测试空成功标准"""
        validator = AutoValidator()

        hypothesis = {"hypothesis_id": "h1"}
        execution_results = [{"stdout": "done", "exit_code": 0}]

        result = validator._check_success_criteria(hypothesis, execution_results)

        assert result["total"] == 0
        assert result["pass_rate"] == 1.0

    def test_check_success_criteria_passed(self) -> None:
        """测试通过成功标准"""
        validator = AutoValidator()

        hypothesis = {
            "hypothesis_id": "h1",
            "success_criteria": ["测试通过", "无错误"],
        }

        execution_results = [
            {
                "stdout": "All tests passed\nNo errors found",
                "stderr": "",
                "exit_code": 0,
            }
        ]

        result = validator._check_success_criteria(hypothesis, execution_results)

        assert result["total"] == 2
        assert result["pass_rate"] >= 0.5
        assert len(result["passed"]) > 0

    def test_check_success_criteria_failed(self) -> None:
        """测试失败的成功标准"""
        validator = AutoValidator()

        hypothesis = {
            "hypothesis_id": "h1",
            "success_criteria": ["测试通过", "无错误"],
        }

        execution_results = [
            {
                "stdout": "Tests failed",
                "stderr": "Error: Critical error",
                "exit_code": 1,
            }
        ]

        result = validator._check_success_criteria(hypothesis, execution_results)

        assert result["total"] == 2
        assert result["pass_rate"] < 0.5
        assert len(result["failed"]) > 0

    def test_evaluate_criterion_test_pass(self) -> None:
        """测试评估测试通过标准"""
        validator = AutoValidator()

        # 有测试摘要
        test_summary = {"passed": 5, "failed": 0}
        output = "5 tests passed"
        result = validator._evaluate_criterion("测试通过", output, test_summary)
        assert result is True

        # 无测试摘要，但输出中有 passed
        result = validator._evaluate_criterion("test pass", "All tests passed", None)
        assert result is True

    def test_evaluate_criterion_no_error(self) -> None:
        """测试评估无错误标准"""
        validator = AutoValidator()

        result = validator._evaluate_criterion("无错误", "Operation completed", None)
        assert result is True

        result = validator._evaluate_criterion("no error", "Error occurred", None)
        assert result is False

    def test_evaluate_criterion_performance(self) -> None:
        """测试评估性能标准"""
        validator = AutoValidator()

        # 在阈值内
        output = "耗时: 500ms"
        result = validator._evaluate_criterion("响应时间小于 1000ms", output, None)
        assert result is True

        # 超出阈值
        output = "耗时: 2000ms"
        result = validator._evaluate_criterion("响应时间小于 1000ms", output, None)
        assert result is False


class TestAutoValidatorEvidence:
    """测试证据收集"""

    def test_collect_evidence_success(self) -> None:
        """测试收集成功证据"""
        validator = AutoValidator()

        results = [
            {
                "stdout": "All tests passed\nDone successfully",
                "stderr": "",
                "exit_code": 0,
                "artifacts": ["output.json"],
            }
        ]

        evidence = validator._collect_evidence(results)

        assert len(evidence) > 0
        assert any("exit_code=0" in e for e in evidence)
        assert any("passed" in e.lower() for e in evidence)

    def test_collect_evidence_with_artifacts(self) -> None:
        """测试收集包含产物的证据"""
        validator = AutoValidator()

        results = [
            {
                "stdout": "Build completed",
                "stderr": "",
                "exit_code": 0,
                "artifacts": [
                    {"path": "/output/report.json", "type": "report"},
                    "result.log",
                ],
            }
        ]

        evidence = validator._collect_evidence(results)

        assert any("产物" in e for e in evidence)

    def test_collect_counter_evidence_failure(self) -> None:
        """测试收集失败证据"""
        validator = AutoValidator()

        results = [
            {
                "stdout": "Build failed",
                "stderr": "Error: Compilation error",
                "exit_code": 1,
            }
        ]

        counter_evidence = validator._collect_counter_evidence(results)

        assert len(counter_evidence) > 0
        assert any("exit_code=1" in e for e in counter_evidence)

    def test_collect_counter_evidence_with_errors(self) -> None:
        """测试收集包含错误的证据"""
        validator = AutoValidator()

        results = [
            {
                "stdout": "",
                "stderr": "Error: Module not found\nException: ValueError",
                "exit_code": 1,
            }
        ]

        counter_evidence = validator._collect_counter_evidence(results)

        assert any("错误" in e for e in counter_evidence)
        assert any("异常" in e for e in counter_evidence)


class TestAutoValidatorTestSummary:
    """测试测试摘要提取"""

    def test_extract_test_summary_pytest(self) -> None:
        """测试提取 pytest 风格摘要"""
        validator = AutoValidator()

        output = "collected 5 items\n....F\n4 passed, 1 failed"
        summary = validator._extract_test_summary(output)

        assert summary is not None
        assert summary["passed"] == 4
        assert summary["failed"] == 1
        assert summary["framework"] == "pytest"

    def test_extract_test_summary_jest(self) -> None:
        """测试提取 Jest 风格摘要"""
        validator = AutoValidator()

        output = "Tests: 10 passed, 2 failed"
        summary = validator._extract_test_summary(output)

        assert summary is not None
        assert summary["passed"] == 10
        assert summary["failed"] == 2
        assert summary["framework"] == "jest"

    def test_extract_test_summary_generic(self) -> None:
        """测试提取通用风格摘要"""
        validator = AutoValidator()

        output = "成功: 8, 失败: 2"
        summary = validator._extract_test_summary(output)

        assert summary is not None
        assert summary["passed"] == 8
        assert summary["failed"] == 2

    def test_extract_test_summary_none(self) -> None:
        """测试无测试摘要"""
        validator = AutoValidator()

        output = "No test results found"
        summary = validator._extract_test_summary(output)

        assert summary is None


class TestAutoValidatorVerdict:
    """测试验证判断"""

    def test_make_verdict_validated(self) -> None:
        """测试验证通过判断"""
        validator = AutoValidator()

        evidence = ["测试通过", "无错误", "执行成功"]
        counter_evidence = []

        verdict, confidence = validator._make_verdict(evidence, counter_evidence)

        assert verdict == ValidationVerdict.VALIDATED
        assert confidence >= 0.8

    def test_make_verdict_refuted(self) -> None:
        """测试验证反驳判断"""
        validator = AutoValidator()

        evidence = []
        counter_evidence = ["测试失败", "错误: Critical error", "异常退出"]

        verdict, confidence = validator._make_verdict(evidence, counter_evidence)

        assert verdict == ValidationVerdict.REFUTED
        assert confidence <= 0.2

    def test_make_verdict_inconclusive(self) -> None:
        """测试不明确判断"""
        validator = AutoValidator()

        evidence = ["部分测试通过"]
        counter_evidence = ["部分测试失败"]

        verdict, confidence = validator._make_verdict(evidence, counter_evidence)

        assert verdict == ValidationVerdict.INCONCLUSIVE

    def test_make_verdict_with_criteria(self) -> None:
        """测试结合成功标准的判断"""
        validator = AutoValidator()

        evidence = ["测试通过"]
        counter_evidence = []
        criteria_results = {"total": 5, "pass_rate": 1.0}

        verdict, confidence = validator._make_verdict(evidence, counter_evidence, criteria_results)

        assert verdict == ValidationVerdict.VALIDATED
        assert confidence >= 0.8

    def test_verdict_to_state(self) -> None:
        """测试验证结果转状态"""
        validator = AutoValidator()

        assert validator._verdict_to_state(ValidationVerdict.VALIDATED) == "validated"
        assert validator._verdict_to_state(ValidationVerdict.REFUTED) == "refuted"
        assert validator._verdict_to_state(ValidationVerdict.INCONCLUSIVE) == "inconclusive"
        assert validator._verdict_to_state(ValidationVerdict.NEEDS_MORE_INFO) == "pending"


class TestAutoValidatorErrorExtraction:
    """测试错误提取"""

    def test_extract_error_details(self) -> None:
        """测试提取错误详情"""
        validator = AutoValidator()

        output = "Error: File not found\nFAILED: test_login\nException: ValueError"
        details = validator._extract_error_details(output)

        assert len(details) > 0
        assert any("File not found" in d for d in details)

    def test_extract_failed_tests_pytest(self) -> None:
        """测试提取 pytest 失败测试"""
        validator = AutoValidator()

        output = "FAILED test_main.py::test_login\nFAILED test_api.py::test_create"
        failed = validator._extract_failed_tests(output)

        assert len(failed) > 0
        assert any("test_login" in f for f in failed)

    def test_extract_failed_tests_jest(self) -> None:
        """测试提取 Jest 失败测试"""
        validator = AutoValidator()

        output = "✕ should login\n✕ should create user"
        failed = validator._extract_failed_tests(output)

        assert len(failed) > 0

    def test_extract_exceptions(self) -> None:
        """测试提取异常"""
        validator = AutoValidator()

        output = "ValueError: Invalid input\nTypeError: Expected string"
        exceptions = validator._extract_exceptions(output)

        assert len(exceptions) > 0
        assert any("ValueError" in e for e in exceptions)


class TestAutoValidatorNextSteps:
    """测试下一步建议"""

    def test_generate_next_steps_validated(self) -> None:
        """测试验证通过的建议"""
        validator = AutoValidator()

        steps = validator._generate_next_steps(
            ValidationVerdict.VALIDATED,
            ["测试通过"],
            [],
            {"statement": "功能正常"}
        )

        assert len(steps) > 0
        assert any("验证" in s or "继续" in s for s in steps)

    def test_generate_next_steps_refuted(self) -> None:
        """测试验证反驳的建议"""
        validator = AutoValidator()

        steps = validator._generate_next_steps(
            ValidationVerdict.REFUTED,
            [],
            ["测试失败", "exit_code=1"],
            {"statement": "功能正常"}
        )

        assert len(steps) > 0
        assert any("检查" in s or "调整" in s for s in steps)

    def test_generate_next_steps_needs_more_info(self) -> None:
        """测试需要更多信息的建议"""
        validator = AutoValidator()

        steps = validator._generate_next_steps(
            ValidationVerdict.NEEDS_MORE_INFO,
            [],
            [],
            {"statement": "功能正常", "success_criteria": ["测试通过"]}
        )

        assert len(steps) > 0
        assert any("更多信息" in s or "补充" in s for s in steps)


class TestAutoValidatorPatterns:
    """测试模式匹配"""

    def test_success_patterns(self) -> None:
        """测试成功模式"""
        validator = AutoValidator()

        # 检查所有成功模式都有必要字段
        for pattern in validator.success_patterns:
            assert "match" in pattern
            assert "description" in pattern
            assert callable(pattern["match"])

    def test_failure_patterns(self) -> None:
        """测试失败模式"""
        validator = AutoValidator()

        # 检查所有失败模式都有必要字段
        for pattern in validator.failure_patterns:
            assert "match" in pattern
            assert "description" in pattern
            assert callable(pattern["match"])

    def test_match_success_pattern(self) -> None:
        """测试成功模式匹配"""
        validator = AutoValidator()

        # 找一个匹配的模式
        stdout = "Operation completed successfully"
        stderr = ""

        matched = False
        for pattern in validator.success_patterns:
            try:
                if pattern["match"](stdout, stderr):
                    matched = True
                    break
            except Exception:
                pass

        assert matched is True

    def test_match_failure_pattern(self) -> None:
        """测试失败模式匹配"""
        validator = AutoValidator()

        stdout = ""
        stderr = "Error: Something went wrong"

        matched = False
        for pattern in validator.failure_patterns:
            try:
                if pattern["match"](stdout, stderr):
                    matched = True
                    break
            except Exception:
                pass

        assert matched is True


class TestAutoValidatorEdgeCases:
    """测试边界情况"""

    def test_validate_with_no_hypothesis_id(self) -> None:
        """测试无 hypothesis_id 的验证"""
        validator = AutoValidator()

        hypothesis = {"statement": "测试"}
        results = [{"stdout": "done", "exit_code": 0}]

        result = validator.validate(hypothesis, results)

        assert result.hypothesis_id == ""

    def test_validate_with_mixed_results(self) -> None:
        """测试混合执行结果"""
        validator = AutoValidator()

        hypothesis = {
            "hypothesis_id": "h1",
            "statement": "测试",
            "success_criteria": ["测试通过"],
        }

        results = [
            {"stdout": "Test 1 passed", "exit_code": 0},
            {"stdout": "Test 2 failed", "stderr": "Error", "exit_code": 1},
        ]

        result = validator.validate(hypothesis, results)

        # 应该能处理混合结果
        assert result.verdict is not None

    def test_validate_with_long_output(self) -> None:
        """测试长输出"""
        validator = AutoValidator()

        hypothesis = {"hypothesis_id": "h1"}
        results = [
            {
                "stdout": "Line " * 1000 + "Success",
                "stderr": "",
                "exit_code": 0,
            }
        ]

        result = validator.validate(hypothesis, results)

        # 应该能处理长输出而不崩溃
        assert result is not None
        assert len(result.evidence) > 0

    def test_validate_with_unicode_output(self) -> None:
        """测试 Unicode 输出"""
        validator = AutoValidator()

        hypothesis = {
            "hypothesis_id": "h1",
            "success_criteria": ["测试通过"],
        }

        results = [
            {
                "stdout": "测试通过 ✅\n中文输出",
                "stderr": "",
                "exit_code": 0,
            }
        ]

        result = validator.validate(hypothesis, results)

        assert result is not None
        assert result.verdict == ValidationVerdict.VALIDATED

    def test_evaluate_criterion_empty_output(self) -> None:
        """测试空输出的标准评估"""
        validator = AutoValidator()

        result = validator._evaluate_criterion("测试通过", "", None)

        # 空输出应该不匹配
        assert result is False

    def test_collect_evidence_empty_results(self) -> None:
        """测试空结果的证据收集"""
        validator = AutoValidator()

        evidence = validator._collect_evidence([])

        assert evidence == []

    def test_collect_counter_evidence_empty_results(self) -> None:
        """测试空结果的反面证据收集"""
        validator = AutoValidator()

        counter_evidence = validator._collect_counter_evidence([])

        assert counter_evidence == []
