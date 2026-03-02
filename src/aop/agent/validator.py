"""
AutoValidator - 自动验证器

根据执行结果自动判断假设状态。
"""

from __future__ import annotations

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
        # 收集证据
        evidence = self._collect_evidence(execution_results)
        counter_evidence = self._collect_counter_evidence(execution_results)

        # 综合判断
        verdict, confidence = self._make_verdict(evidence, counter_evidence)

        # 确定状态
        state = self._verdict_to_state(verdict)

        return ValidationResult(
            hypothesis_id=hypothesis.get("hypothesis_id", ""),
            state=state,
            verdict=verdict,
            confidence=confidence,
            evidence=evidence,
            counter_evidence=counter_evidence,
            reasoning=self._generate_reasoning(verdict, evidence, counter_evidence),
        )

    def _collect_evidence(self, results: List[dict]) -> List[str]:
        """收集支持假设的证据"""
        evidence = []

        for result in results:
            stdout = result.get("stdout", "")
            exit_code = result.get("exit_code", 0)

            if exit_code == 0:
                evidence.append("执行成功退出")

            if "success" in stdout.lower() or "完成" in stdout:
                evidence.append("发现成功关键词")

        return evidence

    def _collect_counter_evidence(self, results: List[dict]) -> List[str]:
        """收集反对假设的证据"""
        counter_evidence = []

        for result in results:
            stderr = result.get("stderr", "")
            exit_code = result.get("exit_code", 0)

            if exit_code != 0:
                counter_evidence.append(f"进程异常退出，exit_code={exit_code}")

            if "error" in stderr.lower():
                counter_evidence.append("发现错误信息")

        return counter_evidence

    def _make_verdict(
        self,
        evidence: List[str],
        counter_evidence: List[str],
    ) -> tuple:
        """综合判断验证结果"""
        total = len(evidence) + len(counter_evidence)
        if total == 0:
            return ValidationVerdict.INCONCLUSIVE, 0.0

        positive_ratio = len(evidence) / total
        confidence = positive_ratio

        if confidence >= 0.8:
            return ValidationVerdict.VALIDATED, confidence
        elif confidence <= 0.2:
            return ValidationVerdict.REFUTED, confidence
        else:
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
        return f"基于 {len(evidence)} 条正面证据和 {len(counter_evidence)} 条反面证据，判断为 {verdict.value}"

    def _load_success_patterns(self) -> List[dict]:
        """加载成功模式"""
        return [
            {"match": lambda s, e: "success" in s.lower(), "description": "发现成功关键词"},
            {"match": lambda s, e: "完成" in s, "description": "操作完成"},
        ]

    def _load_failure_patterns(self) -> List[dict]:
        """加载失败模式"""
        return [
            {"match": lambda s, e: "error" in e.lower(), "description": "发现错误"},
            {"match": lambda s, e: "failed" in s.lower(), "description": "操作失败"},
        ]
