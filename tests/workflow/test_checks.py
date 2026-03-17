"""Tests for workflow quality gates."""

from aop.workflow import (
    CompletionGate,
    VerificationReport,
    WorkflowPlan,
    WorkflowPlanChecker,
    WorkflowTask,
)


def test_plan_checker_rejects_missing_verification_steps():
    checker = WorkflowPlanChecker()
    plan = WorkflowPlan(
        summary="Build login MVP",
        tasks=[
            WorkflowTask(
                task_id="task-1",
                title="Implement login",
                objective="Implement login",
                output_format="Code changes",
                boundaries="Keep scope limited",
                effort_budget=5,
            )
        ],
    )

    report = checker.check(plan)

    assert report.passed is False
    assert any("verification" in issue.message.lower() for issue in report.issues)


def test_completion_gate_requires_passing_verification():
    gate = CompletionGate()

    decision = gate.evaluate(
        verification_report=VerificationReport(
            summary="Still has gaps.",
            verdict="partial",
        ),
        execution_results=[{"task_id": "task-1", "success": True}],
        learnings=[{"phase": "execute", "insights": ["Something worked"]}],
    )

    assert decision.passed is False
    assert decision.status == "needs_follow_up"
    assert any("partial" in reason for reason in decision.reasons)
