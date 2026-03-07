"""Execution engine."""

from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List

from ..adapter import get_adapter_registry
from ..types import ProviderId, TaskInput, TaskResult, TaskState, NormalizedFinding
from .review import ReviewEngine, ReviewPolicy, ReviewRequest, ReviewResult


@dataclass
class ExecutionResult:
    task_id: str
    success: bool
    terminal_state: TaskState
    provider_results: Dict[ProviderId, TaskResult] = field(default_factory=dict)
    all_findings: List[NormalizedFinding] = field(default_factory=list)
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)


class ExecutionEngine:
    def __init__(self, providers=None, default_timeout=600):
        self.providers = providers or ["claude", "codex"]
        self.default_timeout = default_timeout
        self._registry = get_adapter_registry()
    
    def detect_providers(self):
        results = {}
        for pid in self.providers:
            adapter = self._registry.get(pid)
            if adapter:
                results[pid] = adapter.detect()
        return results
    
    def execute(self, prompt, repo_root="."):
        task_id = "task-" + hashlib.sha256((prompt + str(time.time())).encode()).hexdigest()[:8]
        start = time.time()
        task = TaskInput(task_id=task_id, prompt=prompt, repo_root=repo_root, target_paths=["."], timeout_seconds=self.default_timeout)
        results = {}
        errors = []
        run_refs = {}
        
        # 启动所有 provider
        for pid in self.providers:
            adapter = self._registry.get(pid)
            if adapter:
                presence = adapter.detect()
                if presence.detected:
                    try:
                        ref = adapter.run(task)
                        run_refs[pid] = ref
                    except Exception as e:
                        errors.append(f"{pid}: {str(e)}")
                else:
                    errors.append(f"{pid}: not available")
        
        # 等待所有任务完成
        import time as time_module
        timeout = self.default_timeout
        poll_interval = 1.0
        elapsed = 0.0
        
        while elapsed < timeout and run_refs:
            for pid, ref in list(run_refs.items()):
                adapter = self._registry.get(pid)
                if adapter:
                    try:
                        status = adapter.poll(ref)
                        if status.completed:
                            # 创建 TaskResult
                            success = status.attempt_state == "SUCCEEDED"
                            results[pid] = TaskResult(
                                task_id=task_id,
                                provider=pid,
                                success=success,
                                error=status.message if not success else None,
                            )
                            del run_refs[pid]
                    except Exception as e:
                        errors.append(f"{pid}: poll error - {str(e)}")
                        results[pid] = TaskResult(task_id=task_id, provider=pid, success=False, error=str(e))
                        del run_refs[pid]
            
            if run_refs:
                time_module.sleep(poll_interval)
                elapsed += poll_interval
        
        # 超时处理
        for pid in run_refs:
            errors.append(f"{pid}: timeout")
            results[pid] = TaskResult(task_id=task_id, provider=pid, success=False, error="timeout")
        
        success_count = sum(1 for r in results.values() if r.success)
        state = TaskState.COMPLETED if success_count == len(results) else TaskState.FAILED
        return ExecutionResult(task_id=task_id, success=state == TaskState.COMPLETED, terminal_state=state,
                               provider_results=results, duration_seconds=time.time() - start, errors=errors)
    
    def run(self, prompt, repo_root=".", target_paths=None, task_id=None, 
            include_token_usage=False, synthesize=False, synthesis_provider=None):
        """
        Alias for execute() for CLI compatibility.
        
        Args:
            prompt: The task prompt
            repo_root: Repository root path
            target_paths: Target paths to analyze
            task_id: Optional task ID
            include_token_usage: Whether to include token usage
            synthesize: Whether to run synthesis
            synthesis_provider: Provider to use for synthesis
            
        Returns:
            ExecutionResult
        """
        return self.execute(prompt=prompt, repo_root=repo_root)


__all__ = [
    "ExecutionResult",
    "ExecutionEngine",
    "ReviewEngine",
    "ReviewPolicy",
    "ReviewRequest",
    "ReviewResult",
]
