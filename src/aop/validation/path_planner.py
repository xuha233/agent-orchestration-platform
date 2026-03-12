"""
ValidationPathPlanner - 最小验证路径规划器

目标：用最少的时间和成本验证所有关键假设

策略：
1. 并行验证无依赖的假设
2. 优先验证高影响低成本的假设
3. 识别关键路径
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict


class ValidationMethod(Enum):
    """验证方法"""
    LANDING_PAGE = "landing_page"
    SURVEY = "survey"
    INTERVIEW = "interview"
    PROTOTYPE = "prototype"
    CONCIERGE = "concierge"
    WIZARD_OF_OZ = "wizard_of_oz"
    SMOKE_TEST = "smoke_test"
    A_B_TEST = "ab_test"
    FAKE_DOOR = "fake_door"
    CROWDFUNDING = "crowdfunding"
    PRE_ORDER = "pre_order"
    WAITLIST = "waitlist"


class CostLevel(Enum):
    """成本等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PlannerConfig:
    """规划器配置"""
    max_parallel_steps: int = 3
    prefer_low_cost: bool = True
    prefer_quick_wins: bool = True
    max_total_days: Optional[int] = None


@dataclass
class ValidationStep:
    """验证步骤"""
    step_id: str
    hypothesis_id: str
    method: str
    description: str
    estimated_days: int
    estimated_cost: str
    dependencies: List[str]
    success_criteria: str
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "hypothesis_id": self.hypothesis_id,
            "method": self.method,
            "description": self.description,
            "estimated_days": self.estimated_days,
            "estimated_cost": self.estimated_cost,
            "dependencies": self.dependencies,
            "success_criteria": self.success_criteria,
            "priority": self.priority,
        }


@dataclass
class ValidationPath:
    """验证路径"""
    steps: List[ValidationStep]
    total_days: int
    total_cost: str
    parallel_opportunities: List[List[str]]
    critical_path: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "total_days": self.total_days,
            "total_cost": self.total_cost,
            "parallel_opportunities": self.parallel_opportunities,
            "critical_path": self.critical_path,
        }
    
    def get_summary(self) -> str:
        """获取路径摘要"""
        lines = [
            f"# 验证路径规划",
            f"",
            f"**总时间**: {self.total_days} 天",
            f"**总成本**: {self.total_cost}",
            f"**步骤数**: {len(self.steps)}",
            f"**可并行组**: {len(self.parallel_opportunities)} 组",
            f"",
            f"## 步骤详情",
        ]
        
        for i, step in enumerate(self.steps):
            is_critical = step.step_id in self.critical_path
            critical_mark = " ⚠️ 关键路径" if is_critical else ""
            lines.extend([
                f"",
                f"### {i+1}. {step.description}{critical_mark}",
                f"- **假设**: {step.hypothesis_id}",
                f"- **方法**: {step.method}",
                f"- **时间**: {step.estimated_days} 天",
                f"- **成本**: {step.estimated_cost}",
            ])
            if step.dependencies:
                lines.append(f"- **依赖**: {', '.join(step.dependencies)}")
        
        if self.parallel_opportunities:
            lines.extend([
                f"",
                f"## 并行执行机会",
            ])
            for i, group in enumerate(self.parallel_opportunities):
                lines.append(f"- 第{i+1}组: {', '.join(group)}")
        
        return "\n".join(lines)


