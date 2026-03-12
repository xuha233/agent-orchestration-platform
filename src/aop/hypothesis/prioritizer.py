"""
HypothesisPrioritizer - 假设优先级自动排序器

基于多维度评估自动排序假设，帮助创业者识别最值得优先验证的假设。

核心维度：
1. 影响力 (Impact) - 如果假设为真，对产品成功的影响程度
2. 验证成本 (Cost) - 验证这个假设需要的时间/金钱
3. 不确定性 (Uncertainty) - 当前对这个假设的信心程度

优先级公式：
priority = (impact * 10 - cost * 5 - uncertainty * 3) / 10
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ImpactLevel(Enum):
    """影响等级"""
    CRITICAL = 10
    HIGH = 8
    MEDIUM = 5
    LOW = 3


class CostLevel(Enum):
    """验证成本等级"""
    VERY_LOW = 1
    LOW = 3
    MEDIUM = 5
    HIGH = 7
    VERY_HIGH = 10


class UncertaintyLevel(Enum):
    """不确定性等级"""
    VERY_LOW = 1
    LOW = 3
    MEDIUM = 5
    HIGH = 7
    VERY_HIGH = 10


@dataclass
class PrioritizerConfig:
    """排序器配置"""
    impact_weight: float = 10.0
    cost_weight: float = 5.0
    uncertainty_weight: float = 3.0
    min_score: float = 0.0
    max_score: float = 10.0
    boost_uncertain: bool = True
    uncertainty_boost_factor: float = 0.3


@dataclass
class HypothesisScore:
    """假设评分结果"""
    hypothesis_id: str
    statement: str
    impact_score: float
    cost_score: float
    uncertainty_score: float
    priority_score: float
    reasoning: str
    rank: int = 0
    raw_hypothesis: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "statement": self.statement,
            "impact_score": self.impact_score,
            "cost_score": self.cost_score,
            "uncertainty_score": self.uncertainty_score,
            "priority_score": self.priority_score,
            "reasoning": self.reasoning,
            "rank": self.rank,
        }


class HypothesisPrioritizer:
    """假设优先级自动排序器"""
    
    def __init__(self, config: Optional[PrioritizerConfig] = None):
        self.config = config or PrioritizerConfig()
    
    def prioritize(
        self,
        hypotheses: List[Dict],
        context: Optional[Dict] = None
    ) -> List[HypothesisScore]:
        if not hypotheses:
            return []
        
        scores = []
        for h in hypotheses:
            score = self.score_hypothesis(h, context)
            scores.append(score)
        
        scores.sort(key=lambda s: s.priority_score, reverse=True)
        
        for i, score in enumerate(scores):
            score.rank = i + 1
        
        return scores
    
    def score_hypothesis(
        self,
        hypothesis: Dict,
        context: Optional[Dict] = None
    ) -> HypothesisScore:
        hypothesis_id = hypothesis.get("hypothesis_id", hypothesis.get("id", "unknown"))
        statement = hypothesis.get("statement", hypothesis.get("description", ""))
        
        impact_score = self._evaluate_impact(hypothesis, context)
        cost_score = self._evaluate_cost(hypothesis, context)
        uncertainty_score = self._evaluate_uncertainty(hypothesis, context)
        
        priority_score = self._calculate_priority(
            impact_score, cost_score, uncertainty_score
        )
        
        reasoning = self._generate_reasoning(
            impact_score, cost_score, uncertainty_score, priority_score
        )
        
        return HypothesisScore(
            hypothesis_id=hypothesis_id,
            statement=statement,
            impact_score=impact_score,
            cost_score=cost_score,
            uncertainty_score=uncertainty_score,
            priority_score=priority_score,
            reasoning=reasoning,
            raw_hypothesis=hypothesis,
        )
    
    def get_ranking_explanation(self, scores: List[HypothesisScore]) -> str:
        if not scores:
            return "没有假设需要排序。"
        
        lines = [
            "# 假设优先级排序结果",
            "",
            f"共 {len(scores)} 个假设，按优先级从高到低排列：",
        ]
        
        for score in scores:
            lines.extend([
                "",
                f"## #{score.rank}: {score.hypothesis_id}",
                f"**陈述**: {score.statement}",
                f"**优先级分数**: {score.priority_score:.2f}",
                f"**各维度分数**:",
                f"  - 影响力: {score.impact_score:.1f}/10",
                f"  - 验证成本: {score.cost_score:.1f}/10 (越高越贵)",
                f"  - 不确定性: {score.uncertainty_score:.1f}/10",
                f"**理由**: {score.reasoning}",
            ])
        
        lines.extend([
            "",
            "---",
            "",
            "### 排序逻辑说明",
            "",
            "优先级公式: priority = (impact × 10 - cost × 5 - uncertainty × 3) / 10",
            "- 影响↑ → 优先级↑",
            "- 成本↑ → 优先级↓",
            "- 不确定性↑ → 优先级↓（但高不确定性假设更值得验证）",
            "",
            "建议：优先验证高影响、低成本、高不确定性的假设。",
        ])
        
        return "\n".join(lines)
    
    def _evaluate_impact(
        self,
        hypothesis: Dict,
        context: Optional[Dict] = None
    ) -> float:
        if "impact" in hypothesis:
            impact = hypothesis["impact"]
            if isinstance(impact, (int, float)):
                return self._clamp_score(impact)
            if isinstance(impact, str):
                return self._parse_impact_level(impact)
        
        h_type = hypothesis.get("type", hypothesis.get("hypothesis_type", "technical"))
        if isinstance(h_type, str):
            type_impact = {
                "business": 9.0,
                "architectural": 8.0,
                "security": 7.0,
                "technical": 6.0,
                "performance": 5.0,
                "usability": 4.0,
            }
            base_score = type_impact.get(h_type.lower(), 5.0)
        else:
            base_score = 5.0
        
        statement = hypothesis.get("statement", "").lower()
        high_impact_keywords = [
            "核心", "关键", "必须", "决定", "成功", "失败", "生死",
            "revenue", "core", "critical", "essential", "must"
        ]
        low_impact_keywords = [
            "优化", "改进", "增强", "可选", "锦上添花",
            "optimize", "improve", "enhance", "optional", "nice to have"
        ]
        
        for keyword in high_impact_keywords:
            if keyword in statement:
                base_score = min(10.0, base_score + 1.5)
                break
        
        for keyword in low_impact_keywords:
            if keyword in statement:
                base_score = max(1.0, base_score - 1.0)
                break
        
        return self._clamp_score(base_score)
    
    def _evaluate_cost(
        self,
        hypothesis: Dict,
        context: Optional[Dict] = None
    ) -> float:
        if "cost" in hypothesis:
            cost = hypothesis["cost"]
            if isinstance(cost, (int, float)):
                return self._clamp_score(cost)
            if isinstance(cost, str):
                return self._parse_cost_level(cost)
        
        effort = hypothesis.get("estimated_effort", hypothesis.get("effort", ""))
        if effort:
            if isinstance(effort, (int, float)):
                if effort <= 1:
                    return CostLevel.VERY_LOW.value
                elif effort <= 2:
                    return CostLevel.LOW.value
                elif effort <= 5:
                    return CostLevel.MEDIUM.value
                elif effort <= 14:
                    return CostLevel.HIGH.value
                else:
                    return CostLevel.VERY_HIGH.value
            
            effort_str = str(effort).lower()
            if any(k in effort_str for k in ["小时", "分钟", "hour", "min", "即时", "立即"]):
                return CostLevel.VERY_LOW.value
            if any(k in effort_str for k in ["天", "day", "1-2"]):
                return CostLevel.LOW.value
            if any(k in effort_str for k in ["周", "week", "3-5"]):
                return CostLevel.MEDIUM.value
            if any(k in effort_str for k in ["月", "month", "复杂"]):
                return CostLevel.HIGH.value
        
        validation_method = hypothesis.get("validation_method", "").lower()
        method_cost = {
            "落地页": CostLevel.LOW.value,
            "landing page": CostLevel.LOW.value,
            "问卷": CostLevel.VERY_LOW.value,
            "survey": CostLevel.VERY_LOW.value,
            "访谈": CostLevel.LOW.value,
            "interview": CostLevel.LOW.value,
            "原型": CostLevel.MEDIUM.value,
            "prototype": CostLevel.MEDIUM.value,
            "mvp": CostLevel.MEDIUM.value,
            "礼宾": CostLevel.LOW.value,
            "concierge": CostLevel.LOW.value,
        }
        
        base_score = CostLevel.MEDIUM.value
        for method, cost in method_cost.items():
            if method in validation_method:
                base_score = cost
                break
        
        dependencies = hypothesis.get("dependencies", [])
        if dependencies:
            base_score = min(10.0, base_score + len(dependencies) * 0.5)
        
        return self._clamp_score(base_score)
    
    def _evaluate_uncertainty(
        self,
        hypothesis: Dict,
        context: Optional[Dict] = None
    ) -> float:
        if "uncertainty" in hypothesis:
            uncertainty = hypothesis["uncertainty"]
            if isinstance(uncertainty, (int, float)):
                return self._clamp_score(uncertainty)
            if isinstance(uncertainty, str):
                return self._parse_uncertainty_level(uncertainty)
        
        risk = hypothesis.get("risk_level", hypothesis.get("risk", "medium"))
        if isinstance(risk, str):
            risk_uncertainty = {
                "low": UncertaintyLevel.LOW.value,
                "medium": UncertaintyLevel.MEDIUM.value,
                "high": UncertaintyLevel.HIGH.value,
            }
            base_score = risk_uncertainty.get(risk.lower(), UncertaintyLevel.MEDIUM.value)
        else:
            base_score = UncertaintyLevel.MEDIUM.value
        
        return self._clamp_score(base_score)
    
    def _calculate_priority(
        self,
        impact: float,
        cost: float,
        uncertainty: float
    ) -> float:
        cfg = self.config
        
        priority = (
            impact * cfg.impact_weight
            - cost * cfg.cost_weight
            - uncertainty * cfg.uncertainty_weight
        ) / 10.0
        
        if cfg.boost_uncertain and uncertainty >= UncertaintyLevel.HIGH.value:
            boost = uncertainty * cfg.uncertainty_boost_factor
            priority += boost
        
        return self._clamp_score(priority, cfg.min_score, cfg.max_score)
    
    def _generate_reasoning(
        self,
        impact: float,
        cost: float,
        uncertainty: float,
        priority: float
    ) -> str:
        reasons = []
        
        if impact >= ImpactLevel.HIGH.value:
            reasons.append(f"影响力高({impact:.1f})，对产品成功至关重要")
        elif impact >= ImpactLevel.MEDIUM.value:
            reasons.append(f"影响力中等({impact:.1f})，值得验证")
        else:
            reasons.append(f"影响力较低({impact:.1f})，优先级可降低")
        
        if cost <= CostLevel.LOW.value:
            reasons.append(f"验证成本低({cost:.1f})，快速验证")
        elif cost >= CostLevel.HIGH.value:
            reasons.append(f"验证成本高({cost:.1f})，需权衡投入产出")
        
        if uncertainty >= UncertaintyLevel.HIGH.value:
            reasons.append(f"不确定性高({uncertainty:.1f})，建议优先验证以降低风险")
        elif uncertainty <= UncertaintyLevel.LOW.value:
            reasons.append(f"不确定性低({uncertainty:.1f})，验证优先级可降低")
        
        return "；".join(reasons)
    
    def _parse_impact_level(self, value: str) -> float:
        mapping = {
            "critical": ImpactLevel.CRITICAL.value,
            "关键": ImpactLevel.CRITICAL.value,
            "high": ImpactLevel.HIGH.value,
            "高": ImpactLevel.HIGH.value,
            "medium": ImpactLevel.MEDIUM.value,
            "中": ImpactLevel.MEDIUM.value,
            "中等": ImpactLevel.MEDIUM.value,
            "low": ImpactLevel.LOW.value,
            "低": ImpactLevel.LOW.value,
        }
        return mapping.get(value.lower(), ImpactLevel.MEDIUM.value)
    
    def _parse_cost_level(self, value: str) -> float:
        mapping = {
            "very_low": CostLevel.VERY_LOW.value,
            "极低": CostLevel.VERY_LOW.value,
            "low": CostLevel.LOW.value,
            "低": CostLevel.LOW.value,
            "medium": CostLevel.MEDIUM.value,
            "中": CostLevel.MEDIUM.value,
            "中等": CostLevel.MEDIUM.value,
            "high": CostLevel.HIGH.value,
            "高": CostLevel.HIGH.value,
            "very_high": CostLevel.VERY_HIGH.value,
            "极高": CostLevel.VERY_HIGH.value,
        }
        return mapping.get(value.lower(), CostLevel.MEDIUM.value)
    
    def _parse_uncertainty_level(self, value: str) -> float:
        mapping = {
            "very_low": UncertaintyLevel.VERY_LOW.value,
            "极低": UncertaintyLevel.VERY_LOW.value,
            "low": UncertaintyLevel.LOW.value,
            "低": UncertaintyLevel.LOW.value,
            "medium": UncertaintyLevel.MEDIUM.value,
            "中": UncertaintyLevel.MEDIUM.value,
            "中等": UncertaintyLevel.MEDIUM.value,
            "high": UncertaintyLevel.HIGH.value,
            "高": UncertaintyLevel.HIGH.value,
            "very_high": UncertaintyLevel.VERY_HIGH.value,
            "极高": UncertaintyLevel.VERY_HIGH.value,
        }
        return mapping.get(value.lower(), UncertaintyLevel.MEDIUM.value)
    
    def _clamp_score(
        self,
        score: float,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None
    ) -> float:
        min_val = min_val if min_val is not None else self.config.min_score
        max_val = max_val if max_val is not None else self.config.max_score
        return max(min_val, min(max_val, score))
