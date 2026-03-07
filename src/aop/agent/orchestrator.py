"""
AgentOrchestrator - Unified orchestration entry point

Supports multiple AI coding tools:
- Claude Code (claude-code)
- OpenCode (opencode)
- Codex CLI (codex)
"""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Callable, Dict, Any

from .types import (
    SprintContext,
    SprintState,
    ClarifiedRequirement,
    GeneratedHypothesis,
    AgentDriverConfig,
    HypothesisGenerationConfig,
    SprintResult,
)
from .clarifier import RequirementClarifier, ClarificationConfig
from .hypothesis_generator import HypothesisGenerator
from .validator import AutoValidator
from .learning_extractor import LearningExtractor
from .persistence import SprintPersistence
from .preflight import PreFlightValidator, PreFlightStatus
from .executor import ExecutorType, ExecutorInfo, discover_all
from ..llm import LLMClient, LLMMessage
from .prompts import ORCHESTRATOR_SYSTEM_PROMPT, build_subagent_task


@dataclass
class OrchestrationConfig:
    """Orchestration configuration"""
    # LLM configuration
    llm_provider: str = "claude"
    llm_model: str = "claude-sonnet-4-20250514"

    # Executor configuration
    executor: ExecutorType = ExecutorType.CLAUDE_CODE
    exec_timeout: int = 600
    exec_max_parallel: int = 5

    # Workflow configuration
    auto_clarify: bool = True
    auto_generate_hypotheses: bool = True
    auto_execute: bool = True
    auto_validate: bool = True
    auto_learn: bool = True

    # Storage
    storage_path: Path | None = None

    # Callbacks
    progress_callback: Callable[[str, str, Dict[str, Any]], None] | None = None

    # Debug
    dry_run: bool = False
    verbose: bool = False


