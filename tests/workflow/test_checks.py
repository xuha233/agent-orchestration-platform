"""Tests for workflow quality gates."""

from aop.workflow import (
    CompletionGate,
    WorkflowLoopDetector,
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


def test_loop_detector_stops_after_repeated_failures():
    detector = WorkflowLoopDetector()

    report = detector.evaluate(
        execution_results=[
            {"task_id": "task-1", "hypothesis_id": "H-001", "success": False},
            {"task_id": "repair-1", "hypothesis_id": "H-001", "success": False},
        ],
        repair_attempts=1,
    )

    assert report.should_stop is True
    assert "repeated_failures" in report.categories
    assert any("H-001" in reason for reason in report.reasons)


def test_plan_checker_flags_budget_pressure():
    checker = WorkflowPlanChecker()
    plan = WorkflowPlan(
        summary="Ship broad platform upgrade",
        verification_steps=["Run validation"],
        tasks=[
            WorkflowTask(
                task_id="task-1",
                title="Large migration",
                objective="Migrate several systems",
                output_format="Code changes",
                boundaries="Keep scope documented",
                verification_steps=["Run smoke tests"],
                effort_budget=30,
            ),
            WorkflowTask(
                task_id="task-2",
                title="Large verification pass",
                objective="Validate multiple flows",
                output_format="Test results",
                boundaries="Only verify planned scope",
                verification_steps=["Collect results"],
                effort_budget=80,
            ),
        ],
    )

    report = checker.check(plan)

    assert any("per-task effort budget" in issue.message for issue in report.issues)
    assert any("total effort budget" in issue.message for issue in report.issues)


def test_loop_detector_stops_when_failure_pressure_is_high():
    detector = WorkflowLoopDetector()

    report = detector.evaluate(
        execution_results=[
            {"task_id": f"task-{index}", "hypothesis_id": f"H-{index}", "success": index < 3}
            for index in range(8)
        ],
        repair_attempts=0,
    )

    assert report.should_stop is True
    assert "failure_pressure" in report.categories
    assert any("context pressure" in reason.lower() for reason in report.reasons)
