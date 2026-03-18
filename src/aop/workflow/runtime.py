"""Workflow runtime coordination for AOP."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List

from .artifacts import WorkflowArtifactManager
from .checks import CompletionGate, GuardrailReport, WorkflowLoopDetector, WorkflowPlanChecker
from .types import (
    GapClosurePlan,
    GapItem,
    VerificationCheck,
    VerificationReport,
    WorkflowPhase,
    WorkflowPlan,
    WorkflowRun,
    WorkflowTask,
)

if TYPE_CHECKING:
    from ..agent.types import SprintContext


class WorkflowRuntime:
    """Owns workflow phase state, artifacts, gates, and repair loop decisions."""

    def __init__(
        self,
        storage_path: Path,
        report_progress: Callable[[str, str], None] | None = None,
        execute_workflow_tasks: Callable[[List[WorkflowTask]], List[Dict[str, Any]]] | None = None,
    ):
        self.storage_path = Path(storage_path)
        self.report_progress = report_progress
        self.execute_workflow_tasks = execute_workflow_tasks

        self.workflow_artifacts = WorkflowArtifactManager(self.storage_path)
        self.plan_checker = WorkflowPlanChecker()
        self.completion_gate = CompletionGate()
        self.loop_detector = WorkflowLoopDetector()

        self.workflow_run: WorkflowRun | None = None
        self.latest_verification_report: VerificationReport | None = None
        self.latest_gap_closure_plan: GapClosurePlan | None = None
        self.latest_guardrail_report: GuardrailReport | None = None
        self.repair_attempts = 0

    def initialize(self, context: SprintContext) -> None:
        """Reset runtime state for a new sprint context."""
        self.latest_verification_report = None
        self.latest_gap_closure_plan = None
        self.latest_guardrail_report = None
        self.repair_attempts = 0
        self.workflow_run = WorkflowRun(
            run_id=context.sprint_id,
            original_input=context.original_input,
        )
        self.workflow_artifacts.initialize_run(self.workflow_run)

    def sync_metadata(self, context: SprintContext) -> None:
        """Sync run metadata from current sprint context."""
        if self.workflow_run is None:
            self.workflow_run = WorkflowRun(
                run_id=context.sprint_id,
                original_input=context.original_input,
            )

        clarified = context.clarified_requirement
        self.workflow_run.clarified_summary = getattr(clarified, "summary", "")
        self.workflow_run.success_criteria = list(
            getattr(clarified, "success_criteria", []) or []
        )
        self.workflow_run.hypothesis_ids = [
            self._get_hypothesis_id(hypothesis, index)
            for index, hypothesis in enumerate(context.hypotheses or [])
        ]
        self.workflow_artifacts.update_run(self.workflow_run)

    def update_phase(
        self,
        context: SprintContext,
        phase: WorkflowPhase,
        status: str = "running",
    ) -> None:
        """Update current workflow phase and persist metadata."""
        if self.workflow_run is None:
            self.workflow_run = WorkflowRun(
                run_id=context.sprint_id,
                original_input=context.original_input,
            )
        self.workflow_run.current_phase = phase
        self.workflow_run.status = status
        self.sync_metadata(context)

    def write_plan(self, context: SprintContext) -> None:
        """Build and persist PLAN.md plus plan check."""
        if not context.clarified_requirement:
            return
        self.update_phase(context, WorkflowPhase.PLAN)
        plan = self.build_workflow_plan(context)
        self.workflow_artifacts.write_plan(context.sprint_id, plan)
        self.workflow_artifacts.write_plan_check(
            context.sprint_id,
            self.plan_checker.check(plan),
        )

    def write_verification(self, context: SprintContext) -> None:
        """Build and persist verification artifacts."""
        report = self.build_verification_report(context)
        self.latest_verification_report = report
        self.workflow_artifacts.write_verification(context.sprint_id, report)
        if report.gaps:
            self.latest_gap_closure_plan = self.build_gap_closure_plan(report)
            self.workflow_artifacts.write_gap_closure(
                context.sprint_id,
                self.latest_gap_closure_plan,
            )
        else:
            self.latest_gap_closure_plan = None
            self.workflow_artifacts.clear_gap_closure(context.sprint_id)

    def write_learnings(self, context: SprintContext) -> None:
        """Persist learnings for the current run."""
        learnings = [
            {
                "phase": getattr(learning, "phase", ""),
                "insights": getattr(learning, "insights", []),
            }
            for learning in context.learnings
        ]
        self.workflow_artifacts.write_learnings(context.sprint_id, learnings)

    def write_execution(
        self,
        sprint_id: str,
        execution_results: List[Dict[str, Any]],
    ) -> None:
        """Persist execution results for the current run."""
        self.workflow_artifacts.write_execution(sprint_id, execution_results)

    def finalize(self, context: SprintContext, status: str, summary: str) -> None:
        """Persist completion and optional guardrail artifacts."""
        learnings = [
            {
                "phase": getattr(learning, "phase", ""),
                "insights": getattr(learning, "insights", []),
            }
            for learning in context.learnings or []
        ]
        decision = self.completion_gate.evaluate(
            verification_report=self.latest_verification_report,
            execution_results=context.execution_results,
            learnings=learnings,
        )
        final_phase = (
            WorkflowPhase.COMPLETE
            if decision.passed and status == "completed"
            else WorkflowPhase.GAP_CLOSE
        )
        final_status = decision.status if status == "completed" else status
        if self.latest_guardrail_report and self.latest_guardrail_report.should_stop:
            final_status = "needs_follow_up"
        self.update_phase(context, final_phase, status=final_status)
        self.workflow_artifacts.write_completion(context.sprint_id, decision)
        if self.latest_guardrail_report is not None:
            self.workflow_artifacts.write_guardrails(
                context.sprint_id,
                self.latest_guardrail_report,
            )
        self.workflow_artifacts.write_summary(context.sprint_id, summary)

    def run_gap_closure_cycle(
        self,
        context: SprintContext,
        auto_execute: bool,
        auto_validate: Callable[[List[Any], List[Dict[str, Any]]], None],
    ) -> None:
        """Run one bounded repair wave and re-validate."""
        if not auto_execute or self.execute_workflow_tasks is None:
            return
        if self.latest_gap_closure_plan is None:
            return
        if not self.latest_gap_closure_plan.repair_tasks:
            return
        if self.repair_attempts >= 1:
            self.latest_guardrail_report = self.loop_detector.evaluate(
                context.execution_results,
                repair_attempts=self.repair_attempts,
            )
            return

        self.repair_attempts += 1
        self._report("gap_closing", "执行有边界的修复任务中...")
        self.update_phase(context, WorkflowPhase.GAP_CLOSE)

        repair_results = self.execute_workflow_tasks(self.latest_gap_closure_plan.repair_tasks)
        context.execution_results.extend(repair_results)
        self.workflow_artifacts.write_execution(
            context.sprint_id,
            context.execution_results,
        )

        self._report("revalidating", "修复后重新验证中...")
        auto_validate(context.hypotheses, context.execution_results)
        self.write_verification(context)
        if self.latest_gap_closure_plan is not None:
            self.latest_guardrail_report = self.loop_detector.evaluate(
                context.execution_results,
                repair_attempts=self.repair_attempts,
            )
        else:
            self.latest_guardrail_report = None

    def build_workflow_plan(self, context: SprintContext) -> WorkflowPlan:
        """Build a workflow plan from sprint context."""
        requirement = context.clarified_requirement
        hypotheses = context.hypotheses or []
        tasks = []

        for index, hypothesis in enumerate(hypotheses):
            title = self._get_hypothesis_statement(hypothesis) or f"Hypothesis {index + 1}"
            tasks.append(
                WorkflowTask(
                    task_id=f"task-{index + 1}",
                    title=title[:100],
                    description=self._get_hypothesis_validation_method(hypothesis) or title,
                    hypothesis_id=self._get_hypothesis_id(hypothesis, index),
                    dependencies=self._get_hypothesis_dependencies(hypothesis),
                    verification_steps=self._get_hypothesis_success_criteria(hypothesis)
                    or list(getattr(requirement, "success_criteria", []) or []),
                    objective=title,
                    output_format="Execution result with concrete artifact or repo change summary.",
                    tools_guidance=self._get_hypothesis_tools_guidance(hypothesis)
                    or "Use the configured orchestrator or execution engine.",
                    boundaries=self._get_hypothesis_boundaries(hypothesis)
                    or "Do not change unrelated files or exceed the scoped task.",
                    effort_budget=self._get_hypothesis_effort_budget(hypothesis),
                )
            )

        return WorkflowPlan(
            summary=getattr(requirement, "summary", ""),
            goals=list(getattr(requirement, "core_features", []) or [])
            or [getattr(requirement, "summary", "")],
            tasks=tasks,
            verification_steps=list(getattr(requirement, "success_criteria", []) or []),
            out_of_scope=[],
            risks=list(getattr(requirement, "risks", []) or []),
        )

    def build_verification_report(self, context: SprintContext) -> VerificationReport:
        """Build verification report from execution and validation state."""
        truths: List[str] = []
        gaps: List[str] = []
        evidence: List[str] = []
        checks: List[VerificationCheck] = []
        verdict_by_hypothesis: Dict[str, str] = {}

        validation_results = getattr(context, "validation_results", []) or []
        for validation in validation_results:
            verdict = getattr(getattr(validation, "verdict", None), "value", None) or str(
                getattr(validation, "verdict", "unknown")
            )
            hypothesis_id = getattr(validation, "hypothesis_id", "unknown")
            reasoning = getattr(validation, "reasoning", "")
            verdict_by_hypothesis[hypothesis_id] = verdict

            checks.append(
                VerificationCheck(
                    name=f"hypothesis:{hypothesis_id}",
                    status=verdict,
                    details=reasoning,
                )
            )

            if verdict == "validated":
                truths.append(f"{hypothesis_id} validated")
            elif verdict in {"refuted", "needs_more_info", "inconclusive"}:
                gaps.append(f"{hypothesis_id} verification verdict: {verdict}")

        for result in context.execution_results or []:
            task_id = result.get("task_id", "unknown-task")
            hypothesis_id = result.get("hypothesis_id", "unknown")
            state = result.get("state", "unknown")
            success = result.get("success", False)
            evidence.append(
                f"{task_id}: hypothesis={hypothesis_id}, state={state}, success={success}"
            )
            if success:
                truths.append(f"{task_id} executed successfully")
            elif verdict_by_hypothesis.get(hypothesis_id) == "validated":
                truths.append(f"{task_id} failure was superseded by a validated repair.")
            else:
                gaps.append(f"{task_id} failed during execution")

        verdict = "pass" if not gaps else "partial"
        summary = "Verification passed with no recorded gaps." if not gaps else (
            f"Verification found {len(gaps)} gap(s) that still need attention."
        )
        return VerificationReport(
            summary=summary,
            verdict=verdict,
            truths=truths,
            gaps=gaps,
            evidence=evidence,
            checks=checks,
        )

    def build_gap_closure_plan(self, report: VerificationReport) -> GapClosurePlan:
        """Build bounded repair plan from verification gaps."""
        gap_items: List[GapItem] = []
        repair_tasks: List[WorkflowTask] = []

        for index, gap in enumerate(report.gaps, start=1):
            gap_id = f"gap-{index}"
            gap_item = GapItem(
                gap_id=gap_id,
                title=f"Resolve {gap_id}",
                description=gap,
                source="verification",
                severity="important",
                suggested_action="Investigate the failing requirement and patch only the scoped issue.",
                verification_target=gap,
            )
            gap_items.append(gap_item)
            repair_tasks.append(
                WorkflowTask(
                    task_id=f"repair-{index}",
                    title=gap_item.title,
                    description=gap_item.description,
                    verification_steps=[gap_item.verification_target],
                    objective=gap_item.suggested_action,
                    output_format="Minimal code or artifact update plus evidence of the fix.",
                    tools_guidance="Focus only on the failing path and gather concrete verification evidence.",
                    boundaries="Avoid unrelated refactors and stop after the scoped gap is addressed.",
                    effort_budget=5,
                )
            )

        return GapClosurePlan(
            summary=f"Generated {len(gap_items)} repair task(s) from verification gaps.",
            gaps=gap_items,
            repair_tasks=repair_tasks,
            stop_conditions=[
                "Stop if the same gap remains after one targeted repair attempt.",
                "Stop if fixing the gap requires broader scope than the current run allows.",
            ],
            next_verification_steps=[
                *[gap.verification_target for gap in gap_items if gap.verification_target],
                "Re-run verification after targeted repair tasks complete.",
            ],
        )

    def _report(self, stage: str, message: str) -> None:
        if self.report_progress is not None:
            self.report_progress(stage, message)

    def _get_hypothesis_id(self, hypothesis: Any, index: int) -> str:
        if hasattr(hypothesis, "id") and getattr(hypothesis, "id"):
            return getattr(hypothesis, "id")
        if hasattr(hypothesis, "hypothesis_id") and getattr(hypothesis, "hypothesis_id"):
            return getattr(hypothesis, "hypothesis_id")
        if isinstance(hypothesis, dict):
            return hypothesis.get("id") or hypothesis.get("hypothesis_id") or f"h{index}"
        return f"h{index}"

    def _get_hypothesis_statement(self, hypothesis: Any) -> str:
        if hasattr(hypothesis, "statement"):
            return getattr(hypothesis, "statement", "")
        if isinstance(hypothesis, dict):
            return hypothesis.get("statement", "")
        return ""

    def _get_hypothesis_validation_method(self, hypothesis: Any) -> str:
        if hasattr(hypothesis, "validation_method"):
            return getattr(hypothesis, "validation_method", "")
        if isinstance(hypothesis, dict):
            return hypothesis.get("validation_method", "")
        return ""

    def _get_hypothesis_dependencies(self, hypothesis: Any) -> List[str]:
        if hasattr(hypothesis, "dependencies"):
            return list(getattr(hypothesis, "dependencies", []) or [])
        if isinstance(hypothesis, dict):
            return list(hypothesis.get("dependencies", []) or [])
        return []

    def _get_hypothesis_success_criteria(self, hypothesis: Any) -> List[str]:
        if hasattr(hypothesis, "success_criteria"):
            return list(getattr(hypothesis, "success_criteria", []) or [])
        if isinstance(hypothesis, dict):
            return list(hypothesis.get("success_criteria", []) or [])
        return []

    def _get_hypothesis_tools_guidance(self, hypothesis: Any) -> str:
        if hasattr(hypothesis, "tools_guidance"):
            return getattr(hypothesis, "tools_guidance", "")
        if isinstance(hypothesis, dict):
            return hypothesis.get("tools_guidance", "")
        return ""

    def _get_hypothesis_boundaries(self, hypothesis: Any) -> str:
        if hasattr(hypothesis, "boundaries"):
            return getattr(hypothesis, "boundaries", "")
        if isinstance(hypothesis, dict):
            return hypothesis.get("boundaries", "")
        return ""

    def _get_hypothesis_effort_budget(self, hypothesis: Any) -> int:
        if hasattr(hypothesis, "effort_budget"):
            return int(getattr(hypothesis, "effort_budget", 10) or 10)
        if isinstance(hypothesis, dict):
            return int(hypothesis.get("effort_budget", 10) or 10)
        return 10
