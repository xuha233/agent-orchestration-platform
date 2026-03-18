"""Workflow quality gates for plan, completion, and repair guardrails."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .types import VerificationReport, WorkflowPlan


@dataclass
class PlanCheckIssue:
    """A single plan quality issue."""

    severity: str
    message: str


@dataclass
class PlanCheckReport:
    """Result of validating a workflow plan."""

    passed: bool
    summary: str
    issues: List[PlanCheckIssue] = field(default_factory=list)


@dataclass
class CompletionDecision:
    """Decision emitted by the completion gate."""

    passed: bool
    status: str
    summary: str
    reasons: List[str] = field(default_factory=list)


@dataclass
class GuardrailReport:
    """Guardrail decision for bounded repair execution."""

    should_stop: bool
    summary: str
    reasons: List[str] = field(default_factory=list)


class WorkflowPlanChecker:
    """Lightweight validation for plan quality before execution."""

    def check(self, plan: WorkflowPlan) -> PlanCheckReport:
        issues: List[PlanCheckIssue] = []

        if not plan.summary.strip():
            issues.append(PlanCheckIssue("critical", "Plan summary is missing."))

        if not plan.tasks:
            issues.append(PlanCheckIssue("critical", "Plan has no tasks."))

        if not plan.verification_steps:
            issues.append(
                PlanCheckIssue("critical", "Plan has no top-level verification steps.")
            )

        for task in plan.tasks:
            if not task.title.strip():
                issues.append(
                    PlanCheckIssue("important", f"{task.task_id} is missing a title.")
                )
            if not task.verification_steps:
                issues.append(
                    PlanCheckIssue(
                        "critical",
                        f"{task.task_id} is missing task-level verification steps.",
                    )
                )
            if not task.objective.strip():
                issues.append(
                    PlanCheckIssue(
                        "important",
                        f"{task.task_id} is missing a clear objective.",
                    )
                )
            if not task.output_format.strip():
                issues.append(
                    PlanCheckIssue(
                        "important",
                        f"{task.task_id} is missing an output format contract.",
                    )
                )
            if not task.boundaries.strip():
                issues.append(
                    PlanCheckIssue(
                        "minor",
                        f"{task.task_id} is missing task boundaries.",
                    )
                )
            if task.effort_budget <= 0:
                issues.append(
                    PlanCheckIssue(
                        "important",
                        f"{task.task_id} has an invalid effort budget.",
                    )
                )

        critical_count = sum(1 for issue in issues if issue.severity == "critical")
        passed = critical_count == 0
        summary = (
            "Plan passed validation."
            if passed
            else f"Plan failed validation with {critical_count} critical issue(s)."
        )
        return PlanCheckReport(passed=passed, summary=summary, issues=issues)


class CompletionGate:
    """Decide whether a workflow run can be considered complete."""

    def evaluate(
        self,
        verification_report: VerificationReport | None,
        execution_results: List[dict] | None,
        learnings: List[dict] | None,
    ) -> CompletionDecision:
        reasons: List[str] = []

        if verification_report is None:
            reasons.append("Missing verification report.")
        elif verification_report.verdict != "pass":
            reasons.append(
                f"Verification verdict is {verification_report.verdict}, not pass."
            )

        if not execution_results:
            reasons.append("No execution results were recorded.")

        if learnings is None:
            reasons.append("Learning stage did not produce an artifact.")

        if reasons:
            return CompletionDecision(
                passed=False,
                status="needs_follow_up",
                summary="Completion gate did not pass.",
                reasons=reasons,
            )

        return CompletionDecision(
            passed=True,
            status="completed",
            summary="Completion gate passed.",
            reasons=[],
        )


class WorkflowLoopDetector:
    """Detect repeated failure patterns and repair-budget exhaustion."""

    def evaluate(
        self,
        execution_results: List[dict] | None,
        repair_attempts: int,
        max_repair_attempts: int = 1,
        repeated_failure_threshold: int = 2,
    ) -> GuardrailReport:
        reasons: List[str] = []
        failure_counts: dict[str, int] = {}

        for result in execution_results or []:
            if result.get("success", False):
                continue
            key = result.get("hypothesis_id") or result.get("task_id") or "unknown"
            failure_counts[key] = failure_counts.get(key, 0) + 1

        for key, count in failure_counts.items():
            if count >= repeated_failure_threshold:
                reasons.append(
                    f"Repeated failure threshold reached for {key}: {count} failures."
                )

        if repair_attempts >= max_repair_attempts:
            reasons.append(
                f"Repair budget exhausted at {repair_attempts} attempt(s)."
            )

        if reasons:
            return GuardrailReport(
                should_stop=True,
                summary="Repair guardrails require the workflow to stop and re-plan.",
                reasons=reasons,
            )

        return GuardrailReport(
            should_stop=False,
            summary="Repair guardrails allow another bounded step.",
            reasons=[],
        )
