"""
LearningExtractor - 学习提取器

从执行日志中自动提取学习经验。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Any
import re

from .types import ExtractedLearning


@dataclass
class PhaseRelation:
    """阶段关联信息"""
    from_phase: str
    to_phase: str
    correlation_type: str  # "sequential", "dependency", "conflict"
    confidence: float
    evidence: List[str] = field(default_factory=list)


@dataclass
class PatternStats:
    """模式统计"""
    pattern: str
    count: int
    success_rate: float
    phases: List[str] = field(default_factory=list)


@dataclass
class PerformanceInsight:
    """性能洞察"""
    metric_type: str  # "duration", "memory", "tokens"
    phase: str
    value: float
    trend: str  # "improving", "degrading", "stable"
    recommendation: str | None = None


class LearningExtractor:
    """
    学习提取器

    从执行日志中自动提取学习经验。

    提取策略:
    1. 错误模式识别 - 识别常见错误并分类
    2. 成功模式识别 - 识别成功的关键因素
    3. 时间序列分析 - 分析执行时间模式
    4. 跨Provider对比 - 对比不同Provider的表现
    5. 跨阶段关联分析 - 分析不同阶段之间的依赖和影响
    """

    def __init__(self):
        self.known_error_patterns = self._load_error_patterns()
        self.known_success_patterns = self._load_success_patterns()
        self._pattern_stats: Dict[str, PatternStats] = {}
        self._phase_relations: List[PhaseRelation] = []

    def extract(self, execution_results: List[dict]) -> List[ExtractedLearning]:
        """
        从执行结果中提取学习

        Args:
            execution_results: 执行结果列表

        Returns:
            提取的学习列表
        """
        if not execution_results:
            return []

        learnings: List[ExtractedLearning] = []

        # 按阶段分组
        phase_results = self._group_by_phase(execution_results)

        # 识别模式并统计
        all_patterns = self._identify_patterns(execution_results)

        # 提取洞察
        all_insights = self._extract_insights(execution_results)

        for phase, results in phase_results.items():
            learning = self._extract_from_phase(phase, results)
            # 添加该阶段相关的模式和洞察
            learning.patterns = [p.pattern for p in all_patterns if phase in p.phases]
            learning.insights = [
                i.recommendation for i in all_insights
                if i.recommendation and i.phase == phase
            ]
            learnings.append(learning)

        # 跨阶段学习
        cross_phase_learning = self._extract_cross_phase_learning(execution_results, phase_results)
        if cross_phase_learning:
            learnings.append(cross_phase_learning)

        return learnings

    def _group_by_phase(self, results: List[dict]) -> Dict[str, List[dict]]:
        """按阶段分组结果"""
        phases: Dict[str, List[dict]] = {}

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
        what_worked: List[str] = []
        what_failed: List[str] = []
        insights: List[str] = []

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
        patterns: List[str] = []

        if "success" in stdout.lower() or "成功" in stdout:
            patterns.append(f"[{provider}] 操作成功")

        if "done" in stdout.lower() or "完成" in stdout:
            patterns.append(f"[{provider}] 任务完成")

        # 使用已知成功模式进行匹配
        for pattern_info in self.known_success_patterns:
            try:
                if pattern_info["match"](stdout, stderr):
                    patterns.append(f"[{provider}] {pattern_info['description']}")
            except Exception:
                pass

        return patterns

    def _extract_failure_patterns(self, stdout: str, stderr: str, provider: str) -> List[str]:
        """提取失败模式"""
        patterns: List[str] = []

        if "error" in stderr.lower():
            patterns.append(f"[{provider}] 发现错误")

        if "failed" in stdout.lower():
            patterns.append(f"[{provider}] 操作失败")

        # 使用已知错误模式进行匹配
        for pattern_info in self.known_error_patterns:
            try:
                if pattern_info["match"](stdout, stderr):
                    patterns.append(f"[{provider}] {pattern_info['description']}")
            except Exception:
                pass

        return patterns

    # ========== 增强方法 ==========

    def _identify_patterns(self, results: List[dict]) -> List[PatternStats]:
        """
        识别模式并统计频率

        分析成功/失败模式的出现频率和成功率
        """
        pattern_data: Dict[str, Dict[str, Any]] = {}
        phase_results = self._group_by_phase(results)

        for phase, phase_items in phase_results.items():
            for result in phase_items:
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                exit_code = result.get("exit_code", 0)
                provider = result.get("provider", "unknown")

                # 提取当前结果的所有模式
                if exit_code == 0:
                    found_patterns = self._extract_success_patterns(stdout, stderr, provider)
                else:
                    found_patterns = self._extract_failure_patterns(stdout, stderr, provider)

                for pattern in found_patterns:
                    if pattern not in pattern_data:
                        pattern_data[pattern] = {
                            "count": 0,
                            "success_count": 0,
                            "phases": set(),
                        }
                    pattern_data[pattern]["count"] += 1
                    pattern_data[pattern]["phases"].add(phase)
                    if exit_code == 0:
                        pattern_data[pattern]["success_count"] += 1

        # 构建统计结果
        pattern_stats: List[PatternStats] = []
        for pattern, data in pattern_data.items():
            success_rate = data["success_count"] / data["count"] if data["count"] > 0 else 0.0
            stats = PatternStats(
                pattern=pattern,
                count=data["count"],
                success_rate=success_rate,
                phases=list(data["phases"]),
            )
            pattern_stats.append(stats)
            self._pattern_stats[pattern] = stats

        # 按出现次数排序
        pattern_stats.sort(key=lambda x: x.count, reverse=True)
        return pattern_stats

    def _extract_insights(self, results: List[dict]) -> List[PerformanceInsight]:
        """
        提取性能、资源、依赖洞察

        从执行结果中提取有价值的洞察信息
        """
        insights: List[PerformanceInsight] = []
        phase_results = self._group_by_phase(results)

        for phase, phase_items in phase_results.items():
            # 性能洞察 - 执行时间分析
            durations = self._extract_durations(phase_items)
            if durations:
                avg_duration = sum(durations) / len(durations)
                trend = self._analyze_trend(durations)
                recommendation = self._generate_duration_recommendation(phase, avg_duration, trend)

                insights.append(PerformanceInsight(
                    metric_type="duration",
                    phase=phase,
                    value=avg_duration,
                    trend=trend,
                    recommendation=recommendation,
                ))

            # Token 使用分析
            tokens = [r.get("tokens_used", 0) for r in phase_items if r.get("tokens_used")]
            if tokens:
                avg_tokens = sum(tokens) / len(tokens)
                token_trend = self._analyze_trend(tokens)
                token_rec = self._generate_token_recommendation(phase, avg_tokens, token_trend)

                insights.append(PerformanceInsight(
                    metric_type="tokens",
                    phase=phase,
                    value=avg_tokens,
                    trend=token_trend,
                    recommendation=token_rec,
                ))

            # 资源/依赖洞察 - 错误分析
            dependency_issues = self._extract_dependency_issues(phase_items)
            if dependency_issues:
                for issue in dependency_issues:
                    insights.append(PerformanceInsight(
                        metric_type="dependency",
                        phase=phase,
                        value=1.0,  # 存在问题标记
                        trend="stable",
                        recommendation=f"建议检查依赖: {issue}",
                    ))

        return insights

    def _extract_cross_phase_learning(
        self,
        all_results: List[dict],
        phase_results: Dict[str, List[dict]]
    ) -> ExtractedLearning | None:
        """
        提取跨阶段学习

        分析不同阶段之间的关联和依赖
        """
        if len(phase_results) < 2:
            return None

        phase_names = list(phase_results.keys())
        cross_insights: List[str] = []
        cross_patterns: List[str] = []
        what_worked: List[str] = []
        what_failed: List[str] = []

        # 分析阶段间的顺序依赖
        sequential_relations = self._analyze_sequential_relations(phase_results)
        for relation in sequential_relations:
            cross_patterns.append(
                f"阶段 '{relation.from_phase}' -> '{relation.to_phase}': {relation.correlation_type}"
            )
            if relation.correlation_type == "dependency":
                cross_insights.append(
                    f"{relation.from_phase} 阶段的成功影响 {relation.to_phase} 阶段"
                )

        # 分析错误传播
        error_propagation = self._analyze_error_propagation(phase_results)
        if error_propagation:
            for prop in error_propagation:
                what_failed.append(prop)
                cross_insights.append(f"检测到错误传播: {prop}")

        # 分析成功路径
        success_path = self._analyze_success_path(phase_results)
        if success_path:
            what_worked.append(success_path)
            cross_insights.append(f"成功路径: {success_path}")

        # 计算跨阶段置信度
        confidence = self._calculate_cross_phase_confidence(phase_results)

        return ExtractedLearning(
            phase="cross_phase",
            what_worked=what_worked,
            what_failed=what_failed,
            insights=cross_insights,
            patterns=cross_patterns,
            confidence=confidence,
        )

    def _calculate_confidence(self, results: List[dict]) -> float:
        """
        计算学习置信度（增强版）

        综合考虑多个因素：
        - 样本数量
        - 成功率
        - 模式一致性
        - 错误确定性
        """
        if not results:
            return 0.0

        total = len(results)
        success_count = sum(1 for r in results if r.get("exit_code", -1) == 0)
        failure_count = total - success_count

        # 基础置信度：基于样本量
        sample_confidence = min(1.0, total / 10.0)  # 10个样本达到最大值

        # 成功率置信度
        success_rate = success_count / total if total > 0 else 0.0
        success_confidence = success_rate if success_count >= failure_count else (1 - success_rate)

        # 模式一致性：检查是否有一致的成功/失败模式
        pattern_consistency = self._calculate_pattern_consistency(results)

        # 错误确定性：有明确错误信息时置信度更高
        error_certainty = self._calculate_error_certainty(results)

        # 综合置信度（加权平均）
        confidence = (
            sample_confidence * 0.2 +
            success_confidence * 0.3 +
            pattern_consistency * 0.3 +
            error_certainty * 0.2
        )

        return min(1.0, confidence)

    # ========== 辅助方法 ==========

    def _extract_durations(self, results: List[dict]) -> List[float]:
        """提取执行时间"""
        durations: List[float] = []
        for result in results:
            # 尝试从不同字段获取时间
            if "duration" in result:
                durations.append(float(result["duration"]))
            elif "elapsed_time" in result:
                durations.append(float(result["elapsed_time"]))
            elif "started_at" in result and "completed_at" in result:
                # 计算时间差（简化处理）
                try:
                    start = result["started_at"]
                    end = result["completed_at"]
                    # 假设是时间戳或可解析的字符串
                    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                        durations.append(abs(end - start))
                except Exception:
                    pass
        return durations

    def _analyze_trend(self, values: List[float]) -> str:
        """分析趋势"""
        if len(values) < 2:
            return "stable"

        # 简单趋势分析：比较前后两半的平均值
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(values[mid:]) / (len(values) - mid) if len(values) > mid else 0

        if second_half_avg < first_half_avg * 0.9:
            return "improving"
        elif second_half_avg > first_half_avg * 1.1:
            return "degrading"
        else:
            return "stable"

    def _generate_duration_recommendation(
        self,
        phase: str,
        avg_duration: float,
        trend: str
    ) -> str | None:
        """生成执行时间建议"""
        if trend == "degrading":
            return f"{phase} 阶段执行时间变长，建议检查是否有性能问题"
        elif trend == "improving":
            return f"{phase} 阶段执行效率提升，可以保持当前策略"
        return None

    def _generate_token_recommendation(
        self,
        phase: str,
        avg_tokens: float,
        trend: str
    ) -> str | None:
        """生成 Token 使用建议"""
        if avg_tokens > 10000:
            return f"{phase} 阶段 Token 消耗较高（平均 {avg_tokens:.0f}），考虑优化提示词"
        if trend == "degrading":
            return f"{phase} 阶段 Token 消耗增加，建议审查是否有冗余输出"
        return None

    def _extract_dependency_issues(self, results: List[dict]) -> List[str]:
        """提取依赖问题"""
        issues: List[str] = []
        dependency_keywords = [
            "module not found",
            "import error",
            "dependency",
            "no such file",
            "找不到模块",
            "依赖缺失",
        ]

        for result in results:
            stdout = result.get("stdout", "").lower()
            stderr = result.get("stderr", "").lower()
            combined = stdout + stderr

            for keyword in dependency_keywords:
                if keyword in combined:
                    # 尝试提取具体的依赖名称
                    match = re.search(r"['\"]?([\w\-\.]+)['\"]?\s*(not found|missing|error)", combined)
                    if match:
                        issues.append(match.group(1))
                    else:
                        issues.append(keyword)
                    break

        return list(set(issues))

    def _analyze_sequential_relations(
        self,
        phase_results: Dict[str, List[dict]]
    ) -> List[PhaseRelation]:
        """分析阶段间的顺序关系"""
        relations: List[PhaseRelation] = []
        phases = list(phase_results.keys())

        for i in range(len(phases) - 1):
            from_phase = phases[i]
            to_phase = phases[i + 1]

            from_results = phase_results[from_phase]
            to_results = phase_results[to_phase]

            # 计算相关性
            from_success = sum(1 for r in from_results if r.get("exit_code", -1) == 0)
            to_success = sum(1 for r in to_results if r.get("exit_code", -1) == 0)

            from_success_rate = from_success / len(from_results) if from_results else 0
            to_success_rate = to_success / len(to_results) if to_results else 0

            # 判断关联类型
            if from_success_rate > 0.8 and to_success_rate > 0.8:
                correlation_type = "sequential"
                confidence = 0.9
            elif from_success_rate > 0.7 and to_success_rate < 0.5:
                correlation_type = "dependency"
                confidence = 0.8
            elif from_success_rate < 0.3 and to_success_rate < 0.3:
                correlation_type = "conflict"
                confidence = 0.7
            else:
                correlation_type = "sequential"
                confidence = 0.5

            evidence = [
                f"{from_phase} 成功率: {from_success_rate:.1%}",
                f"{to_phase} 成功率: {to_success_rate:.1%}",
            ]

            relations.append(PhaseRelation(
                from_phase=from_phase,
                to_phase=to_phase,
                correlation_type=correlation_type,
                confidence=confidence,
                evidence=evidence,
            ))

        self._phase_relations = relations
        return relations

    def _analyze_error_propagation(
        self,
        phase_results: Dict[str, List[dict]]
    ) -> List[str]:
        """分析错误传播"""
        propagations: List[str] = []
        phases = list(phase_results.keys())

        for i in range(len(phases) - 1):
            current_phase = phases[i]
            next_phase = phases[i + 1]

            current_results = phase_results[current_phase]
            next_results = phase_results[next_phase]

            # 检查当前阶段失败后，下一阶段是否也失败
            current_errors = [
                r.get("stderr", "") or r.get("stdout", "")
                for r in current_results
                if r.get("exit_code", -1) != 0
            ]

            next_errors = [
                r.get("stderr", "") or r.get("stdout", "")
                for r in next_results
                if r.get("exit_code", -1) != 0
            ]

            if current_errors and next_errors:
                # 寻找相似的错误
                for ce in current_errors[:2]:
                    for ne in next_errors[:2]:
                        # 简单的相似性检查
                        common_words = set(ce.lower().split()) & set(ne.lower().split())
                        if len(common_words) > 3:
                            propagations.append(
                                f"错误从 {current_phase} 传播到 {next_phase}"
                            )
                            break

        return propagations

    def _analyze_success_path(
        self,
        phase_results: Dict[str, List[dict]]
    ) -> str | None:
        """分析成功路径"""
        successful_phases: List[str] = []

        for phase, results in phase_results.items():
            success_rate = sum(1 for r in results if r.get("exit_code", -1) == 0) / len(results)
            if success_rate > 0.8:
                successful_phases.append(phase)

        if successful_phases:
            return " -> ".join(successful_phases)

        return None

    def _calculate_cross_phase_confidence(
        self,
        phase_results: Dict[str, List[dict]]
    ) -> float:
        """计算跨阶段学习置信度"""
        if len(phase_results) < 2:
            return 0.0

        # 基于阶段数量和数据量
        total_results = sum(len(r) for r in phase_results.values())
        phase_count = len(phase_results)

        # 阶段覆盖率
        coverage = phase_count / 5.0  # 假设有5个主要阶段

        # 数据量置信度
        data_confidence = min(1.0, total_results / 20.0)

        # 关系确定性
        relation_confidence = 0.0
        if self._phase_relations:
            relation_confidence = sum(r.confidence for r in self._phase_relations) / len(self._phase_relations)

        return min(1.0, coverage * 0.3 + data_confidence * 0.4 + relation_confidence * 0.3)

    def _calculate_pattern_consistency(self, results: List[dict]) -> float:
        """计算模式一致性"""
        if not results:
            return 0.0

        # 统计成功和失败的分布
        success_count = sum(1 for r in results if r.get("exit_code", -1) == 0)
        failure_count = len(results) - success_count

        # 如果全部成功或全部失败，一致性高
        if success_count == 0 or failure_count == 0:
            return 1.0

        # 否则根据比例计算
        majority = max(success_count, failure_count)
        return majority / len(results)

    def _calculate_error_certainty(self, results: List[dict]) -> float:
        """计算错误确定性"""
        failures = [r for r in results if r.get("exit_code", -1) != 0]

        if not failures:
            return 1.0  # 没有失败，确定性高

        # 检查失败结果是否有明确的错误信息
        certain_failures = 0
        for r in failures:
            stderr = r.get("stderr", "")
            stdout = r.get("stdout", "")

            # 有明确的错误关键字
            error_keywords = ["error", "failed", "exception", "错误", "失败"]
            if any(kw in stderr.lower() or kw in stdout.lower() for kw in error_keywords):
                certain_failures += 1

        return certain_failures / len(failures) if failures else 0.0

    def _load_error_patterns(self) -> List[dict]:
        """加载已知错误模式"""
        return [
            {"match": lambda s, e: "permission denied" in e.lower(), "description": "权限问题"},
            {"match": lambda s, e: "module not found" in e.lower(), "description": "模块未找到"},
            {"match": lambda s, e: "network" in e.lower(), "description": "网络错误"},
            {"match": lambda s, e: "timeout" in e.lower(), "description": "超时错误"},
            {"match": lambda s, e: "memory" in e.lower(), "description": "内存不足"},
            {"match": lambda s, e: "syntax" in e.lower(), "description": "语法错误"},
        ]

    def _load_success_patterns(self) -> List[dict]:
        """加载已知成功模式"""
        return [
            {"match": lambda s, e: "successfully" in s.lower(), "description": "操作成功"},
            {"match": lambda s, e: "done" in s.lower(), "description": "任务完成"},
            {"match": lambda s, e: "passed" in s.lower(), "description": "测试通过"},
            {"match": lambda s, e: "built" in s.lower(), "description": "构建完成"},
        ]
