"""Artifact persistence for workflow runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .checks import CompletionDecision, PlanCheckReport
from .types import GapClosurePlan, VerificationReport, WorkflowPlan, WorkflowRun


class WorkflowArtifactManager:
    """Persists run-scoped workflow artifacts under `.aop/runs/<run_id>/`."""

    def __init__(self, base_path: Path | str):
        base = Path(base_path)
        self.aop_dir = base if base.name == ".aop" else base / ".aop"
        self.runs_dir = self.aop_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def get_run_dir(self, run_id: str) -> Path:
        """Return the run directory and ensure it exists."""
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def initialize_run(self, run: WorkflowRun) -> Path:
        """Create the run directory and write initial metadata."""
        run_dir = self.get_run_dir(run.run_id)
        self._write_json(run_dir / "run.json", self._run_payload(run))
        self.write_run_markdown(run)
        return run_dir

    def update_run(self, run: WorkflowRun) -> None:
        """Refresh run metadata and overview markdown."""
        run.updated_at = datetime.now()
        run_dir = self.get_run_dir(run.run_id)
        self._write_json(run_dir / "run.json", self._run_payload(run))
        self.write_run_markdown(run)

    def write_run_markdown(self, run: WorkflowRun) -> Path:
        """Write the high-level run status file."""
        lines = [
            f"# Workflow Run {run.run_id}",
            "",
            f"- Status: {run.status}",
            f"- Current phase: {run.current_phase.value}",
            f"- Created at: {run.created_at.isoformat()}",
            f"- Updated at: {run.updated_at.isoformat()}",
            "",
            "## Original Input",
            "",
            run.original_input or "N/A",
            "",
            "## Clarified Summary",
            "",
            run.clarified_summary or "N/A",
            "",
            "## Success Criteria",
            "",
        ]
        lines.extend(self._format_bullets(run.success_criteria))
        lines.extend(
            [
                "",
                "## Hypotheses",
                "",
            ]
        )
        lines.extend(self._format_bullets(run.hypothesis_ids))
        return self._write_markdown(self.get_run_dir(run.run_id) / "RUN.md", lines)

    def write_plan(self, run_id: str, plan: WorkflowPlan) -> Path:
        """Persist the plan artifact."""
        run_dir = self.get_run_dir(run_id)
        self._write_json(run_dir / "plan.json", asdict(plan))

        lines = [
            "# PLAN",
            "",
            "## Summary",
            "",
            plan.summary or "N/A",
            "",
            "## Goals",
            "",
        ]
        lines.extend(self._format_bullets(plan.goals))
        lines.extend(["", "## Tasks", ""])

        if plan.tasks:
            for task in plan.tasks:
                lines.append(f"### {task.task_id}: {task.title}")
                lines.append("")
                lines.append(task.description or "N/A")
                lines.append("")
                lines.append(f"- Hypothesis: {task.hypothesis_id or 'N/A'}")
                lines.append(f"- Objective: {task.objective or 'N/A'}")
                lines.append(f"- Output format: {task.output_format or 'N/A'}")
                lines.append(f"- Tool guidance: {task.tools_guidance or 'N/A'}")
                lines.append(f"- Boundaries: {task.boundaries or 'N/A'}")
                lines.append(f"- Effort budget: {task.effort_budget}")
                lines.append(f"- Dependencies: {', '.join(task.dependencies) if task.dependencies else 'None'}")
                lines.append("- Verification steps:")
                lines.extend(self._format_bullets(task.verification_steps, indent="  "))
                lines.append("")
        else:
            lines.append("- No tasks generated")
            lines.append("")

        lines.extend(["## Verification Plan", ""])
        lines.extend(self._format_bullets(plan.verification_steps))
        lines.extend(["", "## Risks", ""])
        lines.extend(self._format_bullets(plan.risks))
        lines.extend(["", "## Out of Scope", ""])
        lines.extend(self._format_bullets(plan.out_of_scope))
        return self._write_markdown(run_dir / "PLAN.md", lines)

    def write_plan_check(self, run_id: str, report: PlanCheckReport) -> Path:
        """Persist the plan checker result."""
        run_dir = self.get_run_dir(run_id)
        self._write_json(
            run_dir / "plan_check.json",
            {
                "passed": report.passed,
                "summary": report.summary,
                "issues": [issue.__dict__ for issue in report.issues],
            },
        )

        lines = [
            "# PLAN CHECK",
            "",
            f"- Passed: {report.passed}",
            "",
            "## Summary",
            "",
            report.summary,
            "",
            "## Issues",
            "",
        ]

        if report.issues:
            for issue in report.issues:
                lines.append(f"- [{issue.severity}] {issue.message}")
        else:
            lines.append("- No issues found")

        return self._write_markdown(run_dir / "PLAN_CHECK.md", lines)

    def write_execution(self, run_id: str, execution_results: List[Dict[str, Any]]) -> Path:
        """Persist execution results as a workflow artifact."""
        run_dir = self.get_run_dir(run_id)
        self._write_json(run_dir / "execution.json", {"results": execution_results})

        lines = ["# EXECUTION", ""]
        if not execution_results:
            lines.extend(["- No execution results recorded", ""])
        else:
            for result in execution_results:
                lines.append(f"## {result.get('task_id', 'unknown-task')}")
                lines.append("")
                lines.append(f"- Hypothesis: {result.get('hypothesis_id', 'N/A')}")
                lines.append(f"- State: {result.get('state', 'unknown')}")
                lines.append(f"- Success: {result.get('success', False)}")
                errors = result.get("errors") or []
                lines.append(f"- Errors: {', '.join(errors) if errors else 'None'}")
                lines.append("")
        return self._write_markdown(run_dir / "EXECUTION.md", lines)

    def write_verification(self, run_id: str, report: VerificationReport) -> Path:
        """Persist the verification artifact."""
        run_dir = self.get_run_dir(run_id)
        self._write_json(run_dir / "verification.json", asdict(report))

        lines = [
            "# VERIFICATION",
            "",
            f"- Verdict: {report.verdict}",
            "",
            "## Summary",
            "",
            report.summary or "N/A",
            "",
            "## Truths",
            "",
        ]
        lines.extend(self._format_bullets(report.truths))
        lines.extend(["", "## Evidence", ""])
        lines.extend(self._format_bullets(report.evidence))
        lines.extend(["", "## Gaps", ""])
        lines.extend(self._format_bullets(report.gaps))
        lines.extend(["", "## Checks", ""])

        if report.checks:
            for check in report.checks:
                lines.append(f"- {check.name}: {check.status}")
                if check.details:
                    lines.append(f"  - {check.details}")
        else:
            lines.append("- No checks recorded")

        return self._write_markdown(run_dir / "VERIFICATION.md", lines)

    def write_gap_closure(self, run_id: str, plan: GapClosurePlan) -> Path:
        """Persist the gap-closure repair plan."""
        run_dir = self.get_run_dir(run_id)
        self._write_json(run_dir / "gap_closure.json", asdict(plan))

        lines = [
            "# GAPS",
            "",
            "## Summary",
            "",
            plan.summary or "N/A",
            "",
            "## Gap Items",
            "",
        ]

        if plan.gaps:
            for gap in plan.gaps:
                lines.append(f"### {gap.gap_id}: {gap.title}")
                lines.append("")
                lines.append(gap.description or "N/A")
                lines.append("")
                lines.append(f"- Source: {gap.source or 'N/A'}")
                lines.append(f"- Severity: {gap.severity}")
                lines.append(f"- Suggested action: {gap.suggested_action or 'N/A'}")
                lines.append(f"- Verification target: {gap.verification_target or 'N/A'}")
                lines.append("")
        else:
            lines.extend(["- No structured gaps recorded", ""])

        lines.extend(["## Repair Tasks", ""])
        if plan.repair_tasks:
            for task in plan.repair_tasks:
                lines.append(f"- {task.task_id}: {task.title}")
                lines.append(f"  - Objective: {task.objective or 'N/A'}")
                lines.append(f"  - Boundaries: {task.boundaries or 'N/A'}")
                lines.append(f"  - Verification: {', '.join(task.verification_steps) if task.verification_steps else 'None'}")
        else:
            lines.append("- No repair tasks generated")

        lines.extend(["", "## Stop Conditions", ""])
        lines.extend(self._format_bullets(plan.stop_conditions))
        lines.extend(["", "## Next Verification Steps", ""])
        lines.extend(self._format_bullets(plan.next_verification_steps))
        return self._write_markdown(run_dir / "GAPS.md", lines)

    def write_learnings(self, run_id: str, learnings: List[Dict[str, Any]]) -> Path:
        """Persist learnings for the run."""
        run_dir = self.get_run_dir(run_id)
        self._write_json(run_dir / "learnings.json", {"records": learnings})

        lines = ["# LEARNINGS", ""]
        if not learnings:
            lines.extend(["- No learnings recorded", ""])
        else:
            for learning in learnings:
                lines.append(f"## {learning.get('phase', 'unknown')}")
                lines.append("")
                insights = learning.get("insights", [])
                lines.extend(self._format_bullets(insights))
                lines.append("")
        return self._write_markdown(run_dir / "LEARNINGS.md", lines)

    def write_summary(self, run_id: str, summary: str) -> Path:
        """Persist a short summary for the run."""
        return self._write_markdown(
            self.get_run_dir(run_id) / "SUMMARY.md",
            ["# SUMMARY", "", summary or "N/A", ""],
        )

    def write_completion(self, run_id: str, decision: CompletionDecision) -> Path:
        """Persist the completion gate decision."""
        run_dir = self.get_run_dir(run_id)
        self._write_json(
            run_dir / "completion.json",
            {
                "passed": decision.passed,
                "status": decision.status,
                "summary": decision.summary,
                "reasons": decision.reasons,
            },
        )
        lines = [
            "# COMPLETION",
            "",
            f"- Passed: {decision.passed}",
            f"- Status: {decision.status}",
            "",
            "## Summary",
            "",
            decision.summary,
            "",
            "## Reasons",
            "",
        ]
        lines.extend(self._format_bullets(decision.reasons))
        return self._write_markdown(run_dir / "COMPLETION.md", lines)

    def _run_payload(self, run: WorkflowRun) -> Dict[str, Any]:
        return {
            "run_id": run.run_id,
            "original_input": run.original_input,
            "current_phase": run.current_phase.value,
            "status": run.status,
            "clarified_summary": run.clarified_summary,
            "success_criteria": run.success_criteria,
            "hypothesis_ids": run.hypothesis_ids,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
        }

    def _format_bullets(self, items: Iterable[str], indent: str = "") -> List[str]:
        values = [item for item in items if item]
        if not values:
            return [f"{indent}- None"]
        return [f"{indent}- {item}" for item in values]

    def _write_markdown(self, path: Path, lines: List[str]) -> Path:
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> Path:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path
