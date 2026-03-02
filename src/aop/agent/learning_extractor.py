"""
LearningExtractor - 学习提取器

从执行日志中自动提取学习经验。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any
import re

from .types import ExtractedLearning


class LearningExtractor:
    """
    学习提取器

    从执行日志中自动提取学习经验。

    提取策略:
    1. 错误模式识别 - 识别常见错误并分类
    2. 成功模式识别 - 识别成功的关键因素
    3. 时间序列分析 - 分析执行时间模式
    4. 跨Provider对比 - 对比不同Provider的表现
    """

    def __init__(self):
        self.known_error_patterns = self._load_error_patterns()
        self.known_success_patterns = self._load_success_patterns()

    def extract(self, execution_results: List[dict]) -> List[ExtractedLearning]:
        """
        从执行结果中提取学习

        Args:
            execution_results: 执行结果列表

        Returns:
            提取的学习列表
        """
        learnings = []

        # 按阶段分组
        phase_results = self._group_by_phase(execution_results)

        for phase, results in phase_results.items():
            learning = self._extract_from_phase(phase, results)
            learnings.append(learning)

        return learnings

    def _group_by_phase(self, results: List[dict]) -> Dict[str, List[dict]]:
        """按阶段分组结果"""
        phases = {}

        for result in results:
            phase = self._infer_phase(result)
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(result)

        return phases

    def _infer_phase(self, result: dict) -> str:
        """推断执行阶段"""
        stdout = str(result).lower()

        if any(kw in stdout for kw in ["setup", "init", "install", "配置"]):
            return "setup"
        elif any(kw in stdout for kw in ["test", "测试", "spec"]):
            return "test"
        elif any(kw in stdout for kw in ["build", "构建", "compile"]):
            return "build"
        elif any(kw in stdout for kw in ["deploy", "部署", "release"]):
            return "deploy"
        else:
            return "development"

    def _extract_from_phase(self, phase: str, results: List[dict]) -> ExtractedLearning:
        """从单个阶段提取学习"""
        what_worked = []
        what_failed = []
        insights = []

        for result in results:
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            exit_code = result.get("exit_code", 0)
            provider = result.get("provider", "unknown")

            # 提取成功经验
            if exit_code == 0:
                worked = self._extract_success_patterns(stdout, stderr, provider)
                what_worked.extend(worked)

            # 提取失败经验
            if exit_code != 0 or stderr:
                failed = self._extract_failure_patterns(stdout, stderr, provider)
                what_failed.extend(failed)

        # 去重
        what_worked = list(set(what_worked))
        what_failed = list(set(what_failed))

        return ExtractedLearning(
            phase=phase,
            what_worked=what_worked,
            what_failed=what_failed,
            insights=insights,
            patterns=[],
            confidence=self._calculate_confidence(results),
        )

    def _extract_success_patterns(self, stdout: str, stderr: str, provider: str) -> List[str]:
        """提取成功模式"""
        patterns = []

        if "success" in stdout.lower() or "成功" in stdout:
            patterns.append(f"[{provider}] 操作成功")

        if "done" in stdout.lower() or "完成" in stdout:
            patterns.append(f"[{provider}] 任务完成")

        return patterns

    def _extract_failure_patterns(self, stdout: str, stderr: str, provider: str) -> List[str]:
        """提取失败模式"""
        patterns = []

        if "error" in stderr.lower():
            patterns.append(f"[{provider}] 发现错误")

        if "failed" in stdout.lower():
            patterns.append(f"[{provider}] 操作失败")

        return patterns

    def _calculate_confidence(self, results: List[dict]) -> float:
        """计算学习置信度"""
        if not results:
            return 0.0

        success_count = sum(1 for r in results if r.get("exit_code", -1) == 0)
        return min(1.0, len(results) / 5 * (success_count / len(results) if results else 0))

    def _load_error_patterns(self) -> List[dict]:
        """加载已知错误模式"""
        return [
            {"match": lambda s, e: "permission denied" in e.lower(), "description": "权限问题"},
            {"match": lambda s, e: "module not found" in e.lower(), "description": "模块未找到"},
            {"match": lambda s, e: "network" in e.lower(), "description": "网络错误"},
        ]

    def _load_success_patterns(self) -> List[dict]:
        """加载已知成功模式"""
        return [
            {"match": lambda s, e: "successfully" in s.lower(), "description": "操作成功"},
            {"match": lambda s, e: "done" in s.lower(), "description": "任务完成"},
        ]
