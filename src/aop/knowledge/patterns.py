"""
创业模式库

收集常见的创业模式和最佳实践。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import KnowledgeBase, KnowledgeEntry


@dataclass
class StartupPattern(KnowledgeEntry):
    """创业模式"""
    when_to_use: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    success_rate: Optional[float] = None
    difficulty: str = "medium"  # easy, medium, hard
    time_to_value: str = ""  # 时间周期描述
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "when_to_use": self.when_to_use,
            "examples": self.examples,
            "success_rate": self.success_rate,
            "difficulty": self.difficulty,
            "time_to_value": self.time_to_value,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StartupPattern":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            when_to_use=data.get("when_to_use", []),
            examples=data.get("examples", []),
            success_rate=data.get("success_rate"),
            difficulty=data.get("difficulty", "medium"),
            time_to_value=data.get("time_to_value", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )


class StartupPatternLibrary(KnowledgeBase):
    """创业模式库"""
    
    def __init__(self, storage_path: Optional[Path] = None, load_defaults: bool = True):
        super().__init__(storage_path)
        
        if load_defaults and not self._entries:
            self._load_default_patterns()
    
    def search_patterns(
        self,
        query: str,
        tags: Optional[List[str]] = None
    ) -> List[StartupPattern]:
        """
        搜索相关模式
        
        Args:
            query: 搜索关键词
            tags: 标签过滤
        
        Returns:
            匹配的模式列表
        """
        results = self.search(query, tags)
        return [p for p in results if isinstance(p, StartupPattern)]
    
    def suggest_patterns(self, context: Dict[str, Any]) -> List[StartupPattern]:
        """
        根据上下文建议模式
        
        Args:
            context: 上下文信息，可能包含：
                - project_type: 项目类型
                - stage: 阶段 (idea, validation, growth, scale)
                - constraints: 约束条件
                - resources: 资源情况
        
        Returns:
            建议的模式列表
        """
        results = self.suggest(context)
        return [p for p in results if isinstance(p, StartupPattern)]
    
    def add_pattern(self, pattern: StartupPattern) -> None:
        """添加新模式"""
        self.add(pattern)
    
    def search(self, query: str, tags: Optional[List[str]] = None) -> List[KnowledgeEntry]:
        """搜索知识条目"""
        results = []
        query_lower = query.lower()
        
        for entry in self._entries.values():
            if not isinstance(entry, StartupPattern):
                continue
            
            # 标签过滤
            if not self._tags_match(entry.tags, tags):
                continue
            
            # 文本匹配
            text_fields = [
                entry.name,
                entry.description,
                " ".join(entry.when_to_use),
                " ".join(entry.examples),
            ]
            
            if any(self._text_match(f, query_lower) for f in text_fields):
                results.append(entry)
        
        return results
    
    def suggest(self, context: Dict[str, Any]) -> List[KnowledgeEntry]:
        """根据上下文建议"""
        results = []
        
        project_type = context.get("project_type", "").lower()
        stage = context.get("stage", "").lower()
        constraints = context.get("constraints", {})
        
        for entry in self._entries.values():
            if not isinstance(entry, StartupPattern):
                continue
            
            score = 0
            
            # 阶段匹配
            if stage:
                stage_keywords = {
                    "idea": ["validation", "demand", "验证", "需求"],
                    "validation": ["mvp", "验证", "测试", "validation", "test"],
                    "growth": ["增长", "growth", "scaling", "扩展"],
                    "scale": ["scale", "扩展", "增长", "growth"],
                }
                
                stage_tags = stage_keywords.get(stage, [])
                if any(t in entry.tags for t in stage_tags):
                    score += 2
            
            # 项目类型匹配
            if project_type:
                if project_type in entry.tags or project_type in entry.when_to_use:
                    score += 2
            
            # 资源约束匹配
            if constraints.get("low_budget"):
                if "low-cost" in entry.tags or "低成本" in entry.tags:
                    score += 2
            
            if constraints.get("time_constrained"):
                if "quick" in entry.tags or "快速" in entry.description:
                    score += 1
            
            if score > 0:
                results.append((entry, score))
        
        # 按分数排序
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results]
    
    def _create_entry(self, data: Dict[str, Any]) -> Optional[KnowledgeEntry]:
        return StartupPattern.from_dict(data)
    
    def _load_default_patterns(self) -> None:
        """加载默认模式"""
        default_patterns = [
            StartupPattern(
                id="landing_page_first",
                name="落地页优先",
                description="在构建产品前，先用落地页测试需求是否存在。通过收集邮箱注册或预购来验证用户兴趣。",
                when_to_use=["需求假设未验证", "B2C 产品", "时间紧张", "预算有限"],
                examples=["Dropbox", "Airbnb", "Buffer"],
                success_rate=0.7,
                difficulty="easy",
                time_to_value="1-3天",
                tags=["validation", "demand", "low-cost", "quick-win"],
            ),
            StartupPattern(
                id="concierge_mvp",
                name="礼宾式 MVP",
                description="人工提供产品服务，验证需求后再自动化。用户以为在使用产品，实际是人工在后台操作。",
                when_to_use=["解决方案假设未验证", "服务型产品", "技术复杂", "需要深度理解用户"],
                examples=["Food on the Table", "Zappos", "Aardvark"],
                success_rate=0.6,
                difficulty="medium",
                time_to_value="1-2周",
                tags=["validation", "solution", "manual", "customer-development"],
            ),
            StartupPattern(
                id="wizard_of_oz",
                name="绿野仙踪 MVP",
                description="用户以为在使用完整产品，实际是人工在背后运作。与礼宾式类似，但更注重用户体验的真实感。",
                when_to_use=["技术方案不确定", "需要验证用户体验", "AI/算法类产品"],
                examples=["Mechanical Turk", "早期 Facebook 推荐算法"],
                success_rate=0.55,
                difficulty="medium",
                time_to_value="1-2周",
                tags=["validation", "solution", "manual", "ux-testing"],
            ),
            StartupPattern(
                id="fake_door",
                name="假门测试",
                description="在产品中放置一个不存在的功能入口，测量用户点击率来验证需求。",
                when_to_use=["功能需求不确定", "需要快速决策", "已有用户基础"],
                examples=["各种 SaaS 功能测试"],
                success_rate=0.65,
                difficulty="easy",
                time_to_value="数小时",
                tags=["validation", "demand", "quick-win", "feature-testing"],
            ),
            StartupPattern(
                id="smoke_test",
                name="烟雾测试",
                description="投放广告到落地页，测量点击率和转化率，验证市场需求。",
                when_to_use=["市场大小不确定", "获客成本不确定", "B2C 产品"],
                examples=["各类 DTC 品牌"],
                success_rate=0.7,
                difficulty="easy",
                time_to_value="1-3天",
                tags=["validation", "demand", "low-cost", "marketing"],
            ),
            StartupPattern(
                id="pre_order",
                name="预购验证",
                description="在产品开发前接受预购，用真金白银验证付费意愿。",
                when_to_use=["付费意愿不确定", "硬件产品", "高客单价产品"],
                examples=["Pebble", "Oculus", "各类众筹项目"],
                success_rate=0.5,
                difficulty="medium",
                time_to_value="2-4周",
                tags=["validation", "pricing", "revenue", "crowdfunding"],
            ),
            StartupPattern(
                id="waitlist",
                name="等待名单",
                description="建立等待名单，测量用户愿意等待的程度和推荐行为。",
                when_to_use=["产品未准备好", "制造稀缺感", "病毒传播测试"],
                examples=["Robinhood", "Superhuman", "Clubhouse"],
                success_rate=0.75,
                difficulty="easy",
                time_to_value="1-5天",
                tags=["validation", "demand", "growth", "low-cost"],
            ),
            StartupPattern(
                id="single_feature_mvp",
                name="单功能 MVP",
                description="只做一个核心功能，把它做到极致，验证核心价值主张。",
                when_to_use=["功能范围不清", "资源有限", "竞争激烈"],
                examples=["Instagram (最初只是滤镜)", "Twitter (最初只是状态更新)"],
                success_rate=0.6,
                difficulty="medium",
                time_to_value="2-4周",
                tags=["mvp", "focus", "core-value", "product"],
            ),
            StartupPattern(
                id="viral_loop",
                name="病毒循环",
                description="设计让用户主动传播的产品机制，验证增长假设。",
                when_to_use=["增长假设不确定", "社交属性产品", "需要快速获客"],
                examples=["Dropbox 邀请奖励", "Airbnb 房东推荐", "微信红包"],
                success_rate=0.4,
                difficulty="hard",
                time_to_value="2-4周",
                tags=["growth", "viral", "acquisition", "metrics"],
            ),
            StartupPattern(
                id="pilot_program",
                name="试点项目",
                description="与少数早期客户深度合作，验证产品价值和商业模式。",
                when_to_use=["B2B 产品", "高客单价", "需要客户反馈"],
                examples=["各类企业软件早期"],
                success_rate=0.7,
                difficulty="medium",
                time_to_value="1-3月",
                tags=["validation", "b2b", "enterprise", "partnership"],
            ),
            StartupPattern(
                id="content_first",
                name="内容先行",
                description="先通过内容建立受众，再开发产品卖给受众。",
                when_to_use=["受众不确定", "需要建立信任", "知识付费/社区类"],
                examples=["各类 KOL 品牌", "Newsletter 产品"],
                success_rate=0.65,
                difficulty="medium",
                time_to_value="1-3月",
                tags=["audience", "content", "trust", "community"],
            ),
            StartupPattern(
                id="platform_arbitrage",
                name="平台套利",
                description="利用现有平台的流量和用户，快速验证产品概念。",
                when_to_use=["流量获取困难", "平台有红利", "快速验证"],
                examples=["各类微信小程序", "Shopify 应用", "Figma 插件"],
                success_rate=0.5,
                difficulty="medium",
                time_to_value="1-2周",
                tags=["growth", "platform", "distribution", "quick-win"],
            ),
        ]
        
        for pattern in default_patterns:
            self._entries[pattern.id] = pattern
