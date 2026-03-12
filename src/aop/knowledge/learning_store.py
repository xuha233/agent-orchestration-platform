"""
学习存储模块

捕获和存储项目开发过程中的学习，形成知识积累。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import KnowledgeBase, KnowledgeEntry


class LearningCategory(Enum):
    """学习类别"""
    TECHNICAL = "technical"         # 技术相关
    BUSINESS = "business"           # 业务相关
    PROCESS = "process"             # 流程相关
    TEAM = "team"                   # 团队相关
    MARKET = "market"               # 市场相关
    USER = "user"                   # 用户相关
    MISTAKE = "mistake"             # 错误教训
    SUCCESS = "success"             # 成功经验


@dataclass
class LearningEntry(KnowledgeEntry):
    """学习条目"""
    category: str = "technical"
    phase: str = ""                 # 阶段: clarify, hypothesis, execution, validation
    hypothesis_id: Optional[str] = None  # 关联的假设 ID
    evidence: List[str] = field(default_factory=list)  # 支撑证据
    action_items: List[str] = field(default_factory=list)  # 后续行动
    impact: str = "medium"          # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "category": self.category,
            "phase": self.phase,
            "hypothesis_id": self.hypothesis_id,
            "evidence": self.evidence,
            "action_items": self.action_items,
            "impact": self.impact,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningEntry":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category=data.get("category", "technical"),
            phase=data.get("phase", ""),
            hypothesis_id=data.get("hypothesis_id"),
            evidence=data.get("evidence", []),
            action_items=data.get("action_items", []),
            impact=data.get("impact", "medium"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )


class LearningStore(KnowledgeBase):
    """学习存储"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        super().__init__(storage_path)
    
    def add_learning(
        self,
        name: str,
        description: str,
        category: str = "technical",
        phase: str = "",
        hypothesis_id: Optional[str] = None,
        evidence: Optional[List[str]] = None,
        action_items: Optional[List[str]] = None,
        impact: str = "medium",
        tags: Optional[List[str]] = None,
    ) -> LearningEntry:
        """
        添加学习条目
        
        Args:
            name: 学习标题
            description: 学习内容描述
            category: 类别
            phase: 阶段
            hypothesis_id: 关联假设 ID
            evidence: 支撑证据
            action_items: 后续行动
            impact: 影响程度
            tags: 标签
        
        Returns:
            创建的学习条目
        """
        learning = LearningEntry(
            id=f"learning_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._entries)}",
            name=name,
            description=description,
            category=category,
            phase=phase,
            hypothesis_id=hypothesis_id,
            evidence=evidence or [],
            action_items=action_items or [],
            impact=impact,
            tags=tags or [],
        )
        
        self.add(learning)
        return learning
    
    def get_learnings_by_phase(self, phase: str) -> List[LearningEntry]:
        """按阶段获取学习"""
        return [
            e for e in self._entries.values()
            if isinstance(e, LearningEntry) and e.phase == phase
        ]
    
    def get_learnings_by_category(self, category: str) -> List[LearningEntry]:
        """按类别获取学习"""
        return [
            e for e in self._entries.values()
            if isinstance(e, LearningEntry) and e.category == category
        ]
    
    def get_learnings_by_hypothesis(self, hypothesis_id: str) -> List[LearningEntry]:
        """按假设 ID 获取学习"""
        return [
            e for e in self._entries.values()
            if isinstance(e, LearningEntry) and e.hypothesis_id == hypothesis_id
        ]
    
    def get_high_impact_learnings(self) -> List[LearningEntry]:
        """获取高影响学习"""
        return [
            e for e in self._entries.values()
            if isinstance(e, LearningEntry) and e.impact == "high"
        ]
    
    def get_recent_learnings(self, days: int = 7) -> List[LearningEntry]:
        """获取最近的学习"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        return [
            e for e in self._entries.values()
            if isinstance(e, LearningEntry) and e.created_at.timestamp() >= cutoff
        ]
    
    def get_summary(self) -> str:
        """获取学习摘要"""
        if not self._entries:
            return "暂无学习记录。"
        
        # 按类别统计
        category_counts: Dict[str, int] = {}
        impact_counts: Dict[str, int] = {}
        
        for entry in self._entries.values():
            if isinstance(entry, LearningEntry):
                category_counts[entry.category] = category_counts.get(entry.category, 0) + 1
                impact_counts[entry.impact] = impact_counts.get(entry.impact, 0) + 1
        
        lines = [
            "# 学习摘要",
            "",
            f"**总学习数**: {len(self._entries)}",
            "",
            "## 按类别分布",
        ]
        
        for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {category}: {count}")
        
        lines.extend([
            "",
            "## 按影响分布",
        ])
        
        for impact, count in sorted(impact_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {impact}: {count}")
        
        # 高影响学习详情
        high_impact = self.get_high_impact_learnings()
        if high_impact:
            lines.extend([
                "",
                "## 高影响学习",
            ])
            for learning in high_impact[:5]:
                lines.append(f"- {learning.name}: {learning.description[:100]}...")
        
        return "\n".join(lines)
    
    def search(self, query: str, tags: Optional[List[str]] = None) -> List[KnowledgeEntry]:
        """搜索学习"""
        results = []
        query_lower = query.lower()
        
        for entry in self._entries.values():
            if not isinstance(entry, LearningEntry):
                continue
            
            if not self._tags_match(entry.tags, tags):
                continue
            
            text_fields = [
                entry.name,
                entry.description,
                " ".join(entry.evidence),
                " ".join(entry.action_items),
            ]
            
            if any(self._text_match(f, query_lower) for f in text_fields):
                results.append(entry)
        
        return results
    
    def suggest(self, context: Dict[str, Any]) -> List[KnowledgeEntry]:
        """根据上下文建议"""
        phase = context.get("phase", "")
        category = context.get("category", "")
        
        results = []
        
        for entry in self._entries.values():
            if not isinstance(entry, LearningEntry):
                continue
            
            score = 0
            
            if phase and entry.phase == phase:
                score += 2
            
            if category and entry.category == category:
                score += 1
            
            if entry.impact == "high":
                score += 1
            
            if score > 0:
                results.append((entry, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results]
    
    def _create_entry(self, data: Dict[str, Any]) -> Optional[KnowledgeEntry]:
        return LearningEntry.from_dict(data)
    
    def export_to_markdown(self) -> str:
        """导出为 Markdown 格式"""
        if not self._entries:
            return "# 学习记录\n\n暂无学习记录。"
        
        lines = ["# 学习记录\n"]
        
        # 按阶段分组
        phases = ["clarify", "hypothesis", "execution", "validation"]
        phase_names = {
            "clarify": "需求澄清",
            "hypothesis": "假设生成",
            "execution": "任务执行",
            "validation": "结果验证",
        }
        
        for phase in phases:
            phase_learnings = self.get_learnings_by_phase(phase)
            if phase_learnings:
                lines.append(f"## {phase_names.get(phase, phase)}\n")
                
                for learning in phase_learnings:
                    impact_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(learning.impact, "⚪")
                    lines.append(f"### {impact_emoji} {learning.name}\n")
                    lines.append(f"{learning.description}\n")
                    
                    if learning.evidence:
                        lines.append(f"\n**证据**:\n")
                        for e in learning.evidence:
                            lines.append(f"- {e}")
                    
                    if learning.action_items:
                        lines.append(f"\n**后续行动**:\n")
                        for a in learning.action_items:
                            lines.append(f"- [ ] {a}")
                    
                    lines.append(f"\n---\n")
        
        # 无阶段的学习
        no_phase = [e for e in self._entries.values() 
                   if isinstance(e, LearningEntry) and not e.phase]
        if no_phase:
            lines.append("## 其他\n")
            for learning in no_phase:
                lines.append(f"- {learning.name}: {learning.description}\n")
        
        return "\n".join(lines)
