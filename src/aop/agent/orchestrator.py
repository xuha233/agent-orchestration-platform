"""
AgentOrchestrator - Unified orchestration entry point

Supports multiple AI coding tools:
- Claude Code (claude-code)
- OpenCode (opencode)
- Codex CLI (codex)
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from enum import Enum

from .types import (
    SprintContext,
    SprintState,
    ClarifiedRequirement,
    GeneratedHypothesis,
    AgentDriverConfig,
    HypothesisGenerationConfig,
)
from .clarifier import RequirementClarifier, ClarificationConfig
from .hypothesis_generator import HypothesisGenerator
from .validator import AutoValidator
from .learning_extractor import LearningExtractor
from .persistence import SprintPersistence
from ..llm import LLMClient, LLMMessage


class ExecutorType(Enum):
    """Supported executor types"""
    CLAUDE_CODE = "claude-code"
    OPENCODE = "opencode"
    CODEX = "codex"


@dataclass
class ExecutorInfo:
    """Information about an available executor"""
    executor_type: ExecutorType
    available: bool
    version: str | None = None
    path: str | None = None
    error: str | None = None


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


@dataclass
class SprintResult:
    """Sprint execution result"""
    sprint_id: str
    success: bool
    state: SprintState
    clarified_requirement: Dict[str, Any]
    hypotheses: List[Dict[str, Any]]
    execution_results: List[Dict[str, Any]]
    learnings: List[Dict[str, Any]]
    next_steps: List[str]
    summary: str


class ExecutorDiscovery:
    """Discovers available executors on the system"""
    
    # Command names for each executor
    EXECUTOR_COMMANDS = {
        ExecutorType.CLAUDE_CODE: "claude",
        ExecutorType.OPENCODE: "opencode",
        ExecutorType.CODEX: "codex",
    }
    
    # Version flags for each executor
    VERSION_FLAGS = {
        ExecutorType.CLAUDE_CODE: ["--version"],
        ExecutorType.OPENCODE: ["--version"],
        ExecutorType.CODEX: ["--version"],
    }
    
    @classmethod
    def discover_all(cls) -> Dict[ExecutorType, ExecutorInfo]:
        """Discover all available executors"""
        results = {}
        for executor_type in ExecutorType:
            results[executor_type] = cls.check_executor(executor_type)
        return results
    
    @classmethod
    def check_executor(cls, executor_type: ExecutorType) -> ExecutorInfo:
        """Check if a specific executor is available"""
        command = cls.EXECUTOR_COMMANDS.get(executor_type)
        if not command:
            return ExecutorInfo(
                executor_type=executor_type,
                available=False,
                error=f"Unknown executor type: {executor_type}",
            )
        
        # Check if command exists in PATH
        command_path = shutil.which(command)
        if not command_path:
            return ExecutorInfo(
                executor_type=executor_type,
                available=False,
                error=f"Command '{command}' not found in PATH",
            )
        
        # Try to get version
        version = None
        try:
            version_flags = cls.VERSION_FLAGS.get(executor_type, ["--version"])
            result = subprocess.run(
                [command] + version_flags,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse version from output (first line, first word-like thing)
                version = result.stdout.strip().split('\n')[0][:50]
        except Exception:
            pass
        
        return ExecutorInfo(
            executor_type=executor_type,
            available=True,
            version=version,
            path=command_path,
        )
    
    @classmethod
    def get_available_executors(cls) -> List[ExecutorType]:
        """Get list of available executor types"""
        available = []
        for executor_type in ExecutorType:
            info = cls.check_executor(executor_type)
            if info.available:
                available.append(executor_type)
        return available
    
    @classmethod
    def get_best_executor(cls) -> ExecutorType:
        """Get the best available executor (preference order: claude-code > opencode > codex)"""
        preference_order = [
            ExecutorType.CLAUDE_CODE,
            ExecutorType.OPENCODE,
            ExecutorType.CODEX,
        ]
        
        for executor_type in preference_order:
            info = cls.check_executor(executor_type)
            if info.available:
                return executor_type
        
        # Default to claude-code even if not available
        return ExecutorType.CLAUDE_CODE


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
            self._executor_info = ExecutorDiscovery.discover_all()
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
        """Execute tasks using configured executor"""
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
        results = []
        for i, h in enumerate(self.context.hypotheses):
            if hasattr(h, 'statement'):
                task_prompt = f"Task: {h.statement}\n\n"
                if hasattr(h, 'validation_method'):
                    task_prompt += f"Validation: {h.validation_method}\n"
                
                result = {
                    "task_id": f"task_{i}",
                    "hypothesis_id": f"h{i}",
                    "executor": self.config.executor.value,
                    "prompt": task_prompt,
                    "success": True,  # Placeholder
                }
                results.append(result)
        
        return results
    
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
