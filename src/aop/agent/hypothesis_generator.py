"""
HypothesisGenerator - 假设生成器

基于澄清后的需求，自动生成可验证的假设。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

from .types import GeneratedHypothesis, HypothesisType, ClarifiedRequirement


class HypothesisGenerator:
    """
    假设生成器

    基于澄清后的需求，自动生成可验证的假设。

    假设生成策略:
    1. 从需求中提取关键决策点
    2. 将决策点转化为可验证的假设
    3. 为每个假设设置验证方法和成功标准
    4. 识别假设之间的依赖关系
    5. 评估风险和工作量
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, requirement: ClarifiedRequirement) -> List[GeneratedHypothesis]:
        """
        生成假设列表

        Args:
            requirement: 澄清后的需求

        Returns:
            生成的假设列表
        """
        # 第一步：提取关键决策点
        decision_points = self._extract_decision_points(requirement)

        # 第二步：生成假设
        hypotheses = []
        for dp in decision_points:
            h = self._decision_to_hypothesis(dp, requirement)
            hypotheses.append(h)

        # 第三步：分析依赖关系
        hypotheses = self._analyze_dependencies(hypotheses)

        # 第四步：评估风险和工作量
        hypotheses = self._assess_risks_and_effort(hypotheses)

        return hypotheses

    def _extract_decision_points(self, requirement: ClarifiedRequirement) -> List[Dict[str, Any]]:
        """从需求中提取关键决策点"""
        # 简化实现
        return [
            {
                "description": "技术栈选择",
                "options": ["Next.js + Supabase", "Django + PostgreSQL", "Spring Boot + MySQL"],
                "risk": "medium",
                "impact": "全项目",
            },
            {
                "description": "认证方案",
                "options": ["JWT", "Session", "OAuth"],
                "risk": "high",
                "impact": "安全模块",
            },
        ]

    def _decision_to_hypothesis(
        self,
        decision_point: dict,
        requirement: ClarifiedRequirement,
    ) -> GeneratedHypothesis:
        """将决策点转换为假设"""
        return GeneratedHypothesis(
            statement=f"采用 {decision_point["options"][0]} 可以满足项目需求",
            hypothesis_type=HypothesisType.TECHNICAL,
            validation_method="构建原型并测试核心功能",
            success_criteria=["原型可运行", "核心功能正常", "性能达标"],
            priority="quick_win" if decision_point["risk"] == "low" else "deep_dive",
            estimated_effort="1-2天" if decision_point["risk"] == "low" else "3-5天",
            dependencies=[],
            risk_level=decision_point["risk"],
        )

    def _analyze_dependencies(self, hypotheses: List[GeneratedHypothesis]) -> List[GeneratedHypothesis]:
        """分析假设之间的依赖关系"""
        # 简化实现
        return hypotheses

    def _assess_risks_and_effort(self, hypotheses: List[GeneratedHypothesis]) -> List[GeneratedHypothesis]:
        """评估风险和工作量"""
        effort_map = {
            HypothesisType.TECHNICAL: "2-3天",
            HypothesisType.ARCHITECTURAL: "5-7天",
            HypothesisType.PERFORMANCE: "3-5天",
            HypothesisType.SECURITY: "4-6天",
            HypothesisType.USABILITY: "1-3天",
            HypothesisType.BUSINESS: "1-2天",
        }

        for h in hypotheses:
            if not h.estimated_effort:
                h.estimated_effort = effort_map.get(h.hypothesis_type, "3-5天")

        return hypotheses
