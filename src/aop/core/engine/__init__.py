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
        
        with ThreadPoolExecutor(max_workers=len(self.providers)) as executor:
            futures = {}
            for pid in self.providers:
                adapter = self._registry.get(pid)
                if adapter:
                    presence = adapter.detect()
                    if presence.detected:
                        futures[executor.submit(adapter.run, task)] = pid
                    else:
                        errors.append(f"{pid}: not available")
            
            for future in as_completed(futures):
                pid = futures[future]
                try:
                    results[pid] = future.result()
                except Exception as e:
                    errors.append(f"{pid}: {str(e)}")
                    results[pid] = TaskResult(task_id=task_id, provider=pid, success=False, error=str(e))
        
        success_count = sum(1 for r in results.values() if r.success)
        state = TaskState.COMPLETED if success_count == len(results) else TaskState.FAILED
        return ExecutionResult(task_id=task_id, success=state == TaskState.COMPLETED, terminal_state=state,
                               provider_results=results, duration_seconds=time.time() - start, errors=errors)


__all__ = [
    "ExecutionResult",
    "ExecutionEngine",
    "ReviewEngine",
    "ReviewPolicy",
    "ReviewRequest",
    "ReviewResult",
]
