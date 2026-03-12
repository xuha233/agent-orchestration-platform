"""
反模式库

收集常见的创业错误和陷阱，帮助创业者避免犯错。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import KnowledgeBase, KnowledgeEntry


@dataclass
class AntiPattern(KnowledgeEntry):
    """反模式"""
    symptoms: List[str] = field(default_factory=list)  # 症状/表现
    causes: List[str] = field(default_factory=list)    # 原因
    consequences: List[str] = field(default_factory=list)  # 后果
    solutions: List[str] = field(default_factory=list)  # 解决方案
    severity: str = "medium"  # low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "symptoms": self.symptoms,
            "causes": self.causes,
            "consequences": self.consequences,
            "solutions": self.solutions,
            "severity": self.severity,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AntiPattern":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            symptoms=data.get("symptoms", []),
            causes=data.get("causes", []),
            consequences=data.get("consequences", []),
            solutions=data.get("solutions", []),
            severity=data.get("severity", "medium"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AntiPatternWarning:
    """反模式警告"""
    anti_pattern: AntiPattern
    matched_symptoms: List[str]
    matched_context: Dict[str, Any]
    risk_level: str
    recommendation: str


class AntiPatternLibrary(KnowledgeBase):
    """反模式库"""
    
    def __init__(self, storage_path: Optional[Path] = None, load_defaults: bool = True):
        super().__init__(storage_path)
        
        if load_defaults and not self._entries:
            self._load_default_antipatterns()
    
    def check_for_antipatterns(
        self,
        context: Dict[str, Any]
    ) -> List[AntiPatternWarning]:
        """
        检查上下文中是否存在反模式
        
        Args:
            context: 上下文信息，可能包含：
                - decisions: 已做的决策列表
                - behaviors: 当前行为描述
                - metrics: 当前指标
                - team_state: 团队状态
                - product_state: 产品状态
        
        Returns:
            检测到的反模式警告列表
        """
        warnings = []
        
        for entry in self._entries.values():
            if not isinstance(entry, AntiPattern):
                continue
            
            # 检查症状匹配
            matched_symptoms = self._match_symptoms(entry, context)
            
            if matched_symptoms:
                warning = AntiPatternWarning(
                    anti_pattern=entry,
                    matched_symptoms=matched_symptoms,
                    matched_context=context,
                    risk_level=self._calculate_risk(entry, matched_symptoms),
                    recommendation=self._generate_recommendation(entry, matched_symptoms),
                )
                warnings.append(warning)
        
        # 按风险等级排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        warnings.sort(key=lambda w: severity_order.get(w.risk_level, 99))
        
        return warnings
    
    def search(self, query: str, tags: Optional[List[str]] = None) -> List[KnowledgeEntry]:
        """搜索知识条目"""
        results = []
        query_lower = query.lower()
        
        for entry in self._entries.values():
            if not isinstance(entry, AntiPattern):
                continue
            
            if not self._tags_match(entry.tags, tags):
                continue
            
            text_fields = [
                entry.name,
                entry.description,
                " ".join(entry.symptoms),
                " ".join(entry.causes),
            ]
            
            if any(self._text_match(f, query_lower) for f in text_fields):
                results.append(entry)
        
        return results
    
    def suggest(self, context: Dict[str, Any]) -> List[KnowledgeEntry]:
        """根据上下文建议"""
        # 对于反模式，建议就是检测结果
        warnings = self.check_for_antipatterns(context)
        return [w.anti_pattern for w in warnings]
    
    def add_antipattern(self, antipattern: AntiPattern) -> None:
        """添加反模式"""
        self.add(antipattern)
    
    def _create_entry(self, data: Dict[str, Any]) -> Optional[KnowledgeEntry]:
        return AntiPattern.from_dict(data)
    
    def _match_symptoms(
        self,
        antipattern: AntiPattern,
        context: Dict[str, Any]
    ) -> List[str]:
        """匹配症状"""
        matched = []
        
        # 从决策中匹配
        decisions = context.get("decisions", [])
        for decision in decisions:
            decision_text = str(decision).lower()
            for symptom in antipattern.symptoms:
                symptom_lower = symptom.lower()
                if symptom_lower in decision_text:
                    matched.append(symptom)
        
        # 从行为中匹配
        behaviors = context.get("behaviors", [])
        for behavior in behaviors:
            behavior_text = str(behavior).lower()
            for symptom in antipattern.symptoms:
                symptom_lower = symptom.lower()
                if symptom_lower in behavior_text and symptom not in matched:
                    matched.append(symptom)
        
        # 从产品状态匹配
        product_state = context.get("product_state", {})
        for key, value in product_state.items():
            state_text = f"{key}: {value}".lower()
            for symptom in antipattern.symptoms:
                symptom_lower = symptom.lower()
                if symptom_lower in state_text and symptom not in matched:
                    matched.append(symptom)
        
        return matched
    
    def _calculate_risk(
        self,
        antipattern: AntiPattern,
        matched_symptoms: List[str]
    ) -> str:
        """计算风险等级"""
        base_severity = antipattern.severity
        match_ratio = len(matched_symptoms) / max(len(antipattern.symptoms), 1)
        
        if match_ratio >= 0.7:
            # 匹配度高于 70%，提升风险等级
            severity_upgrades = {"low": "medium", "medium": "high", "high": "critical"}
            return severity_upgrades.get(base_severity, base_severity)
        elif match_ratio >= 0.4:
            return base_severity
        else:
            # 匹配度低于 40%，降低风险等级
            severity_downgrades = {"critical": "high", "high": "medium", "medium": "low"}
            return severity_downgrades.get(base_severity, base_severity)
    
    def _generate_recommendation(
        self,
        antipattern: AntiPattern,
        matched_symptoms: List[str]
    ) -> str:
        """生成建议"""
        if not matched_symptoms:
            return f"检查是否存在: {antipattern.description}"
        
        symptom_text = "、".join(matched_symptoms[:3])
        solution = antipattern.solutions[0] if antipattern.solutions else "重新审视相关决策"
        
        return f"检测到 {symptom_text}。建议: {solution}"
    
    def _load_default_antipatterns(self) -> None:
        """加载默认反模式"""
        default_antipatterns = [
            AntiPattern(
                id="premature_optimization",
                name="过早优化",
                description="在验证核心价值前就投入大量时间优化性能、代码质量或架构。",
                symptoms=["花大量时间在非核心功能", "追求完美代码", "用户还没用上就在优化"],
                causes=["工程师思维", "害怕失败", "完美主义"],
                consequences=["浪费时间", "错过市场窗口", "可能优化错了东西"],
                solutions=["先验证核心假设", "设定优化阈值", "采用 YAGNI 原则"],
                severity="high",
                tags=["development", "priority", "technical-debt"],
            ),
            AntiPattern(
                id="feature_creep",
                name="功能蔓延",
                description="不断增加新功能，导致产品复杂度失控，核心价值被稀释。",
                symptoms=["功能列表越来越长", "用户反馈说要什么都加", "发布日期不断推迟"],
                causes=["缺乏产品愿景", "不敢拒绝用户", "竞争焦虑"],
                consequences=["产品臃肿", "用户体验差", "开发成本失控"],
                solutions=["坚守 MVP 范围", "建立功能评审机制", "用数据说话"],
                severity="high",
                tags=["product", "scope", "prioritization"],
            ),
            AntiPattern(
                id="solution_looking_for_problem",
                name="拿着锤子找钉子",
                description="先有技术方案，再去找问题。从技术出发而不是用户需求出发。",
                symptoms=["技术栈先定好了", "用户需求还没搞清楚", "经常说'这个技术很酷'"],
                causes=["技术驱动", "缺乏用户调研", "技术背景创业者"],
                consequences=["做出来没人用", "方向错误", "资源浪费"],
                solutions=["先做用户访谈", "问题优先于方案", "假设驱动"],
                severity="critical",
                tags=["strategy", "user-centric", "hypothesis-driven"],
            ),
            AntiPattern(
                id="build_without_validation",
                name="未验证就开发",
                description="没有验证假设就直接开始开发完整产品。",
                symptoms=["还没和用户聊过就开始写代码", "假设都没列出来", "相信自己的直觉"],
                causes=["过度自信", "急于求成", "缺乏方法论"],
                consequences=["做错了方向", "浪费大量时间", "可能失败收场"],
                solutions=["列出所有假设", "设计验证实验", "最小化开发"],
                severity="critical",
                tags=["validation", "hypothesis", "mvp"],
            ),
            AntiPattern(
                id="ignoring_metrics",
                name="忽视数据",
                description="不设定成功指标，也不跟踪数据，凭感觉判断。",
                symptoms=["没有明确的目标指标", "不做数据埋点", "凭感觉做决策"],
                causes=["不懂数据分析", "懒惰", "害怕面对真相"],
                consequences=["不知道问题在哪", "无法优化", "可能错失机会"],
                solutions=["设定 OMTM", "建立数据看板", "定期复盘"],
                severity="medium",
                tags=["metrics", "data-driven", "decision-making"],
            ),
            AntiPattern(
                id="copying_competitors",
                name="盲目抄袭",
                description="直接复制竞品功能，没有思考背后的逻辑和适用场景。",
                symptoms=["竞品做什么就做什么", "没有差异化", "用户问为什么做这个答不上来"],
                causes=["缺乏思考", "竞争焦虑", "路径依赖"],
                consequences=["同质化竞争", "没有护城河", "用户没有切换理由"],
                solutions=["理解竞品策略", "找到差异化点", "关注用户而非竞品"],
                severity="medium",
                tags=["strategy", "differentiation", "competition"],
            ),
            AntiPattern(
                id="perfectionism_paralysis",
                name="完美主义瘫痪",
                description="因为想要完美而迟迟不敢发布或行动。",
                symptoms=["产品总觉得还不完美", "不断推迟发布", "害怕用户批评"],
                causes=["完美主义", "害怕失败", "过度保护"],
                consequences=["错失市场窗口", "失去动力", "永远发布不了"],
                solutions=["接受不完美", "设定硬性发布日期", "迭代思维"],
                severity="medium",
                tags=["mindset", "shipping", "iteration"],
            ),
            AntiPattern(
                id="ignoring_user_feedback",
                name="忽视用户反馈",
                description="用户反馈的问题视而不见，或者只听自己想听的。",
                symptoms=["用户抱怨但不改", "只收集正面反馈", "觉得用户不懂"],
                causes=["自我中心", "确认偏误", "防御心理"],
                consequences=["用户流失", "产品脱离需求", "口碑变差"],
                solutions=["建立反馈机制", "保持开放心态", "定期用户访谈"],
                severity="high",
                tags=["user-feedback", "customer-development", "product-market-fit"],
            ),
            AntiPattern(
                id="scaling_prematurely",
                name="过早扩张",
                description="产品市场验证前就开始大规模扩张团队或营销投入。",
                symptoms=["PMF 没找到就招人", "预算大量投广告", "用户留存不行但拼命获客"],
                causes=["融资压力", "急于求成", "错误判断阶段"],
                consequences=["烧钱太快", "团队臃肿", "可能倒闭"],
                solutions=["先验证 PMF", "控制团队规模", "关注留存"],
                severity="critical",
                tags=["scaling", "growth", "funding"],
            ),
            AntiPattern(
                id="technical_debt_ignorance",
                name="技术债务忽视",
                description="只顾快上功能，完全不考虑代码质量和可维护性。",
                symptoms=["代码越来越乱", "新功能开发越来越慢", "bug 越修越多"],
                causes=["只顾短期", "缺乏工程文化", "压力过大"],
                consequences=["开发效率下降", "人才流失", "重构成本高"],
                solutions=["定期还债", "代码审查", "架构规划"],
                severity="medium",
                tags=["engineering", "technical-debt", "code-quality"],
            ),
        ]
        
        for antipattern in default_antipatterns:
            self._entries[antipattern.id] = antipattern
