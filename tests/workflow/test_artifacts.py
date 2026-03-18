"""Tests for workflow artifact persistence."""

from aop.workflow import (
    CompletionDecision,
    GapClosurePlan,
    GapItem,
    PlanCheckReport,
    VerificationCheck,
    VerificationReport,
    WorkflowArtifactManager,
    WorkflowPhase,
    WorkflowPlan,
    WorkflowRun,
    WorkflowTask,
)


def test_workflow_artifact_manager_writes_run_plan_and_verification(tmp_path):
    manager = WorkflowArtifactManager(tmp_path)
    run = WorkflowRun(
        run_id="run-001",
        original_input="Build a login MVP",
        current_phase=WorkflowPhase.PLAN,
        clarified_summary="Create a simple login flow",
        success_criteria=["Users can log in"],
        hypothesis_ids=["H-001"],
    )

    manager.initialize_run(run)
    manager.write_plan(
        run.run_id,
        WorkflowPlan(
            summary="Create a login MVP",
            goals=["Implement login form"],
            tasks=[
                WorkflowTask(
                    task_id="task-1",
                    title="Implement login form",
                    description="Build UI and auth wiring",
                    hypothesis_id="H-001",
                    verification_steps=["Manual login smoke test"],
                )
            ],
            verification_steps=["Run smoke test"],
            risks=["Auth edge cases are not covered"],
        ),
    )
    manager.write_execution(
        run.run_id,
        [
            {
                "task_id": "task-1",
                "hypothesis_id": "H-001",
                "success": True,
                "state": "completed",
                "errors": [],
            }
        ],
    )
    manager.write_verification(
        run.run_id,
        VerificationReport(
            summary="Verification passed.",
            verdict="pass",
            truths=["Login flow works"],
            evidence=["task-1 completed"],
            checks=[VerificationCheck(name="smoke-test", status="passed")],
        ),
    )
    manager.write_plan_check(
        run.run_id,
        PlanCheckReport(
            passed=True,
            summary="Plan passed validation.",
        ),
    )
    manager.write_summary(run.run_id, "Run completed successfully.")
    manager.write_completion(
        run.run_id,
        CompletionDecision(
            passed=True,
            status="completed",
            summary="Completion gate passed.",
        ),
    )
    manager.write_gap_closure(
        run.run_id,
        GapClosurePlan(
            summary="One follow-up gap remains.",
            gaps=[
                GapItem(
                    gap_id="gap-1",
                    title="Fix login failure",
                    description="Login smoke test failed.",
                    verification_target="Smoke test passes",
                )
            ],
        ),
    )

    run_dir = tmp_path / ".aop" / "runs" / "run-001"
    assert (run_dir / "RUN.md").exists()
    assert (run_dir / "PLAN.md").exists()
    assert (run_dir / "PLAN_CHECK.md").exists()
    assert (run_dir / "EXECUTION.md").exists()
    assert (run_dir / "VERIFICATION.md").exists()
    assert (run_dir / "GAPS.md").exists()
    assert (run_dir / "COMPLETION.md").exists()
    assert (run_dir / "SUMMARY.md").exists()

    plan_content = (run_dir / "PLAN.md").read_text(encoding="utf-8")
    verification_content = (run_dir / "VERIFICATION.md").read_text(encoding="utf-8")

    assert "Implement login form" in plan_content
    assert "Verdict: pass" in verification_content
