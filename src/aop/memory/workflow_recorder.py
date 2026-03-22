# -*- coding: utf-8 -*-
"""Workflow-aware memory recording for AOP."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from ..primary.workspace import SettingsManager
from ..workflow.checks import CompletionDecision, GuardrailReport, PlanCheckReport
from ..workflow.types import GapClosurePlan, VerificationReport, WorkflowPlan, WorkflowRun
from .config import MemoryConfig, resolve_memory_config
from .service import MemoryService

logger = logging.getLogger(__name__)


class WorkflowMemoryRecorder:
    """Record workflow artifacts into the configured memory backend."""

    def __init__(
        self,
        workspace_path: Path | str,
        settings_manager: SettingsManager | None = None,
    ) -> None:
        base = Path(workspace_path)
        self.workspace_path = base.parent if base.name == ".aop" else base
        self.settings_manager = settings_manager or SettingsManager()

    def is_enabled(self) -> bool:
        """Return whether workflow memory writes should be attempted."""
        if not self.settings_manager.get_enable_mem0_memory():
            return False
        config = self._load_config()
        return config.enabled

    def record_plan(
        self,
        run: WorkflowRun,
        plan: WorkflowPlan,
        plan_check: PlanCheckReport,
    ) -> None:
        """Record plan and plan-check memory."""
        service = self._build_service()
        if service is None:
            return

        self._remember(
            service,
            content="\n".join(
                [
                    f"Workflow plan for {run.run_id}",
                    f"Summary: {plan.summary or 'N/A'}",
                    f"Goals: {self._join(plan.goals)}",
                    f"Verification: {self._join(plan.verification_steps)}",
                    f"Risks: {self._join(plan.risks)}",
                ]
            ),
            metadata={
                "type": "workflow_plan",
                "run_id": run.run_id,
                "phase": run.current_phase.value,
                "status": run.status,
                "issues": len(plan_check.issues),
            },
        )

    def record_verification(
        self,
        run: WorkflowRun,
        report: VerificationReport,
        gap_closure: GapClosurePlan | None = None,
    ) -> None:
        """Record verification and optional gap closure memory."""
        service = self._build_service()
        if service is None:
            return

        self._remember(
            service,
            content="\n".join(
                [
                    f"Workflow verification for {run.run_id}",
                    f"Verdict: {report.verdict}",
                    f"Summary: {report.summary or 'N/A'}",
                    f"Truths: {self._join(report.truths)}",
                    f"Gaps: {self._join(report.gaps)}",
                ]
            ),
            metadata={
                "type": "workflow_verification",
                "run_id": run.run_id,
                "phase": run.current_phase.value,
                "status": run.status,
                "verdict": report.verdict,
                "gap_count": len(report.gaps),
            },
        )

        if gap_closure is not None:
            self._remember(
                service,
                content="\n".join(
                    [
                        f"Gap closure plan for {run.run_id}",
                        f"Summary: {gap_closure.summary or 'N/A'}",
                        f"Repair tasks: {self._join(task.title for task in gap_closure.repair_tasks)}",
                        f"Next verification: {self._join(gap_closure.next_verification_steps)}",
                    ]
                ),
                metadata={
                    "type": "workflow_gap_closure",
                    "run_id": run.run_id,
                    "phase": run.current_phase.value,
                    "status": run.status,
                    "gap_count": len(gap_closure.gaps),
                },
            )

    def record_learnings(self, run: WorkflowRun, learnings: list[dict[str, Any]]) -> None:
        """Record learnings emitted by the workflow."""
        service = self._build_service()
        if service is None or not learnings:
            return

        self._remember(
            service,
            content="\n".join(
                [
                    f"Workflow learnings for {run.run_id}",
                    *[
                        f"- {learning.get('phase', 'unknown')}: {self._join(learning.get('insights', []) or [])}"
                        for learning in learnings
                    ],
                ]
            ),
            metadata={
                "type": "workflow_learning",
                "run_id": run.run_id,
                "phase": run.current_phase.value,
                "status": run.status,
                "learning_count": len(learnings),
            },
        )

    def record_completion(
        self,
        run: WorkflowRun,
        decision: CompletionDecision,
        guardrails: GuardrailReport | None = None,
    ) -> None:
        """Record completion gate output and optional guardrail report."""
        service = self._build_service()
        if service is None:
            return

        self._remember(
            service,
            content="\n".join(
                [
                    f"Workflow completion for {run.run_id}",
                    f"Passed: {decision.passed}",
                    f"Status: {decision.status}",
                    f"Summary: {decision.summary or 'N/A'}",
                    f"Reasons: {self._join(decision.reasons)}",
                ]
            ),
            metadata={
                "type": "workflow_completion",
                "run_id": run.run_id,
                "phase": run.current_phase.value,
                "status": decision.status,
                "passed": decision.passed,
            },
        )

        if guardrails is not None:
            self._remember(
                service,
                content="\n".join(
                    [
                        f"Workflow guardrails for {run.run_id}",
                        f"Should stop: {guardrails.should_stop}",
                        f"Summary: {guardrails.summary or 'N/A'}",
                        f"Categories: {self._join(guardrails.categories)}",
                        f"Reasons: {self._join(guardrails.reasons)}",
                    ]
                ),
                metadata={
                    "type": "workflow_guardrail",
                    "run_id": run.run_id,
                    "phase": run.current_phase.value,
                    "status": run.status,
                    "should_stop": guardrails.should_stop,
                },
            )

    def recall_follow_up_context(
        self,
        run: WorkflowRun,
        report: VerificationReport,
        limit: int = 3,
    ) -> list[str]:
        """Return compact memory hints relevant to current follow-up work."""
        service = self._build_service()
        if service is None:
            return []

        queries = [gap for gap in report.gaps[:2] if gap.strip()]
        if not queries and report.summary.strip():
            queries = [report.summary]

        hints: list[str] = []
        seen: set[str] = set()

        for query in queries:
            for memory in service.search(query, top_k=limit):
                metadata = memory.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                if metadata.get("run_id") == run.run_id:
                    continue
                memory_type = str(metadata.get("type", "general"))
                if not memory_type.startswith("workflow_"):
                    continue
                content = str(memory.get("content", "")).strip()
                if not content:
                    continue
                compact = content.splitlines()[0].strip()
                hint = f"{memory_type}: {compact[:120]}"
                if hint not in seen:
                    seen.add(hint)
                    hints.append(hint)
                if len(hints) >= limit:
                    return hints
        return hints

    def recall_verification_context(
        self,
        run: WorkflowRun,
        report: VerificationReport,
        limit: int = 2,
    ) -> list[str]:
        """Return compact prior memory hints to enrich verification evidence."""
        service = self._build_service()
        if service is None:
            return []

        queries = [gap for gap in report.gaps[:1] if gap.strip()]
        if not queries:
            queries = [truth for truth in report.truths[:1] if truth.strip()]
        if not queries and report.summary.strip():
            queries = [report.summary]

        hints: list[str] = []
        seen: set[str] = set()
        allowed_types = {"workflow_verification", "workflow_gap_closure", "workflow_learning"}

        for query in queries:
            for memory in service.search(query, top_k=limit):
                metadata = memory.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                if metadata.get("run_id") == run.run_id:
                    continue
                memory_type = str(metadata.get("type", "general"))
                if memory_type not in allowed_types:
                    continue
                content = str(memory.get("content", "")).strip()
                if not content:
                    continue
                compact = content.splitlines()[0].strip()
                hint = f"{memory_type}: {compact[:120]}"
                if hint not in seen:
                    seen.add(hint)
                    hints.append(hint)
                if len(hints) >= limit:
                    return hints
        return hints

    def recall_planning_context(
        self,
        run: WorkflowRun,
        plan: WorkflowPlan,
        limit: int = 2,
    ) -> list[str]:
        """Return compact memory hints that can improve the current plan."""
        service = self._build_service()
        if service is None:
            return []

        queries = [goal for goal in plan.goals[:1] if goal.strip()]
        if not queries and plan.summary.strip():
            queries = [plan.summary]
        if not queries:
            queries = [run.original_input]

        hints: list[str] = []
        seen: set[str] = set()
        allowed_types = {"workflow_plan", "workflow_verification", "workflow_learning", "workflow_completion"}

        for query in queries:
            for memory in service.search(query, top_k=limit):
                metadata = memory.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                if metadata.get("run_id") == run.run_id:
                    continue
                memory_type = str(metadata.get("type", "general"))
                if memory_type not in allowed_types:
                    continue
                content = str(memory.get("content", "")).strip()
                if not content:
                    continue
                compact = content.splitlines()[0].strip()
                hint = f"{memory_type}: {compact[:120]}"
                if hint not in seen:
                    seen.add(hint)
                    hints.append(hint)
                if len(hints) >= limit:
                    return hints
        return hints

    def _build_service(self) -> MemoryService | None:
        if not self.settings_manager.get_enable_mem0_memory():
            return None

        config = self._load_config()
        if not config.enabled:
            return None
        return MemoryService(config, workspace_path=self.workspace_path)

    def _load_config(self) -> MemoryConfig:
        return resolve_memory_config(
            self.workspace_path,
            global_enabled=self.settings_manager.get_enable_mem0_memory(),
        )

    def _remember(
        self,
        service: MemoryService,
        content: str,
        metadata: dict[str, Any],
    ) -> None:
        try:
            service.add(content, metadata=metadata)
        except Exception as exc:  # pragma: no cover - fallback safety
            logger.warning("workflow memory recording failed: %s", exc)

    def _join(self, values: Iterable[Any]) -> str:
        items = [str(value).strip() for value in values if str(value).strip()]
        return ", ".join(items) if items else "none"
