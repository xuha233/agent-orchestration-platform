"""
AgentDriver - 全自动 Agent 团队驱动器

从模糊需求到交付的全自动执行。
支持双模式：
- OrchestratorClient 模式：使用中枢 Agent 进行决策和调度（推荐）
- LLMClient 模式：直接调用 LLM API（向后兼容）
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Callable, Dict, Any, TYPE_CHECKING, Literal

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
from .persistence import SprintPersistence
from .scheduler import TaskScheduler
from ..core.engine import ExecutionEngine

if TYPE_CHECKING:
    from ..llm import LLMClient, ClaudeClient, LocalLLMClient
    from ..orchestrator import OrchestratorClient, OrchestratorConfig


class AgentDriver:
    """
    全自动 Agent 团队驱动器

    这是 OpenClaw/Claude Code 的统一入口。
    从模糊需求到交付，全自动执行。

    支持两种模式：
    1. OrchestratorClient 模式：使用中枢 Agent 进行决策和调度（推荐）
    2. LLMClient 模式：直接调用 LLM API（向后兼容）

    使用示例:
        # 使用 Orchestrator 模式（推荐）
        driver = AgentDriver()
        result = driver.run_from_vague_description("帮我做一个电商系统")

        # 指定 Orchestrator 类型
        driver = AgentDriver(config=AgentDriverConfig(orchestrator_type="claude-code"))

        # 向后兼容：使用 LLMClient 模式
        driver = AgentDriver(llm_client=my_llm_client)

        # 恢复中断的冲刺
        result = driver.resume_sprint("sprint-abc123")

        # 获取活跃冲刺列表
        active = driver.get_active_sprints()
    """

    def __init__(
        self,
        config: AgentDriverConfig | None = None,
        llm_client: LLMClient | None = None,
        orchestrator: OrchestratorClient | None = None,
    ):
        """
        初始化 AgentDriver

        Args:
            config: 驱动器配置
            llm_client: LLM 客户端（向后兼容，优先级低于 orchestrator）
            orchestrator: 中枢 Agent 客户端（推荐）
        """
        self.config = config or AgentDriverConfig()
        self.context: SprintContext | None = None
        self._orchestrator: OrchestratorClient | None = orchestrator
        self._llm: LLMClient | None = llm_client

        # 初始化 Orchestrator 或 LLM 客户端
        if orchestrator:
            # 优先使用传入的 orchestrator
            self._orchestrator = orchestrator
        elif self.config.orchestrator_type != "auto":
            # 根据配置创建 orchestrator
            self._orchestrator = self._create_orchestrator()
        else:
            # 自动检测最佳 orchestrator
            self._orchestrator = self._auto_detect_orchestrator()

        # 如果没有 orchestrator，回退到 LLMClient
        if not self._orchestrator:
            if llm_client:
                self._llm = llm_client
            else:
                self._llm = self._create_llm_client()

        # 初始化各组件（传入 OrchestratorClient 或 LLMClient）
        self.clarifier = RequirementClarifier(
            llm_client=self._llm,
            orchestrator_client=self._orchestrator,
        )
        self.hypothesis_generator = HypothesisGenerator(
            llm_client=self._llm,
            orchestrator_client=self._orchestrator,
        )
        self.validator = AutoValidator()
        self.learning_extractor = LearningExtractor(
            orchestrator_client=self._orchestrator,
        )

        # 存储路径
        self.storage_path = self.config.storage_path or Path(".aop")

        # 初始化持久化管理器
        self.persistence = SprintPersistence(str(self.storage_path / "sprints"))

    def _create_llm_client(self) -> LLMClient | None:
        """根据配置创建 LLM 客户端（向后兼容）"""
        from ..llm import ClaudeClient, LocalLLMClient

        if self.config.llm_provider == "claude":
            return ClaudeClient(
                api_key=self.config.llm_api_key,
                model=self.config.llm_model,
            )
        elif self.config.llm_provider == "local":
            return LocalLLMClient()
        return None

    def _create_orchestrator(self) -> OrchestratorClient | None:
        """
        根据配置创建 OrchestratorClient

        Returns:
            OrchestratorClient 实例，如果创建失败则返回 None
        """
        from ..orchestrator import create_orchestrator, OrchestratorConfig

        orch_type = self.config.orchestrator_type
        if orch_type == "auto":
            return self._auto_detect_orchestrator()

        try:
            config = OrchestratorConfig(
                timeout=self.config.default_timeout,
            )
            return create_orchestrator(
                orchestrator_type=orch_type,
                config=config,
                llm_client=self._llm,
            )
        except Exception as e:
            import sys
            print(f"[AOP] Failed to create orchestrator '{orch_type}': {e}", file=sys.stderr)
            return None

    def _auto_detect_orchestrator(self) -> OrchestratorClient | None:
        """
        自动检测最佳可用的 Orchestrator

        优先级: claude-code > opencode > openclaw > api

        Returns:
            最佳可用的 OrchestratorClient 实例
        """
        from ..orchestrator import (
            get_best_orchestrator,
            create_orchestrator,
            OrchestratorConfig,
        )

        try:
            best_type = get_best_orchestrator()
            if best_type == "api" and not self._llm:
                # API 模式需要 LLMClient
                return None

            config = OrchestratorConfig(
                timeout=self.config.default_timeout,
            )
            return create_orchestrator(
                orchestrator_type=best_type,
                config=config,
                llm_client=self._llm,
            )
        except Exception as e:
            import sys
            print(f"[AOP] Auto-detect orchestrator failed: {e}", file=sys.stderr)
            return None

    def get_orchestrator_info(self) -> Dict[str, Any]:
        """
        获取当前使用的 Orchestrator 信息

        Returns:
            Orchestrator 信息字典
        """
        if self._orchestrator:
            return {
                "type": self._orchestrator.orchestrator_type,
                "capabilities": [c.value for c in self._orchestrator.capabilities],
                "mode": "orchestrator",
            }
        elif self._llm:
            return {
                "type": "llm_client",
                "provider": self.config.llm_provider,
                "model": self.config.llm_model,
                "mode": "llm",
            }
        else:
            return {
                "type": "none",
                "mode": "fallback",
            }

    def run_from_vague_description(
        self,
        vague_input: str,
        clarifications_callback: Callable[[str], str] | None = None,
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
        
        # 保存初始状态
        self.persistence.save(self.context)

        try:
            # 阶段1: 澄清需求
            self._report_progress("clarifying", "澄清需求中...")
            clarified = self._clarify_requirement(vague_input, clarifications_callback)
            self.context.clarified_requirement = clarified
            self.context.state = SprintState.CLARIFIED
            self.persistence.save(self.context)  # 增量保存

            # 阶段2: 生成假设
            self._report_progress("generating_hypotheses", "生成假设中...")
            hypotheses = self._generate_hypotheses(clarified)
            self.context.hypotheses = hypotheses
            self.context.state = SprintState.HYPOTHESES_GENERATED
            self.persistence.save(self.context)  # 增量保存

            # 阶段3: 构建任务图
            self._report_progress("decomposing_tasks", "分解任务中...")
            self.context.state = SprintState.TASKS_DECOMPOSED
            self.persistence.save(self.context)  # 增量保存

            # 阶段4: 并行执行 (简化版)
            if self.config.auto_execute:
                self._report_progress("executing", "并行执行中...")
                results = self._execute_tasks()
                self.context.execution_results = results
                self.context.state = SprintState.EXECUTED
                self.persistence.save(self.context)  # 增量保存

                # 阶段5: 自动验证
                if self.config.auto_validate:
                    self._report_progress("validating", "验证结果中...")
                    self._auto_validate(hypotheses, results)
                    self.context.state = SprintState.VALIDATED
                    self.persistence.save(self.context)  # 增量保存

                # 阶段6: 学习提取
                if self.config.auto_learn:
                    self._report_progress("learning", "提取学习中...")
                    learnings = self._extract_learnings(results)
                    self.context.learnings = learnings
                    self.context.state = SprintState.COMPLETED
                    self.persistence.save(self.context)  # 增量保存

            return self._build_result()

        except Exception as e:
            self.context.state = SprintState.FAILED
            self.persistence.save(self.context)  # 保存失败状态
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
        
        self.persistence.save(self.context)

        hypotheses = self._generate_hypotheses(self.context.clarified_requirement)
        self.context.hypotheses = hypotheses
        self.persistence.save(self.context)

        if self.config.auto_execute:
            results = self._execute_tasks()
            self.context.execution_results = results
            self.persistence.save(self.context)

            if self.config.auto_validate:
                self._auto_validate(hypotheses, results)
                self.persistence.save(self.context)

            if self.config.auto_learn:
                learnings = self._extract_learnings(results)
                self.context.learnings = learnings
                self.persistence.save(self.context)

        return self._build_result()

    def resume_sprint(self, sprint_id: str | None = None) -> SprintResult:
        """
        恢复中断的冲刺

        Args:
            sprint_id: 冲刺ID，如果为 None 则恢复最近的活跃冲刺

        Returns:
            SprintResult: 冲刺执行结果

        Raises:
            ValueError: 如果冲刺不存在
        """
        # 如果没有指定 sprint_id，获取最近的活跃冲刺
        if sprint_id is None:
            self.context = self.persistence.get_latest_active()
            if self.context is None:
                raise ValueError("没有找到可恢复的活跃冲刺")
        else:
            self.context = self.persistence.load(sprint_id)

        if self.context is None:
            raise ValueError(f"冲刺 {sprint_id} 不存在或已损坏")

        self._report_progress("resuming", f"恢复冲刺 {self.context.sprint_id}，当前状态: {self.context.state.value}")

        # 根据当前状态继续执行
        if self.context.state == SprintState.INITIALIZED:
            # 重新开始澄清需求
            return self.run_from_vague_description(
                self.context.original_input,
                clarifications_callback=None,
            )

        elif self.context.state == SprintState.CLARIFIED:
            # 从生成假设继续
            self._report_progress("generating_hypotheses", "生成假设中...")
            hypotheses = self._generate_hypotheses(self.context.clarified_requirement)
            self.context.hypotheses = hypotheses
            self.context.state = SprintState.HYPOTHESES_GENERATED
            self.persistence.save(self.context)
            return self._continue_from_hypotheses()

        elif self.context.state == SprintState.HYPOTHESES_GENERATED:
            return self._continue_from_hypotheses()

        elif self.context.state == SprintState.TASKS_DECOMPOSED:
            return self._continue_from_execution()

        elif self.context.state == SprintState.EXECUTED:
            return self._continue_from_validation()

        elif self.context.state == SprintState.VALIDATED:
            return self._continue_from_learning()

        elif self.context.state == SprintState.COMPLETED:
            self._report_progress("completed", "冲刺已完成")
            return self._build_result()

        elif self.context.state == SprintState.FAILED:
            self._report_progress("failed", "冲刺之前失败，请检查错误日志")
            return self._build_result()

        return self._build_result()

    def _continue_from_hypotheses(self) -> SprintResult:
        """从假设生成后继续执行"""
        self._report_progress("decomposing_tasks", "分解任务中...")
        self.context.state = SprintState.TASKS_DECOMPOSED
        self.persistence.save(self.context)

        if self.config.auto_execute:
            return self._continue_from_execution()
        
        return self._build_result()

    def _continue_from_execution(self) -> SprintResult:
        """从任务分解后继续执行"""
        if self.config.auto_execute:
            self._report_progress("executing", "并行执行中...")
            results = self._execute_tasks()
            self.context.execution_results = results
            self.context.state = SprintState.EXECUTED
            self.persistence.save(self.context)

            if self.config.auto_validate:
                return self._continue_from_validation()
        
        return self._build_result()

    def _continue_from_validation(self) -> SprintResult:
        """从执行后继续验证"""
        if self.config.auto_validate:
            self._report_progress("validating", "验证结果中...")
            self._auto_validate(self.context.hypotheses, self.context.execution_results)
            self.context.state = SprintState.VALIDATED
            self.persistence.save(self.context)

            if self.config.auto_learn:
                return self._continue_from_learning()
        
        return self._build_result()

    def _continue_from_learning(self) -> SprintResult:
        """从验证后继续学习提取"""
        if self.config.auto_learn:
            self._report_progress("learning", "提取学习中...")
            learnings = self._extract_learnings(self.context.execution_results)
            self.context.learnings = learnings
            self.context.state = SprintState.COMPLETED
            self.persistence.save(self.context)
        
        return self._build_result()

    def get_active_sprints(self) -> List[str]:
        """
        获取活跃冲刺列表

        Returns:
            活跃冲刺ID列表
        """
        active_states = [
            "initialized",
            "clarified", 
            "hypotheses_generated",
            "tasks_decomposed",
            "executed",
            "validated",
        ]
        
        active_sprints = []
        for state in active_states:
            sprints = self.persistence.list_sprints(status=state)
            active_sprints.extend([s["sprint_id"] for s in sprints])
        
        return active_sprints

    def list_all_sprints(self, status: str | None = None) -> List[Dict[str, Any]]:
        """
        列出所有冲刺

        Args:
            status: 可选的状态过滤

        Returns:
            冲刺信息列表
        """
        return self.persistence.list_sprints(status=status)

    def get_sprint_info(self, sprint_id: str) -> Dict[str, Any] | None:
        """
        获取冲刺信息

        Args:
            sprint_id: 冲刺ID

        Returns:
            冲刺信息字典
        """
        context = self.persistence.load(sprint_id)
        if context is None:
            return None
        
        return {
            "sprint_id": context.sprint_id,
            "state": context.state.value,
            "original_input": context.original_input,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "hypotheses_count": len(context.hypotheses) if context.hypotheses else 0,
            "execution_results_count": len(context.execution_results) if context.execution_results else 0,
            "learnings_count": len(context.learnings) if context.learnings else 0,
        }

    def delete_sprint(self, sprint_id: str) -> bool:
        """
        删除冲刺

        Args:
            sprint_id: 冲刺ID

        Returns:
            删除是否成功
        """
        return self.persistence.delete(sprint_id)

    def archive_sprint(self, sprint_id: str) -> bool:
        """
        归档冲刺

        Args:
            sprint_id: 冲刺ID

        Returns:
            归档是否成功
        """
        return self.persistence.archive(sprint_id)

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
        callback: Callable[[str], str] | None,
    ) -> ClarifiedRequirement:
        """澄清需求"""
        return self.clarifier.clarify(
            vague_input,
            interactive_callback=callback,
        )

    def _generate_hypotheses(self, requirement: ClarifiedRequirement) -> List[Any]:
        """生成假设"""
        raw_hypotheses = self.hypothesis_generator.generate(requirement)
        return raw_hypotheses

    def _execute_tasks(self) -> List[Dict[str, Any]]:
        """
        执行任务

        优先使用 OrchestratorClient 执行，其次使用 ExecutionEngine。
        """
        if not self.context or not self.context.hypotheses:
            return []

        results: List[Dict[str, Any]] = []

        # 优先使用 OrchestratorClient 执行
        if self._orchestrator and self._orchestrator.supports(
            self._get_capability("task_execution")
        ):
            return self._execute_with_orchestrator()

        # 回退到 ExecutionEngine
        return self._execute_with_engine()

    def _get_capability(self, name: str):
        """获取 OrchestratorCapability"""
        from ..orchestrator import OrchestratorCapability
        return getattr(OrchestratorCapability, name.upper(), None)

    def _execute_with_orchestrator(self) -> List[Dict[str, Any]]:
        """使用 OrchestratorClient 执行任务"""
        if not self.context or not self._orchestrator:
            return []

        results: List[Dict[str, Any]] = []

        for i, h in enumerate(self.context.hypotheses):
            # 支持 GeneratedHypothesis 对象和字典两种格式
            if hasattr(h, 'statement'):
                statement = h.statement
                hypothesis_id = f"h{i}"
            else:
                h_dict = h if isinstance(h, dict) else {}
                statement = h_dict.get("statement", "")
                hypothesis_id = h_dict.get("hypothesis_id", f"h{i}")

            try:
                response = self._orchestrator.execute(
                    prompt=statement,
                    repo_root=str(self.storage_path),
                )

                result = {
                    "task_id": f"task-{i}",
                    "hypothesis_id": hypothesis_id,
                    "success": response.finish_reason == "stop",
                    "state": "completed" if response.finish_reason == "stop" else "failed",
                    "provider_results": {
                        "orchestrator": {
                            "success": response.finish_reason == "stop",
                            "output": response.content,
                        }
                    },
                    "duration_seconds": 0,
                    "errors": [] if response.finish_reason == "stop" else [response.finish_reason],
                }
                results.append(result)

            except Exception as e:
                result = {
                    "task_id": f"task-{i}",
                    "hypothesis_id": hypothesis_id,
                    "success": False,
                    "state": "failed",
                    "errors": [str(e)],
                }
                results.append(result)

        return results

    def _execute_with_engine(self) -> List[Dict[str, Any]]:
        """使用 ExecutionEngine 执行任务（向后兼容）"""
        # 从配置获取参数，初始化调度器和执行引擎
        scheduler = TaskScheduler(providers=self.config.providers)
        engine = ExecutionEngine(
            providers=self.config.providers,
            default_timeout=self.config.default_timeout,
        )

        # 将假设转换为调度器需要的格式
        hypotheses_for_scheduler = []
        for i, h in enumerate(self.context.hypotheses):
            # 支持 GeneratedHypothesis 对象和字典两种格式
            if hasattr(h, 'statement'):
                h_dict = {
                    "hypothesis_id": f"h{i}",
                    "statement": h.statement,
                    "type": h.hypothesis_type.value if hasattr(h.hypothesis_type, 'value') else str(h.hypothesis_type),
                    "priority": h.priority,
                    "dependencies": h.dependencies or [],
                    "description": h.validation_method,
                }
            else:
                h_dict = h if isinstance(h, dict) else {}
                h_dict.setdefault("hypothesis_id", f"h{i}")
            hypotheses_for_scheduler.append(h_dict)

        # 调度任务
        assignments = scheduler.schedule(hypotheses_for_scheduler)

        # 执行任务
        results = []
        while True:
            # 获取下一批可执行的任务
            batch = scheduler.get_next_batch(max_tasks=self.config.max_parallel_tasks)
            if not batch:
                break

            for assignment in batch:
                # 生成任务提示
                prompt = scheduler.generate_task_prompt(assignment)

                # 执行任务
                try:
                    exec_result = engine.execute(
                        prompt=prompt,
                        repo_root=assignment.working_directory or "."
                    )

                    result = {
                        "task_id": assignment.task_id,
                        "hypothesis_id": assignment.hypothesis_id,
                        "success": exec_result.success,
                        "state": exec_result.terminal_state.value,
                        "provider_results": {
                            pid: {"success": r.success, "output": r.output if hasattr(r, 'output') else str(r)}
                            for pid, r in exec_result.provider_results.items()
                        },
                        "duration_seconds": exec_result.duration_seconds,
                        "errors": exec_result.errors,
                    }

                    if exec_result.success:
                        scheduler.mark_completed(assignment.task_id, result)
                    else:
                        scheduler.mark_failed(assignment.task_id, ", ".join(exec_result.errors))

                    results.append(result)

                except Exception as e:
                    result = {
                        "task_id": assignment.task_id,
                        "hypothesis_id": assignment.hypothesis_id,
                        "success": False,
                        "state": "failed",
                        "errors": [str(e)],
                    }
                    scheduler.mark_failed(assignment.task_id, str(e))
                    results.append(result)

        return results

    def _auto_validate(self, hypotheses: List[Any], results: List[Dict[str, Any]]):
        """自动验证假设"""
        if not self.context:
            return

        # 存储验证结果
        self.context.validation_results = []

        for hypothesis in hypotheses:
            # 将假设转换为字典格式
            if hasattr(hypothesis, 'statement'):
                h_dict = {
                    "hypothesis_id": getattr(hypothesis, 'hypothesis_id', ''),
                    "statement": hypothesis.statement,
                    "success_criteria": hypothesis.success_criteria if hasattr(hypothesis, 'success_criteria') else [],
                }
            else:
                h_dict = hypothesis if isinstance(hypothesis, dict) else {}

            # 过滤出与该假设相关的执行结果
            related_results = [
                r for r in results
                if r.get("hypothesis_id") == h_dict.get("hypothesis_id")
            ] if h_dict.get("hypothesis_id") else results

            # 执行验证
            validation_result = self.validator.validate(h_dict, related_results)
            self.context.validation_results.append(validation_result)

    def _extract_learnings(self, results: List[Dict[str, Any]]) -> List[ExtractedLearning]:
        """从执行结果中提取学习"""
        return self.learning_extractor.extract(results)

    def _build_result(self) -> SprintResult:
        """构建最终结果"""
        req_dict = {}
        if self.context and self.context.clarified_requirement:
            req_dict = {
                "summary": getattr(self.context.clarified_requirement, 'summary', ''),
            }

        # 转换假设
        hypotheses_data = []
        for h in (self.context.hypotheses if self.context else []):
            if hasattr(h, 'statement'):
                hypotheses_data.append({
                    "statement": h.statement,
                    "priority": getattr(h, 'priority', 'medium'),
                    "risk_level": getattr(h, 'risk_level', 'medium'),
                })

        # 转换学习
        learnings_data = []
        for l in (self.context.learnings if self.context else []):
            learnings_data.append({
                "phase": getattr(l, 'phase', ''),
                "insights": getattr(l, 'insights', []),
            })

        return SprintResult(
            sprint_id=self.context.sprint_id if self.context else "",
            success=self.context.state == SprintState.COMPLETED if self.context else False,
            state=self.context.state if self.context else SprintState.FAILED,
            clarified_requirement=req_dict,
            hypotheses=hypotheses_data,
            execution_results=self.context.execution_results if self.context else [],
            learnings=learnings_data,
            next_steps=self.get_next_steps() if hasattr(self, 'get_next_steps') else [],
            summary=self._generate_summary() if hasattr(self, '_generate_summary') else "",
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
        """保存冲刺上下文（使用持久化管理器）"""
        if self.context:
            self.persistence.save(self.context)

    def _load_context(self, sprint_id: str) -> SprintContext | None:
        """加载冲刺上下文（使用持久化管理器）"""
        return self.persistence.load(sprint_id)
