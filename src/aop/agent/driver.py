"""
AgentDriver - 全自动 Agent 团队驱动器

从模糊需求到交付的全自动执行。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from .types import (
    SprintContext,
    SprintState,
    SprintResult,
    AgentDriverConfig,
    ClarifiedRequirement,
    ExtractedLearning,
)
from .clarifier import RequirementClarifier
from .hypothesis_generator import HypothesisGenerator
from .validator import AutoValidator
from .learning_extractor import LearningExtractor


class AgentDriver:
    """
    全自动 Agent 团队驱动器

    这是 OpenClaw/Claude Code 的统一入口。
    从模糊需求到交付，全自动执行。

    使用示例:
        driver = AgentDriver()
        result = driver.run_from_vague_description(
            "帮我做一个电商系统",
            clarifications_callback=lambda q: input(q)
        )
    """

    def __init__(self, config: Optional[AgentDriverConfig] = None):
        self.config = config or AgentDriverConfig()
        self.context: Optional[SprintContext] = None

        # 初始化各组件
        self.clarifier = RequirementClarifier()
        self.hypothesis_generator = HypothesisGenerator()
        self.validator = AutoValidator()
        self.learning_extractor = LearningExtractor()

        # 存储路径
        self.storage_path = self.config.storage_path or Path(".aop")

    def run_from_vague_description(
        self,
        vague_input: str,
        clarifications_callback: Optional[Callable[[str], str]] = None,
    ) -> SprintResult:
        """
        从模糊描述开始全自动执行

        Args:
            vague_input: 用户的模糊描述
            clarifications_callback: 追问回调函数，如果不提供则自动推断

        Returns:
            SprintResult: 冲刺执行结果
        """
        # 初始化冲刺上下文
        self.context = SprintContext(
            sprint_id=self._generate_sprint_id(),
            original_input=vague_input,
            state=SprintState.INITIALIZED,
        )

        try:
            # 阶段1: 澄清需求
            self._report_progress("clarifying", "澄清需求中...")
            clarified = self._clarify_requirement(vague_input, clarifications_callback)
            self.context.clarified_requirement = clarified
            self.context.state = SprintState.CLARIFIED

            # 阶段2: 生成假设
            self._report_progress("generating_hypotheses", "生成假设中...")
            hypotheses = self._generate_hypotheses(clarified)
            self.context.hypotheses = hypotheses
            self.context.state = SprintState.HYPOTHESES_GENERATED

            # 阶段3: 构建任务图
            self._report_progress("decomposing_tasks", "分解任务中...")
            self.context.state = SprintState.TASKS_DECOMPOSED

            # 阶段4: 并行执行 (简化版)
            if self.config.auto_execute:
                self._report_progress("executing", "并行执行中...")
                results = self._execute_tasks()
                self.context.execution_results = results
                self.context.state = SprintState.EXECUTED

                # 阶段5: 自动验证
                if self.config.auto_validate:
                    self._report_progress("validating", "验证结果中...")
                    self._auto_validate(hypotheses, results)
                    self.context.state = SprintState.VALIDATED

                # 阶段6: 学习提取
                if self.config.auto_learn:
                    self._report_progress("learning", "提取学习中...")
                    learnings = self._extract_learnings(results)
                    self.context.learnings = learnings
                    self.context.state = SprintState.COMPLETED

            # 保存上下文
            self._save_context()

            return self._build_result()

        except Exception as e:
            self.context.state = SprintState.FAILED
            raise

    def run_from_clarified_requirement(
        self,
        requirement: Dict[str, Any],
    ) -> SprintResult:
        """
        从已澄清的需求开始执行
        """
        self.context = SprintContext(
            sprint_id=self._generate_sprint_id(),
            original_input=requirement.get("summary", ""),
            clarified_requirement=ClarifiedRequirement(**requirement),
            state=SprintState.CLARIFIED,
        )

        hypotheses = self._generate_hypotheses(self.context.clarified_requirement)
        self.context.hypotheses = hypotheses

        if self.config.auto_execute:
            results = self._execute_tasks()
            self.context.execution_results = results

            if self.config.auto_validate:
                self._auto_validate(hypotheses, results)

            if self.config.auto_learn:
                learnings = self._extract_learnings(results)
                self.context.learnings = learnings

        self._save_context()
        return self._build_result()

    def resume_sprint(self, sprint_id: str) -> SprintResult:
        """
        恢复中断的冲刺
        """
        self.context = self._load_context(sprint_id)

        if self.context is None:
            raise ValueError(f"Sprint {sprint_id} not found")

        # 根据当前状态继续执行
        # ... (简化实现)

        return self._build_result()

    def get_next_steps(self) -> List[str]:
        """获取建议的下一步操作"""
        if not self.context:
            return ["使用 run_from_vague_description() 开始新冲刺"]

        state_recommendations = {
            SprintState.INITIALIZED: ["等待澄清需求"],
            SprintState.CLARIFIED: ["准备生成假设"],
            SprintState.HYPOTHESES_GENERATED: ["准备分解任务"],
            SprintState.TASKS_DECOMPOSED: ["准备并行执行"],
            SprintState.EXECUTED: ["准备验证结果"],
            SprintState.VALIDATED: ["准备提取学习"],
            SprintState.COMPLETED: ["冲刺已完成，可以开始新冲刺"],
            SprintState.FAILED: ["冲刺失败，检查错误日志"],
        }
        return state_recommendations.get(self.context.state, [])

    # ============ 私有方法 ============

    def _clarify_requirement(
        self,
        vague_input: str,
        callback: Optional[Callable[[str], str]],
    ) -> ClarifiedRequirement:
        """澄清需求"""
        return self.clarifier.clarify(
            vague_input,
            max_rounds=self.config.max_clarification_rounds,
            interactive_callback=callback,
        )

    def _generate_hypotheses(self, requirement: ClarifiedRequirement) -> List[Any]:
        """生成假设"""
        raw_hypotheses = self.hypothesis_generator.generate(requirement)
        return raw_hypotheses

    def _execute_tasks(self) -> List[Dict[str, Any]]:
        """
        执行任务 (简化版)
        
        实际实现会调用 ExecutionEngine
        """
        # TODO: 集成现有的 ExecutionEngine
        return []

    def _auto_validate(self, hypotheses: List[Any], results: List[Dict[str, Any]]):
        """自动验证假设"""
        for hypothesis in hypotheses:
            # 验证每个假设
            pass

    def _extract_learnings(self, results: List[Dict[str, Any]]) -> List[ExtractedLearning]:
        """从执行结果中提取学习"""
        return self.learning_extractor.extract(results)

    def _build_result(self) -> SprintResult:
        """构建最终结果"""
        req_dict = {}
        if self.context and self.context.clarified_requirement:
            req_dict = {
                "summary": self.context.clarified_requirement.summary,
                "user_type": self.context.clarified_requirement.user_type,
                "core_features": self.context.clarified_requirement.core_features,
            }

        return SprintResult(
            sprint_id=self.context.sprint_id if self.context else "",
            success=self.context.state == SprintState.COMPLETED if self.context else False,
            clarified_requirement=req_dict,
            hypotheses=[],
            execution_results=self.context.execution_results if self.context else [],
            learnings=[],
            next_steps=self.get_next_steps(),
            summary=self._generate_summary(),
        )

    def _generate_summary(self) -> str:
        """生成冲刺摘要"""
        if not self.context:
            return "无活跃冲刺"

        return f"冲刺 {self.context.sprint_id} 已完成，共处理 {len(self.context.hypotheses)} 个假设"

    def _generate_sprint_id(self) -> str:
        """生成冲刺ID"""
        timestamp = datetime.now().isoformat()
        return f"sprint-{hashlib.sha256(timestamp.encode()).hexdigest()[:8]}"

    def _report_progress(self, stage: str, message: str):
        """报告进度"""
        if self.config.progress_callback:
            self.config.progress_callback(stage, message)

    def _save_context(self):
        """保存冲刺上下文"""
        if not self.context:
            return

        context_path = self.storage_path / "sprints" / f"{self.context.sprint_id}.json"
        context_path.parent.mkdir(parents=True, exist_ok=True)

        with open(context_path, "w", encoding="utf-8") as f:
            json.dump({
                "sprint_id": self.context.sprint_id,
                "original_input": self.context.original_input,
                "state": self.context.state.value,
                "created_at": self.context.created_at.isoformat(),
            }, f, ensure_ascii=False, indent=2)

    def _load_context(self, sprint_id: str) -> Optional[SprintContext]:
        """加载冲刺上下文"""
        context_path = self.storage_path / "sprints" / f"{sprint_id}.json"

        if not context_path.exists():
            return None

        with open(context_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return SprintContext(
            sprint_id=data["sprint_id"],
            original_input=data["original_input"],
            state=SprintState(data["state"]),
        )