class AgentOrchestrator:
    """
    Unified agent orchestrator
    
    Usage:
    ``python
    orchestrator = AgentOrchestrator(
        llm_client=ClaudeClient(),
        config=OrchestrationConfig(executor=ExecutorType.OPENCODE)
    )
    result = orchestrator.orchestrate("Build an e-commerce system")
    ``
    """
    
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        config: OrchestrationConfig | None = None,
    ):
        self.llm = llm_client
        self.config = config or OrchestrationConfig()
        
        # Initialize components
        self.clarifier = RequirementClarifier(
            llm_client,
            ClarificationConfig(),
        )
        self.hypothesis_generator = HypothesisGenerator(
            llm_client,
        )
        self.validator = AutoValidator()
        self.learning_extractor = LearningExtractor()
        
        # Persistence
        storage_path = self.config.storage_path or Path(".aop")
        self.persistence = SprintPersistence(str(storage_path / "sprints"))
        
        # Current context
        self.context: SprintContext | None = None
        
        # Executor discovery
        self._executor_info: Dict[ExecutorType, ExecutorInfo] | None = None
    
    def discover_executors(self, force_refresh: bool = False) -> Dict[ExecutorType, ExecutorInfo]:
        """
        Discover available executors on the system

        Args:
            force_refresh: Force re-discovery even if cached

        Returns:
            Dict mapping executor types to their availability info
        """
        if force_refresh or self._executor_info is None:
            self._executor_info = discover_all()
        return self._executor_info
    
    def get_available_executors(self, force_refresh: bool = False) -> List[ExecutorType]:
        """Get list of available executor types"""
        info = self.discover_executors(force_refresh)
        return [et for et, ei in info.items() if ei.available]
    
    def get_executor_info(self, executor_type: ExecutorType | None = None) -> ExecutorInfo:
        """Get info about a specific executor (defaults to configured executor)"""
        et = executor_type or self.config.executor
        info = self.discover_executors()
        return info.get(et, ExecutorInfo(executor_type=et, available=False, error="Unknown"))
    
    def orchestrate(
        self,
        requirement: str,
        clarifications_callback: Callable[[str], str] | None = None,
        project_context: Dict[str, Any] | None = None,
    ) -> SprintResult:
        """
        Orchestrate the full development workflow
        
        Args:
            requirement: Requirement description (can be vague)
            clarifications_callback: Callback for clarification questions
            project_context: Project context (existing codebase info)
            
        Returns:
            Sprint execution result
        """
        # Initialize sprint
        self.context = SprintContext(
            sprint_id=self._generate_sprint_id(),
            original_input=requirement,
            state=SprintState.INITIALIZED,
        )
        self.persistence.save(self.context)
        
        try:
            # Phase 1: Clarify requirements
            if self.config.auto_clarify:
                self._report("clarify", "Clarifying requirements...")
                clarified = self.clarifier.clarify(
                    requirement,
                    interactive_callback=clarifications_callback,
                )
                self.context.clarified_requirement = clarified
                self.context.state = SprintState.CLARIFIED
                self.persistence.save(self.context)
            
            # Phase 2: Generate hypotheses
            if self.config.auto_generate_hypotheses:
                self._report("hypothesize", "Generating hypotheses...")
                hypotheses = self.hypothesis_generator.generate(
                    self.context.clarified_requirement,
                    project_context=project_context,
                )
                self.context.hypotheses = hypotheses
                self.context.state = SprintState.HYPOTHESES_GENERATED
                self.persistence.save(self.context)
            
            # Phase 3: Execute
            if self.config.auto_execute and not self.config.dry_run:
                self._report("execute", f"Executing with {self.config.executor.value}...")
                results = self._execute_tasks(project_context)
                self.context.execution_results = results
                self.context.state = SprintState.EXECUTED
                self.persistence.save(self.context)
            
            # Phase 4: Validate
            if self.config.auto_validate:
                self._report("validate", "Validating results...")
                self._validate_hypotheses()
                self.context.state = SprintState.VALIDATED
                self.persistence.save(self.context)
            
            # Phase 5: Learn
            if self.config.auto_learn:
                self._report("learn", "Extracting learnings...")
                learnings = self.learning_extractor.extract(
                    self.context.execution_results
                )
                self.context.learnings = learnings
                self.context.state = SprintState.COMPLETED
                self.persistence.save(self.context)
            
            return self._build_result()
            
        except Exception as e:
            self.context.state = SprintState.FAILED
            self.persistence.save(self.context)
            raise
    
    def resume(self, sprint_id: str | None = None) -> SprintResult:
        """Resume an interrupted sprint"""
        if sprint_id:
            self.context = self.persistence.load(sprint_id)
        else:
            self.context = self.persistence.get_latest_active()
        
        if not self.context:
            raise ValueError("No sprint found to resume")
        
        self._report("resume", f"Resuming sprint {self.context.sprint_id}")
        # Continue from current state...
        return self._build_result()
    
    def status(self, sprint_id: str | None = None) -> Dict[str, Any]:
        """Query sprint status"""
        if sprint_id:
            ctx = self.persistence.load(sprint_id)
        elif self.context:
            ctx = self.context
        else:
            ctx = self.persistence.get_latest_active()
        
        if not ctx:
            return {"status": "no_active_sprint"}
        
        return {
            "sprint_id": ctx.sprint_id,
            "state": ctx.state.value,
            "hypotheses_count": len(ctx.hypotheses) if ctx.hypotheses else 0,
        }
    
    # Private methods...
    def _execute_tasks(self, project_context: Dict[str, Any] | None) -> List[Dict[str, Any]]:
        """
        Execute tasks using configured executor
        
        基于 Anthropic 多 Agent 系统研究，并行执行可减少 90% 时间。
        使用 ThreadPoolExecutor 实现并行任务执行。
        """
        if not self.context or not self.context.hypotheses:
            return []
        
        # Use executor-specific command
        executor_commands = {
            ExecutorType.CLAUDE_CODE: "claude",
            ExecutorType.OPENCODE: "opencode",
            ExecutorType.CODEX: "codex",
        }
        
        command = executor_commands.get(self.config.executor, "claude")
        
        # Check if executor is available
        executor_info = self.get_executor_info()
        if not executor_info.available and not self.config.dry_run:
            self._report("warning", f"Executor {self.config.executor.value} not available: {executor_info.error}")
        
        # Generate tasks from hypotheses
        tasks = []
        for i, h in enumerate(self.context.hypotheses):
            if hasattr(h, 'statement'):
                task_prompt = self._build_task_prompt(h, i)
                tasks.append({
                    "task_id": f"task_{i}",
                    "hypothesis_id": f"h{i}",
                    "executor": self.config.executor.value,
                    "prompt": task_prompt,
                    "hypothesis": h,
                })
        
        # 并行执行（Anthropic 推荐：并行工具调用可减少 90% 时间）
        results = self._execute_parallel(tasks)
        
        return results
    

    def _preflight_check(self, task: Dict[str, Any]) -> "PreFlightResult":
        """
        执行任务前预检（Anthropic 推荐：避免重复执行）
        
        检查项：
        1. 代码是否已存在
        2. 任务是否已完成
        3. 环境是否就绪
        """
        validator = PreFlightValidator(self.config.storage_path or Path("."))
        
        # 构建预检任务
        preflight_task = {
            "objective": task.get("prompt", ""),
            "success_criteria": [],
        }
        
        # 从 hypothesis 提取成功标准
        hypothesis = task.get("hypothesis")
        if hypothesis:
            criteria = getattr(hypothesis, 'success_criteria', [])
            if criteria:
                preflight_task["success_criteria"] = list(criteria) if isinstance(criteria, (list, tuple)) else [str(criteria)]
        
        return validator.validate(preflight_task, hypothesis)
    def _build_task_prompt(self, hypothesis: Any, index: int) -> str:
        """
        构建任务 prompt（Anthropic 推荐格式）
        
        包含：目标、输出格式、工具指导、边界
        """
        prompt_parts = []
        
        # 核心陈述
        statement = getattr(hypothesis, 'statement', 'Unknown task')
        prompt_parts.append(f"Task: {statement}\n\n")
        
        # 目标（Anthropic 推荐）
        objective = getattr(hypothesis, 'objective', '')
        if objective:
            prompt_parts.append(f"Objective: {objective}\n")
        
        # 输出格式（Anthropic 推荐）
        output_format = getattr(hypothesis, 'output_format', '')
        if output_format:
            prompt_parts.append(f"Output Format: {output_format}\n")
        
        # 工具指导（Anthropic 推荐）
        tools_guidance = getattr(hypothesis, 'tools_guidance', '')
        if tools_guidance:
            prompt_parts.append(f"Tools Guidance: {tools_guidance}\n")
        
        # 边界（Anthropic 推荐）
        boundaries = getattr(hypothesis, 'boundaries', '')
        if boundaries:
            prompt_parts.append(f"Boundaries: {boundaries}\n")
        
        # 验证方法
        validation_method = getattr(hypothesis, 'validation_method', '')
        if validation_method:
            prompt_parts.append(f"Validation: {validation_method}\n")
        
        # 成功标准
        success_criteria = getattr(hypothesis, 'success_criteria', [])
        if success_criteria:
            prompt_parts.append(f"Success Criteria:\n")
            for criterion in success_criteria:
                prompt_parts.append(f"  - {criterion}\n")
        
        # 预估调用次数（Anthropic 推荐）
        effort_budget = getattr(hypothesis, 'effort_budget', 10)
        prompt_parts.append(f"\nEffort Budget: ~{effort_budget} tool calls")
        
        return ''.join(prompt_parts)
    
    def _execute_parallel(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        并行执行任务
        
        基于 Anthropic 研究：
        - 并行工具调用可减少 90% 时间
        - 使用 ThreadPoolExecutor 限制并发数
        """
        if not tasks:
            return []
        
        results = []
        max_workers = min(self.config.exec_max_parallel, len(tasks))
        
        # Dry run 模式：直接返回占位结果
        if self.config.dry_run:
            for task in tasks:
                results.append({
                    "task_id": task["task_id"],
                    "hypothesis_id": task["hypothesis_id"],
                    "executor": task["executor"],
                    "prompt": task["prompt"],
                    "success": True,
                    "output": "[Dry run - no actual execution]",
                })
            return results
        
        # 并行执行
        self._report("execute", f"Executing {len(tasks)} tasks in parallel (max {max_workers} workers)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self._execute_single_task, task): task
                for task in tasks
            }
            
            # 收集结果
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result(timeout=self.config.exec_timeout)
                    results.append(result)
                    self._report("task_complete", f"Task {task['task_id']} completed")
                except Exception as e:
                    results.append({
                        "task_id": task["task_id"],
                        "hypothesis_id": task["hypothesis_id"],
                        "executor": task["executor"],
                        "success": False,
                        "error": str(e),
                    })
                    self._report("task_error", f"Task {task['task_id']} failed: {e}")
        
        return results
    
    def _execute_single_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个任务（在线程池中运行）"""
        # TODO: 实际调用 executor（claude-code / opencode / codex）
        # 目前返回占位结果
        return {
            "task_id": task["task_id"],
            "hypothesis_id": task["hypothesis_id"],
            "executor": task["executor"],
            "prompt": task["prompt"],
            "success": True,
            "output": "[Execution placeholder - integrate with actual executor]",
        }
    
    def _validate_hypotheses(self):
        """Validate hypotheses"""
        if not self.context:
            return
        
        self.context.validation_results = []
        for hypothesis in self.context.hypotheses:
            h_dict = {"statement": getattr(hypothesis, 'statement', '')}
            validation_result = self.validator.validate(h_dict, self.context.execution_results)
            self.context.validation_results.append(validation_result)
    
    def _build_result(self) -> SprintResult:
        """Build final result"""
        req_dict = {}
        if self.context and self.context.clarified_requirement:
            req_dict = {
                "summary": getattr(self.context.clarified_requirement, 'summary', ''),
            }
        
        return SprintResult(
            sprint_id=self.context.sprint_id if self.context else "",
            success=self.context.state == SprintState.COMPLETED if self.context else False,
            state=self.context.state if self.context else SprintState.INITIALIZED,
            clarified_requirement=req_dict,
            hypotheses=[
                {"statement": getattr(h, 'statement', '')}
                for h in (self.context.hypotheses or [])
            ],
            execution_results=self.context.execution_results if self.context else [],
            learnings=[],
            next_steps=[],
            summary=f"Sprint completed with {len(self.context.hypotheses or [])} hypotheses",
        )
    
    def _generate_sprint_id(self) -> str:
        timestamp = datetime.now().isoformat()
        return f"sprint-{hashlib.sha256(timestamp.encode()).hexdigest()[:8]}"
    
    def _report(self, stage: str, message: str, data: Dict[str, Any] | None = None):
        if self.config.progress_callback:
            self.config.progress_callback(stage, message, data or {})
        if self.config.verbose:
            print(f"[{stage}] {message}")


# Convenience function for quick orchestration
def orchestrate(
    requirement: str,
    executor: ExecutorType = ExecutorType.CLAUDE_CODE,
    llm_client: LLMClient | None = None,
    **kwargs,
) -> SprintResult:
    """
    Convenience function for quick orchestration
    
    Args:
        requirement: The requirement to orchestrate
        executor: The executor to use
        llm_client: Optional LLM client
        **kwargs: Additional config options
        
    Returns:
        Sprint execution result
    """
    config = OrchestrationConfig(executor=executor, **kwargs)
    orchestrator = AgentOrchestrator(llm_client=llm_client, config=config)
    return orchestrator.orchestrate(requirement)





