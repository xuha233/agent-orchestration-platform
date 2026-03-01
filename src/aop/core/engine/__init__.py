"""Execution engine."""

from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List

from ..adapter import get_adapter_registry
from ..types import ProviderId, TaskInput, TaskResult, TaskState, NormalizedFinding


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
        task = TaskInput(task_id=task_id, prompt=prompt, repo_root=repo_root, timeout_seconds=self.default_timeout)
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


@dataclass
class ReviewResult:
    task_id: str
    success: bool
    terminal_state: TaskState
    provider_results: Dict = field(default_factory=dict)
    all_findings: List = field(default_factory=list)
    deduplicated_findings: List = field(default_factory=list)
    duration_seconds: float = 0.0
    errors: List = field(default_factory=list)


class ReviewEngine:
    def __init__(self, providers=None, default_timeout=600):
        self.providers = providers or ["claude", "codex"]
        self.default_timeout = default_timeout
        self._registry = get_adapter_registry()
    
    def _generate_fingerprint(self, finding):
        key = finding.category + ":" + finding.title + ":" + finding.evidence.file
        return hashlib.sha256(key.encode()).hexdigest()[:12]
    
    def _deduplicate_findings(self, all_findings):
        fingerprint_map = {}
        for finding in all_findings:
            fp = self._generate_fingerprint(finding)
            if fp in fingerprint_map:
                existing = fingerprint_map[fp]
                merged_by = list(set(existing.detected_by + finding.detected_by))
                fingerprint_map[fp] = NormalizedFinding(
                    finding_id=existing.finding_id, severity=existing.severity, category=existing.category,
                    title=existing.title, evidence=existing.evidence, recommendation=existing.recommendation, detected_by=merged_by)
            else:
                fingerprint_map[fp] = finding
        return list(fingerprint_map.values())
    
    def review(self, prompt, repo_root="."):
        task_id = "review-" + hashlib.sha256((prompt + str(time.time())).encode()).hexdigest()[:8]
        start = time.time()
        review_prompt = "Review the following code and provide findings:\n\n" + prompt
        task = TaskInput(task_id=task_id, prompt=review_prompt, repo_root=repo_root, timeout_seconds=self.default_timeout)
        results = {}
        all_findings = []
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
                    result = future.result()
                    results[pid] = result
                    all_findings.extend(result.findings)
                    if not result.success and result.error:
                        errors.append(f"{pid}: {result.error}")
                except Exception as e:
                    errors.append(f"{pid}: {str(e)}")
                    results[pid] = TaskResult(task_id=task_id, provider=pid, success=False, error=str(e))
        
        deduped = self._deduplicate_findings(all_findings)
        success_count = sum(1 for r in results.values() if r.success)
        state = TaskState.COMPLETED if success_count > 0 else TaskState.FAILED
        return ReviewResult(task_id=task_id, success=state == TaskState.COMPLETED, terminal_state=state,
                            provider_results=results, all_findings=all_findings, deduplicated_findings=deduped,
                            duration_seconds=time.time() - start, errors=errors)
