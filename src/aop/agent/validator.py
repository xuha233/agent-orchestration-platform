"""
AutoValidator - 自动验证器

根据执行结果自动判断假设状态。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

from .types import ValidationResult, ValidationVerdict


class AutoValidator:
    """
    自动验证器

    根据执行结果自动判断假设状态。

    验证策略:
    1. 分析执行日志和产物
    2. 匹配成功标准
    3. 检测失败模式
    4. 综合判断假设状态
    """

    def __init__(self):
        self.success_patterns = self._load_success_patterns()
        self.failure_patterns = self._load_failure_patterns()

    def validate(
        self,
        hypothesis: dict,
        execution_results: List[dict],
    ) -> ValidationResult:
        """
        验证假设

        Args:
            hypothesis: 要验证的假设
            execution_results: 相关的执行结果

        Returns:
            验证结果
        """
        # 检查成功标准
        criteria_results = self._check_success_criteria(hypothesis, execution_results)
        
        # 收集证据
        evidence = self._collect_evidence(execution_results, hypothesis)
        counter_evidence = self._collect_counter_evidence(execution_results)

        # 综合判断
        verdict, confidence = self._make_verdict(
            evidence, counter_evidence, criteria_results
        )

        # 确定状态
        state = self._verdict_to_state(verdict)

        # 生成下一步建议
        next_steps = self._generate_next_steps(verdict, evidence, counter_evidence, hypothesis)

        return ValidationResult(
            hypothesis_id=hypothesis.get("hypothesis_id", ""),
            state=state,
            verdict=verdict,
            confidence=confidence,
            evidence=evidence,
            counter_evidence=counter_evidence,
            reasoning=self._generate_reasoning(verdict, evidence, counter_evidence),
            next_steps=next_steps,
        )

    def _check_success_criteria(
        self,
        hypothesis: dict,
        execution_results: List[dict],
    ) -> dict:
        """
        检查假设的成功标准
        
        Args:
            hypothesis: 包含 success_criteria 的假设
            execution_results: 执行结果列表
            
        Returns:
            包含通过/失败标准详情的字典
        """
        criteria = hypothesis.get("success_criteria", [])
        if not criteria:
            return {"passed": [], "failed": [], "total": 0, "pass_rate": 1.0}
        
        passed = []
        failed = []
        
        # 合并所有输出用于检查
        combined_stdout = "\n".join(r.get("stdout", "") for r in execution_results)
        combined_stderr = "\n".join(r.get("stderr", "") for r in execution_results)
        combined_output = combined_stdout + "\n" + combined_stderr
        
        # 检查是否有测试结果摘要
        test_summary = self._extract_test_summary(combined_output)
        
        for criterion in criteria:
            criterion_text = criterion if isinstance(criterion, str) else str(criterion)
            is_passed = self._evaluate_criterion(criterion_text, combined_output, test_summary)
            
            if is_passed:
                passed.append(criterion_text)
            else:
                failed.append(criterion_text)
        
        total = len(criteria)
        pass_rate = len(passed) / total if total > 0 else 1.0
        
        return {
            "passed": passed,
            "failed": failed,
            "total": total,
            "pass_rate": pass_rate,
        }

    def _evaluate_criterion(
        self,
        criterion: str,
        output: str,
        test_summary: dict | None,
    ) -> bool:
        """
        评估单个成功标准
        
        Args:
            criterion: 成功标准文本
            output: 合并的输出内容
            test_summary: 测试结果摘要（如果有）
            
        Returns:
            标准是否通过
        """
        criterion_lower = criterion.lower()
        
        # 测试通过标准
        if "测试通过" in criterion or "test pass" in criterion_lower:
            if test_summary:
                return test_summary.get("passed", 0) > 0 and test_summary.get("failed", 0) == 0
            # 检查英文或中文测试通过标志
            return ("passed" in output.lower() or "测试通过" in output) and ("failed" not in output.lower() and "失败" not in output)
        
        # 无错误标准
        if "无错误" in criterion or "no error" in criterion_lower:
            return "error" not in output.lower() and "exception" not in output.lower()
        
        # 性能标准（响应时间等）
        time_match = re.search(r"(\d+)\s*(ms|秒|s)", criterion)
        if time_match:
            threshold = int(time_match.group(1))
            # 在输出中查找实际时间
            actual_match = re.search(r"(?:耗时|cost|time)[：:]\s*(\d+)\s*(ms|秒|s)", output, re.IGNORECASE)
            if actual_match:
                actual = int(actual_match.group(1))
                return actual <= threshold
        
        # 返回值标准
        return_match = re.search(r"返回[值为]?\s*(.+)", criterion)
        if return_match:
            expected = return_match.group(1).strip()
            return expected in output
        
        # 默认：在输出中查找标准关键词
        keywords = re.findall(r"[\u4e00-\u9fa5\w]+", criterion)
        matched = sum(1 for kw in keywords if kw.lower() in output.lower())
        return matched >= len(keywords) * 0.5  # 至少匹配一半关键词

    def _extract_test_summary(self, output: str) -> dict | None:
        """
        从输出中提取测试结果摘要
        
        Args:
            output: 合并的输出内容
            
        Returns:
            测试摘要字典或 None
        """
        # Jest 风格: "Tests: X passed, Y failed" - 先检查，因为更具体
        jest_match = re.search(
            r"Tests:\s*(\d+)\s*passed[^,]*(?:,\s*(\d+)\s*failed)?",
            output,
            re.IGNORECASE
        )
        if jest_match:
            return {
                "passed": int(jest_match.group(1)),
                "failed": int(jest_match.group(2) or 0),
                "framework": "jest",
            }
        
        # pytest 风格: "X passed, Y failed" - 后检查，更通用
        pytest_match = re.search(
            r"(\d+)\s*passed[^,]*(?:,\s*(\d+)\s*failed)?",
            output,
            re.IGNORECASE
        )
        if pytest_match:
            return {
                "passed": int(pytest_match.group(1)),
                "failed": int(pytest_match.group(2) or 0),
                "framework": "pytest",
            }
        
        # 通用: "成功 X, 失败 Y"
        generic_match = re.search(
            r"(?:成功|passed)\s*[：:]?\s*(\d+)[^,]*(?:,|，)\s*(?:失败|failed)\s*[：:]?\s*(\d+)",
            output,
            re.IGNORECASE
        )
        if generic_match:
            return {
                "passed": int(generic_match.group(1)),
                "failed": int(generic_match.group(2)),
                "framework": "generic",
            }
        
        return None

    def _collect_evidence(
        self,
        results: List[dict],
        hypothesis: dict | None = None,
    ) -> List[str]:
        """
        收集支持假设的证据
        
        增强功能：
        - 收集测试结果
        - 收集产物文件
        - 匹配日志模式
        
        Args:
            results: 执行结果列表
            hypothesis: 相关假设（可选）
            
        Returns:
            证据列表
        """
        evidence = []
        
        for result in results:
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            exit_code = result.get("exit_code", 0)
            artifacts = result.get("artifacts", [])
            
            # 1. 退出状态
            if exit_code == 0:
                evidence.append("✓ 执行成功退出 (exit_code=0)")
            
            # 2. 测试结果
            test_summary = self._extract_test_summary(stdout + stderr)
            if test_summary:
                passed = test_summary["passed"]
                failed = test_summary["failed"]
                framework = test_summary.get("framework", "unknown")
                if failed == 0 and passed > 0:
                    evidence.append(f"✓ 测试全部通过 ({framework}: {passed} passed)")
                elif passed > 0:
                    evidence.append(f"○ 部分测试通过 ({passed}/{passed + failed})")
            
            # 3. 产物文件
            if artifacts:
                for artifact in artifacts:
                    if isinstance(artifact, str):
                        evidence.append(f"✓ 产物文件: {artifact}")
                    elif isinstance(artifact, dict):
                        path = artifact.get("path", "")
                        artifact_type = artifact.get("type", "file")
                        evidence.append(f"✓ 产物: {artifact_type} - {path}")
            
            # 4. 成功关键词匹配
            success_keywords = ["success", "completed", "完成", "成功", "passed", "done"]
            found_keywords = [kw for kw in success_keywords if kw in stdout.lower()]
            if found_keywords:
                evidence.append(f"✓ 发现成功关键词: {', '.join(found_keywords)}")
            
            # 5. 成功模式匹配
            for pattern in self.success_patterns:
                try:
                    if pattern["match"](stdout, stderr):
                        evidence.append(f"✓ {pattern['description']}")
                except Exception:
                    pass
            
            # 6. 性能指标
            perf_match = re.search(r"(?:耗时|cost|duration)[：:]\s*(\d+)\s*(ms|秒|s)", stdout, re.IGNORECASE)
            if perf_match:
                evidence.append(f"✓ 性能指标: 耗时 {perf_match.group(1)}{perf_match.group(2)}")
            
            # 7. 版本/构建信息
            version_match = re.search(r"(?:version|版本)[：:\s]*([\d.]+)", stdout, re.IGNORECASE)
            if version_match:
                evidence.append(f"✓ 版本信息: v{version_match.group(1)}")
        
        # 去重
        return list(dict.fromkeys(evidence))

    def _collect_counter_evidence(self, results: List[dict]) -> List[str]:
        """
        收集反对假设的证据
        
        增强功能：
        - 提取错误详情
        - 收集失败测试用例
        - 匹配失败模式
        
        Args:
            results: 执行结果列表
            
        Returns:
            反面证据列表
        """
        counter_evidence = []
        
        for result in results:
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            exit_code = result.get("exit_code", 0)
            
            # 1. 进程异常退出
            if exit_code != 0:
                counter_evidence.append(f"✗ 进程异常退出 (exit_code={exit_code})")
            
            # 2. 错误详情提取
            error_details = self._extract_error_details(stderr or stdout)
            for detail in error_details:
                counter_evidence.append(f"✗ 错误: {detail}")
            
            # 3. 失败测试用例
            failed_tests = self._extract_failed_tests(stdout + stderr)
            for test in failed_tests:
                counter_evidence.append(f"✗ 测试失败: {test}")
            
            # 4. 警告信息
            warnings = re.findall(r"(?:warning|警告)[：:]\s*(.+)", stdout + stderr, re.IGNORECASE)
            for warning in warnings[:3]:  # 最多3条警告
                counter_evidence.append(f"⚠ 警告: {warning.strip()}")
            
            # 5. 异常堆栈
            exceptions = self._extract_exceptions(stdout + stderr)
            for exc in exceptions:
                counter_evidence.append(f"✗ 异常: {exc}")
            
            # 6. 失败模式匹配
            for pattern in self.failure_patterns:
                try:
                    if pattern["match"](stdout, stderr):
                        counter_evidence.append(f"✗ {pattern['description']}")
                except Exception:
                    pass
            
            # 7. 超时检测
            if "timeout" in (stdout + stderr).lower() or "timed out" in (stdout + stderr).lower():
                counter_evidence.append("✗ 检测到超时")
            
            # 8. 内存/资源错误
            resource_errors = re.findall(
                r"(?:out of memory|内存不足|oom|资源不足|resource exhausted)",
                stdout + stderr,
                re.IGNORECASE
            )
            if resource_errors:
                counter_evidence.append("✗ 资源不足错误")
        
        # 去重
        return list(dict.fromkeys(counter_evidence))

    def _extract_error_details(self, output: str) -> List[str]:
        """
        从输出中提取错误详情
        
        Args:
            output: 输出内容
            
        Returns:
            错误详情列表
        """
        details = []
        
        # 标准错误格式
        error_patterns = [
            r"Error[：:]\s*(.+)",
            r"错误[：:]\s*(.+)",
            r"FAILED[：:]\s*(.+)",
            r"Exception[：:]\s*(.+)",
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            for match in matches:
                text = match.strip()
                if len(text) > 5 and len(text) < 200:  # 过滤太短或太长的
                    details.append(text)
        
        return details[:5]  # 最多5条

    def _extract_failed_tests(self, output: str) -> List[str]:
        """
        提取失败的测试用例名称
        
        Args:
            output: 输出内容
            
        Returns:
            失败测试列表
        """
        failed = []
        
        # pytest 风格: FAILED test_file.py::test_name
        pytest_failed = re.findall(r"FAILED\s+([\w/]+\.py::\w+)", output)
        failed.extend(pytest_failed)
        
        # Jest 风格: ✕ test name
        jest_failed = re.findall(r"✕\s+(.+)", output)
        failed.extend(jest_failed)
        
        # 通用: FAIL test_name
        generic_failed = re.findall(r"FAIL[ED]?\s*[：:]?\s*(\w+)", output, re.IGNORECASE)
        failed.extend(generic_failed)
        
        return failed[:5]  # 最多5条

    def _extract_exceptions(self, output: str) -> List[str]:
        """
        提取异常类型和消息
        
        Args:
            output: 输出内容
            
        Returns:
            异常列表
        """
        exceptions = []
        
        # Python 异常
        python_exc = re.findall(
            r"(\w+Error|\w+Exception)[：:]\s*(.+)",
            output
        )
        for exc_type, message in python_exc:
            exceptions.append(f"{exc_type}: {message.strip()[:100]}")
        
        # JavaScript 异常
        js_exc = re.findall(
            r"(TypeError|ReferenceError|SyntaxError|Error)[：:]\s*(.+)",
            output
        )
        for exc_type, message in js_exc:
            exceptions.append(f"{exc_type}: {message.strip()[:100]}")
        
        return exceptions[:3]  # 最多3条

    def _make_verdict(
        self,
        evidence: List[str],
        counter_evidence: List[str],
        criteria_results: dict | None = None,
    ) -> tuple:
        """
        综合判断验证结果
        
        Args:
            evidence: 正面证据
            counter_evidence: 反面证据
            criteria_results: 成功标准检查结果
            
        Returns:
            (verdict, confidence) 元组
        """
        # 考虑成功标准通过率
        criteria_weight = 0
        if criteria_results and criteria_results["total"] > 0:
            criteria_weight = criteria_results["pass_rate"]
        
        # 计算证据权重
        total = len(evidence) + len(counter_evidence)
        if total == 0 and criteria_results is None:
            return ValidationVerdict.INCONCLUSIVE, 0.0
        
        if total == 0:
            # 仅基于成功标准
            if criteria_weight >= 0.8:
                return ValidationVerdict.VALIDATED, criteria_weight
            elif criteria_weight <= 0.2:
                return ValidationVerdict.REFUTED, 1 - criteria_weight
            else:
                return ValidationVerdict.INCONCLUSIVE, criteria_weight
        
        # 综合判断
        positive_ratio = len(evidence) / total
        
        # 结合成功标准
        if criteria_results and criteria_results["total"] > 0:
            # 成功标准权重更高
            combined = positive_ratio * 0.4 + criteria_weight * 0.6
        else:
            combined = positive_ratio
        
        confidence = combined
        
        if confidence >= 0.8:
            return ValidationVerdict.VALIDATED, confidence
        elif confidence <= 0.2:
            return ValidationVerdict.REFUTED, confidence
        else:
            # 如果有需要更多信息的情况
            if criteria_results and 0 < criteria_results["pass_rate"] < 0.5:
                return ValidationVerdict.NEEDS_MORE_INFO, confidence
            return ValidationVerdict.INCONCLUSIVE, confidence

    def _verdict_to_state(self, verdict: ValidationVerdict) -> str:
        """将验证结果转换为假设状态"""
        mapping = {
            ValidationVerdict.VALIDATED: "validated",
            ValidationVerdict.REFUTED: "refuted",
            ValidationVerdict.INCONCLUSIVE: "inconclusive",
            ValidationVerdict.NEEDS_MORE_INFO: "pending",
        }
        return mapping.get(verdict, "pending")

    def _generate_reasoning(
        self,
        verdict: ValidationVerdict,
        evidence: List[str],
        counter_evidence: List[str],
    ) -> str:
        """生成推理过程"""
        parts = []
        
        if evidence:
            parts.append(f"正面证据 {len(evidence)} 条")
        if counter_evidence:
            parts.append(f"反面证据 {len(counter_evidence)} 条")
        
        evidence_desc = "、".join(parts) if parts else "无明显证据"
        
        verdict_desc = {
            ValidationVerdict.VALIDATED: "假设得到验证",
            ValidationVerdict.REFUTED: "假设被反驳",
            ValidationVerdict.INCONCLUSIVE: "结论不明确",
            ValidationVerdict.NEEDS_MORE_INFO: "需要更多信息",
        }
        
        return f"{evidence_desc}，{verdict_desc.get(verdict, '状态未知')}"

    def _generate_next_steps(
        self,
        verdict: ValidationVerdict,
        evidence: List[str],
        counter_evidence: List[str],
        hypothesis: dict | None = None,
    ) -> List[str]:
        """
        根据验证结果生成下一步建议
        
        Args:
            verdict: 验证结论
            evidence: 正面证据
            counter_evidence: 反面证据
            hypothesis: 相关假设
            
        Returns:
            建议列表
        """
        steps = []
        
        if verdict == ValidationVerdict.VALIDATED:
            steps.append("✓ 假设已验证，可以继续推进相关任务")
            steps.append("建议：记录验证结果，更新假设状态为 validated")
            if hypothesis:
                steps.append(f"建议：基于「{hypothesis.get('statement', '该假设')}」继续下一步工作")
        
        elif verdict == ValidationVerdict.REFUTED:
            steps.append("✗ 假设被反驳，需要调整方向")
            # 根据反面证据给出具体建议
            if any("exit_code" in e for e in counter_evidence):
                steps.append("建议：检查执行环境配置和依赖项")
            if any("测试失败" in e or "FAILED" in e for e in counter_evidence):
                steps.append("建议：检查失败的测试用例，修复相关问题")
            if any("错误" in e for e in counter_evidence):
                steps.append("建议：根据错误信息定位问题根源")
            if hypothesis:
                steps.append(f"建议：重新评估「{hypothesis.get('statement', '该假设')}」的正确性")
        
        elif verdict == ValidationVerdict.NEEDS_MORE_INFO:
            steps.append("? 需要更多信息才能确定假设状态")
            steps.append("建议：增加测试覆盖率或收集更多执行数据")
            steps.append("建议：检查是否遗漏关键验证步骤")
            if hypothesis:
                criteria = hypothesis.get("success_criteria", [])
                if criteria:
                    steps.append(f"建议：针对成功标准「{criteria[0] if criteria else ''}」补充验证")
        
        else:  # INCONCLUSIVE
            steps.append("? 验证结果不明确")
            steps.append("建议：增加验证维度或调整验证方法")
            steps.append("建议：检查是否存在环境干扰因素")
            if len(evidence) == len(counter_evidence) and len(evidence) > 0:
                steps.append("建议：正反证据相当，考虑增加判定条件")
        
        return steps

    def _load_success_patterns(self) -> List[dict]:
        """加载成功模式"""
        return [
            {"match": lambda s, e: "success" in s.lower(), "description": "发现成功关键词"},
            {"match": lambda s, e: "完成" in s, "description": "操作完成"},
            {"match": lambda s, e: "passed" in s.lower(), "description": "测试通过"},
            {"match": lambda s, e: "ok" in s.lower() and "not ok" not in s.lower(), "description": "状态OK"},
            {"match": lambda s, e: "done" in s.lower(), "description": "任务完成"},
        ]

    def _load_failure_patterns(self) -> List[dict]:
        """加载失败模式"""
        return [
            {"match": lambda s, e: "error" in e.lower(), "description": "发现错误输出"},
            {"match": lambda s, e: "failed" in s.lower(), "description": "操作失败"},
            {"match": lambda s, e: "exception" in e.lower(), "description": "发现异常"},
            {"match": lambda s, e: "fatal" in s.lower() or "fatal" in e.lower(), "description": "致命错误"},
            {"match": lambda s, e: "timeout" in s.lower() or "timeout" in e.lower(), "description": "执行超时"},
        ]
