"""
动态任务调度器
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Set


@dataclass
class TaskAssignment:
    """任务分配"""
    task_id: str
    hypothesis_id: str
    provider: str
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    estimated_tokens: int = 1000
    status: str = "pending"
    result: dict | None = None
    retry_count: int = 0
    max_retries: int = 3
    working_directory: str | None = None  # 工作目录路径
    task_description: str | None = None   # 任务描述


class TaskScheduler:
    """动态任务调度器"""
    
    def __init__(self, providers: List[str] | None = None):
        self.providers = providers or ["claude", "codex", "gemini", "qwen"]
        self.assignments: Dict[str, TaskAssignment] = {}
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.provider_strengths = {
            "claude": ["analysis", "writing", "reasoning", "code_review"],
            "codex": ["coding", "refactoring", "debugging", "testing"],
            "gemini": ["analysis", "multimodal", "creative"],
            "qwen": ["coding", "analysis", "translation"],
        }
    
    def schedule(self, hypotheses: List[dict], working_directory: str | None = None) -> List[TaskAssignment]:
        assignments = []
        for i, h in enumerate(hypotheses):
            hid = h.get("hypothesis_id", f"h{i}")
            assignment = TaskAssignment(
                task_id=f"task_{hid}",
                hypothesis_id=hid,
                provider=self._select_provider(h.get("type", "general")),
                priority=self._calculate_priority(h),
                dependencies=h.get("dependencies", []),
                estimated_tokens=self._estimate_tokens(h),
                working_directory=working_directory or h.get("working_directory"),
                task_description=h.get("description"),
            )
            self.assignments[assignment.task_id] = assignment
            assignments.append(assignment)
        return assignments
    
    def get_next_batch(self, max_tasks: int = 5) -> List[TaskAssignment]:
        batch = [t for t in self.assignments.values() if t.status == "pending" and self._dependencies_met(t)]
        batch.sort(key=lambda t: t.priority, reverse=True)
        return batch[:max_tasks]
    
    def mark_completed(self, task_id: str, result: dict) -> None:
        if task_id in self.assignments:
            self.assignments[task_id].status = "completed"
            self.assignments[task_id].result = result
            self.completed_tasks.add(task_id)
    
    def mark_failed(self, task_id: str, error: str) -> None:
        if task_id in self.assignments:
            task = self.assignments[task_id]
            task.retry_count += 1
            task.status = "failed" if task.retry_count >= task.max_retries else "pending"
            if task.status == "failed":
                self.failed_tasks.add(task_id)
    
    def rebalance(self) -> None:
        for task_id in list(self.failed_tasks):
            task = self.assignments[task_id]
            for provider in self.providers:
                if provider != task.provider:
                    task.provider = provider
                    task.status = "pending"
                    task.retry_count = 0
                    self.failed_tasks.discard(task_id)
                    break
    
    def get_statistics(self) -> dict:
        total = len(self.assignments)
        return {
            "total": total,
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "pending": sum(1 for t in self.assignments.values() if t.status == "pending"),
            "success_rate": len(self.completed_tasks) / total if total > 0 else 0,
        }
    
    def _select_provider(self, task_type: str) -> str:
        for provider, strengths in self.provider_strengths.items():
            if task_type in strengths:
                return provider
        return self.providers[0]
    
    def _calculate_priority(self, hypothesis: dict) -> int:
        return {"critical": 100, "high": 75, "medium": 50, "low": 25}.get(hypothesis.get("priority", "medium"), 50)
    
    def _estimate_tokens(self, hypothesis: dict) -> int:
        return max(len(hypothesis.get("statement", "")) // 4 * 3, 1000)
    
    def _dependencies_met(self, task: TaskAssignment) -> bool:
        return all(dep in self.completed_tasks for dep in task.dependencies)
    
    def generate_task_prompt(self, assignment: TaskAssignment, include_timeout_extension: bool = True) -> str:
        """生成子 Agent 任务提示，包含工作目录信息和超时延长说明"""
        lines = [f"## 任务 ID: {assignment.task_id}"]
        
        if assignment.working_directory:
            lines.append(f"**工作目录**: {assignment.working_directory}")
            lines.append(f"请首先执行: `cd {assignment.working_directory}`")
        
        if assignment.task_description:
            lines.append("**任务描述**:")
            lines.append(assignment.task_description)
        
        # 添加超时延长说明
        if include_timeout_extension:
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("## 超时延长机制")
            lines.append("")
            lines.append("如果你在执行任务时发现剩余时间不足，可以申请延长超时。")
            lines.append("")
            lines.append("**申请方式**：输出以下格式的请求：")
            lines.append("")
            lines.append("```")
            lines.append("[TIMEOUT_EXTENSION_REQUEST]")
            lines.append('{')
            lines.append('  "requested_seconds": 300,')
            lines.append('  "reason": "任务复杂，需要更多时间",')
            lines.append('  "progress_summary": "已完成 50%"')
            lines.append('}')
            lines.append("[/TIMEOUT_EXTENSION_REQUEST]")
            lines.append("```")
            lines.append("")
            lines.append("**参数说明**：")
            lines.append("- `requested_seconds`: 请求延长的秒数（建议 300-600）")
            lines.append("- `reason`: 延长原因")
            lines.append("- `progress_summary`: 当前进度摘要")
            lines.append("")
            lines.append("**注意事项**：")
            lines.append("- 每个任务最多延长 3 次")
            lines.append("- 总延长时间不超过 30 分钟")
            lines.append("- 在申请延长前，请先保存当前进度")
        
        return "\n".join(lines)