class ValidationPathPlanner:
    """最小验证路径规划器"""
    
    # 验证方法的时间/成本映射
    METHOD_INFO = {
        ValidationMethod.LANDING_PAGE: {"days": 2, "cost": CostLevel.LOW},
        ValidationMethod.SURVEY: {"days": 1, "cost": CostLevel.LOW},
        ValidationMethod.INTERVIEW: {"days": 3, "cost": CostLevel.LOW},
        ValidationMethod.PROTOTYPE: {"days": 5, "cost": CostLevel.MEDIUM},
        ValidationMethod.CONCIERGE: {"days": 7, "cost": CostLevel.LOW},
        ValidationMethod.WIZARD_OF_OZ: {"days": 5, "cost": CostLevel.LOW},
        ValidationMethod.SMOKE_TEST: {"days": 2, "cost": CostLevel.LOW},
        ValidationMethod.A_B_TEST: {"days": 7, "cost": CostLevel.MEDIUM},
        ValidationMethod.FAKE_DOOR: {"days": 1, "cost": CostLevel.LOW},
        ValidationMethod.CROWDFUNDING: {"days": 14, "cost": CostLevel.MEDIUM},
        ValidationMethod.PRE_ORDER: {"days": 7, "cost": CostLevel.LOW},
        ValidationMethod.WAITLIST: {"days": 3, "cost": CostLevel.LOW},
    }
    
    # 假设类型到推荐验证方法的映射
    HYPOTHESIS_METHOD_MAP = {
        "demand": [ValidationMethod.LANDING_PAGE, ValidationMethod.FAKE_DOOR, ValidationMethod.WAITLIST],
        "solution": [ValidationMethod.PROTOTYPE, ValidationMethod.CONCIERGE, ValidationMethod.WIZARD_OF_OZ],
        "pricing": [ValidationMethod.SURVEY, ValidationMethod.PRE_ORDER, ValidationMethod.CROWDFUNDING],
        "growth": [ValidationMethod.A_B_TEST, ValidationMethod.SMOKE_TEST],
        "business": [ValidationMethod.INTERVIEW, ValidationMethod.PRE_ORDER],
        "technical": [ValidationMethod.PROTOTYPE, ValidationMethod.SMOKE_TEST],
        "default": [ValidationMethod.LANDING_PAGE, ValidationMethod.PROTOTYPE],
    }
    
    def __init__(self, config: Optional[PlannerConfig] = None):
        self.config = config or PlannerConfig()
    
    def plan(
        self,
        hypotheses: List[Dict],
        constraints: Optional[Dict] = None
    ) -> ValidationPath:
        """
        规划最小验证路径
        
        Args:
            hypotheses: 假设列表
            constraints: 约束条件（时间、预算等）
        
        Returns:
            ValidationPath 验证路径
        """
        if not hypotheses:
            return ValidationPath(
                steps=[],
                total_days=0,
                total_cost="low",
                parallel_opportunities=[],
                critical_path=[],
            )
        
        # 1. 为每个假设生成验证步骤
        steps = self._create_steps(hypotheses)
        
        # 2. 分析依赖关系
        steps = self._analyze_dependencies(steps, hypotheses)
        
        # 3. 识别并行执行机会
        parallel_groups = self.identify_parallel_opportunities(steps)
        
        # 4. 计算关键路径
        critical_path = self.calculate_critical_path(steps)
        
        # 5. 计算总时间和成本
        total_days = self._calculate_total_days(steps, parallel_groups)
        total_cost = self._calculate_total_cost(steps)
        
        return ValidationPath(
            steps=steps,
            total_days=total_days,
            total_cost=total_cost,
            parallel_opportunities=parallel_groups,
            critical_path=critical_path,
        )
    
    def suggest_validation_method(self, hypothesis: Dict) -> str:
        """
        根据假设类型建议验证方法
        
        Args:
            hypothesis: 假设数据
        
        Returns:
            推荐的验证方法名称
        """
        h_type = hypothesis.get("type", hypothesis.get("hypothesis_type", "default"))
        
        if isinstance(h_type, str):
            type_key = h_type.lower()
        else:
            type_key = "default"
        
        methods = self.HYPOTHESIS_METHOD_MAP.get(type_key, self.HYPOTHESIS_METHOD_MAP["default"])
        
        # 如果有显式的验证方法，检查是否有效
        explicit_method = hypothesis.get("validation_method", "")
        if explicit_method:
            for method in ValidationMethod:
                if method.value in explicit_method.lower():
                    return method.value
        
        # 返回推荐的第一个方法
        return methods[0].value if methods else "landing_page"
    
    def identify_parallel_opportunities(self, steps: List[ValidationStep]) -> List[List[str]]:
        """
        识别可并行执行的步骤
        
        Args:
            steps: 验证步骤列表
        
        Returns:
            可并行执行的步骤组列表
        """
        if not steps:
            return []
        
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(steps)
        
        # 按优先级分组
        groups: List[List[str]] = []
        assigned: Set[str] = set()
        
        while len(assigned) < len(steps):
            # 找出所有依赖已满足且未分配的步骤
            available = []
            for step in steps:
                if step.step_id in assigned:
                    continue
                
                deps = dependency_graph.get(step.step_id, set())
                if all(d in assigned for d in deps):
                    available.append(step)
            
            if not available:
                break
            
            # 按优先级排序
            available.sort(key=lambda s: s.priority, reverse=True)
            
            # 取最多 max_parallel_steps 个
            batch = [s.step_id for s in available[:self.config.max_parallel_steps]]
            groups.append(batch)
            assigned.update(batch)
        
        return groups
    
    def calculate_critical_path(self, steps: List[ValidationStep]) -> List[str]:
        """
        计算关键路径
        
        关键路径是验证时间最长的路径
        
        Args:
            steps: 验证步骤列表
        
        Returns:
            关键路径上的步骤 ID 列表
        """
        if not steps:
            return []
        
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(steps)
        step_map = {s.step_id: s for s in steps}
        
        # 计算每个步骤的最早完成时间
        earliest_finish: Dict[str, int] = {}
        
        def get_earliest_finish(step_id: str) -> int:
            if step_id in earliest_finish:
                return earliest_finish[step_id]
            
            step = step_map[step_id]
            deps = dependency_graph.get(step_id, set())
            
            if not deps:
                earliest_finish[step_id] = step.estimated_days
            else:
                max_dep_finish = max(get_earliest_finish(d) for d in deps)
                earliest_finish[step_id] = max_dep_finish + step.estimated_days
            
            return earliest_finish[step_id]
        
        for step in steps:
            get_earliest_finish(step.step_id)
        
        # 找到最大完成时间
        max_finish = max(earliest_finish.values())
        
        # 从后向前回溯关键路径
        critical_path = []
        current_time = max_finish
        
        # 按完成时间降序排序步骤
        sorted_steps = sorted(
            steps,
            key=lambda s: earliest_finish[s.step_id],
            reverse=True
        )
        
        for step in sorted_steps:
            finish_time = earliest_finish[step.step_id]
            start_time = finish_time - step.estimated_days
            
            if start_time <= current_time <= finish_time:
                if step.step_id not in critical_path:
                    critical_path.append(step.step_id)
                    current_time = start_time
        
        critical_path.reverse()
        return critical_path
    
    def _create_steps(self, hypotheses: List[Dict]) -> List[ValidationStep]:
        """为每个假设创建验证步骤"""
        steps = []
        
        for i, h in enumerate(hypotheses):
            hypothesis_id = h.get("hypothesis_id", h.get("id", f"h{i}"))
            statement = h.get("statement", h.get("description", ""))
            
            # 建议验证方法
            method = self.suggest_validation_method(h)
            
            # 获取方法信息
            try:
                method_enum = ValidationMethod(method)
            except ValueError:
                method_enum = ValidationMethod.LANDING_PAGE
            
            method_info = self.METHOD_INFO.get(method_enum, {"days": 3, "cost": CostLevel.MEDIUM})
            
            step = ValidationStep(
                step_id=f"step_{i}",
                hypothesis_id=hypothesis_id,
                method=method,
                description=f"验证假设: {statement[:50]}{'...' if len(statement) > 50 else ''}",
                estimated_days=method_info["days"],
                estimated_cost=method_info["cost"].value,
                dependencies=h.get("dependencies", []),
                success_criteria=h.get("success_criteria", "假设成立") if isinstance(h.get("success_criteria"), str) else "、".join(h.get("success_criteria", ["假设成立"])),
                priority=h.get("priority", 0) if isinstance(h.get("priority"), (int, float)) else 0,
            )
            
            steps.append(step)
        
        return steps
    
    def _analyze_dependencies(
        self,
        steps: List[ValidationStep],
        hypotheses: List[Dict]
    ) -> List[ValidationStep]:
        """分析步骤间的依赖关系"""
        hypothesis_to_step = {s.hypothesis_id: s.step_id for s in steps}
        
        for step in steps:
            # 转换假设ID依赖为步骤ID依赖
            step_deps = []
            for dep_id in step.dependencies:
                if dep_id in hypothesis_to_step:
                    step_deps.append(hypothesis_to_step[dep_id])
            step.dependencies = step_deps
        
        return steps
    
    def _build_dependency_graph(self, steps: List[ValidationStep]) -> Dict[str, Set[str]]:
        """构建依赖图"""
        graph: Dict[str, Set[str]] = defaultdict(set)
        
        for step in steps:
            for dep in step.dependencies:
                graph[step.step_id].add(dep)
        
        return graph
    
    def _calculate_total_days(
        self,
        steps: List[ValidationStep],
        parallel_groups: List[List[str]]
    ) -> int:
        """计算总天数（考虑并行）"""
        if not steps:
            return 0
        
        step_map = {s.step_id: s for s in steps}
        total_days = 0
        
        for group in parallel_groups:
            # 并行组的完成时间取决于组内最长的步骤
            max_days = max(step_map[step_id].estimated_days for step_id in group)
            total_days += max_days
        
        return total_days
    
    def _calculate_total_cost(self, steps: List[ValidationStep]) -> str:
        """计算总成本等级"""
        if not steps:
            return "low"
        
        costs = [s.estimated_cost for s in steps]
        
        if any(c == "high" for c in costs):
            return "high"
        elif any(c == "medium" for c in costs):
            return "medium"
        else:
            return "low"
