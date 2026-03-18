"""Tests for AgentDriver workflow artifact generation."""

from aop.agent.driver import AgentDriver
from aop.agent.types import (
    AgentDriverConfig,
    ClarifiedRequirement,
    ExtractedLearning,
    ValidationResult,
    ValidationVerdict,
)


def test_agent_driver_writes_workflow_artifacts(tmp_path):
    config = AgentDriverConfig(
        storage_path=tmp_path,
        auto_execute=True,
        auto_validate=True,
        auto_learn=True,
    )
    driver = AgentDriver(config=config)

    driver._clarify_requirement = lambda vague_input, callback: ClarifiedRequirement(
        summary="Build a login MVP",
        core_features=["Login form", "Credential validation"],
        success_criteria=["Users can log in successfully"],
        risks=["No signup flow yet"],
    )
    driver._generate_hypotheses = lambda requirement: [
        {
            "hypothesis_id": "H-001",
            "statement": "A simple login flow solves the immediate user need",
            "validation_method": "Run login smoke test",
            "success_criteria": ["Smoke test passes"],
        }
    ]
    driver._execute_tasks = lambda: [
        {
            "task_id": "task-1",
            "hypothesis_id": "H-001",
            "success": True,
            "state": "completed",
            "errors": [],
        }
    ]

    def fake_auto_validate(hypotheses, results):
        driver.context.validation_results = [
            ValidationResult(
                hypothesis_id="H-001",
                state="completed",
                verdict=ValidationVerdict.VALIDATED,
                reasoning="Smoke test passed.",
            )
        ]

    driver._auto_validate = fake_auto_validate
    driver._extract_learnings = lambda results: [
        ExtractedLearning(
            phase="execute",
            insights=["Persisting plan artifacts helps with handoff."],
        )
    ]

    result = driver.run_from_vague_description("Build a login MVP")

    run_dir = tmp_path / ".aop" / "runs" / result.sprint_id
    assert result.success is True
    assert (run_dir / "RUN.md").exists()
    assert (run_dir / "PLAN.md").exists()
    assert (run_dir / "PLAN_CHECK.md").exists()
    assert (run_dir / "EXECUTION.md").exists()
    assert (run_dir / "VERIFICATION.md").exists()
    assert (run_dir / "LEARNINGS.md").exists()
    assert (run_dir / "COMPLETION.md").exists()
    assert (run_dir / "SUMMARY.md").exists()

    summary_content = (run_dir / "SUMMARY.md").read_text(encoding="utf-8")
    verification_content = (run_dir / "VERIFICATION.md").read_text(encoding="utf-8")
    completion_content = (run_dir / "COMPLETION.md").read_text(encoding="utf-8")

    assert "冲刺" in summary_content
    assert "H-001 validated" in verification_content
    assert "Status: completed" in completion_content


def test_agent_driver_accepts_string_storage_path(tmp_path):
    driver = AgentDriver(
        config=AgentDriverConfig(
            storage_path=str(tmp_path),
            auto_execute=False,
            auto_validate=False,
            auto_learn=False,
        )
    )

    assert str(driver.storage_path) == str(tmp_path)


def test_agent_driver_writes_gap_closure_when_verification_has_gaps(tmp_path):
    config = AgentDriverConfig(
        storage_path=tmp_path,
        auto_execute=True,
        auto_validate=True,
        auto_learn=True,
    )
    driver = AgentDriver(config=config)

    driver._clarify_requirement = lambda vague_input, callback: ClarifiedRequirement(
        summary="Build a login MVP",
        core_features=["Login form"],
        success_criteria=["Users can log in successfully"],
    )
    driver._generate_hypotheses = lambda requirement: [
        {
            "hypothesis_id": "H-001",
            "statement": "Login flow works",
            "validation_method": "Run smoke test",
            "success_criteria": ["Smoke test passes"],
        }
    ]
    driver._execute_tasks = lambda: [
        {
            "task_id": "task-1",
            "hypothesis_id": "H-001",
            "success": False,
            "state": "failed",
            "errors": ["Smoke test failed"],
        }
    ]

    def fake_auto_validate(hypotheses, results):
        driver.context.validation_results = [
            ValidationResult(
                hypothesis_id="H-001",
                state="failed",
                verdict=ValidationVerdict.REFUTED,
                reasoning="Smoke test failed.",
            )
        ]

    driver._auto_validate = fake_auto_validate
    driver._extract_learnings = lambda results: [
        ExtractedLearning(
            phase="verify",
            insights=["Need targeted repair plan."],
        )
    ]

    result = driver.run_from_vague_description("Build a login MVP")

    run_dir = tmp_path / ".aop" / "runs" / result.sprint_id
    assert result.success is False
    assert (run_dir / "GAPS.md").exists()

    gaps_content = (run_dir / "GAPS.md").read_text(encoding="utf-8")
    completion_content = (run_dir / "COMPLETION.md").read_text(encoding="utf-8")

    assert "repair-1" in gaps_content
    assert "needs_follow_up" in completion_content


def test_agent_driver_runs_single_repair_wave_and_clears_gaps_on_success(tmp_path):
    config = AgentDriverConfig(
        storage_path=tmp_path,
        auto_execute=True,
        auto_validate=True,
        auto_learn=True,
    )
    driver = AgentDriver(config=config)

    driver._clarify_requirement = lambda vague_input, callback: ClarifiedRequirement(
        summary="Build a login MVP",
        core_features=["Login form"],
        success_criteria=["Users can log in successfully"],
    )
    driver._generate_hypotheses = lambda requirement: [
        {
            "hypothesis_id": "H-001",
            "statement": "Login flow works",
            "validation_method": "Run smoke test",
            "success_criteria": ["Smoke test passes"],
        }
    ]
    driver._execute_tasks = lambda: [
        {
            "task_id": "task-1",
            "hypothesis_id": "H-001",
            "success": False,
            "state": "failed",
            "errors": ["Smoke test failed"],
        }
    ]
    driver._execute_workflow_tasks = lambda tasks: [
        {
            "task_id": tasks[0].task_id,
            "hypothesis_id": "H-001",
            "success": True,
            "state": "completed",
            "errors": [],
            "repair_wave": True,
        }
    ]

    validation_calls = {"count": 0}

    def fake_auto_validate(hypotheses, results):
        validation_calls["count"] += 1
        if validation_calls["count"] == 1:
            driver.context.validation_results = [
                ValidationResult(
                    hypothesis_id="H-001",
                    state="failed",
                    verdict=ValidationVerdict.REFUTED,
                    reasoning="Smoke test failed.",
                )
            ]
        else:
            driver.context.validation_results = [
                ValidationResult(
                    hypothesis_id="H-001",
                    state="completed",
                    verdict=ValidationVerdict.VALIDATED,
                    reasoning="Repair wave fixed the failing path.",
                )
            ]

    driver._auto_validate = fake_auto_validate
    driver._extract_learnings = lambda results: [
        ExtractedLearning(
            phase="gap_close",
            insights=["One repair wave resolved the issue."],
        )
    ]

    result = driver.run_from_vague_description("Build a login MVP")

    run_dir = tmp_path / ".aop" / "runs" / result.sprint_id
    completion_content = (run_dir / "COMPLETION.md").read_text(encoding="utf-8")
    verification_content = (run_dir / "VERIFICATION.md").read_text(encoding="utf-8")

    assert result.success is True
    assert validation_calls["count"] == 2
    assert not (run_dir / "GAPS.md").exists()
    assert "Status: completed" in completion_content
    assert "Verdict: pass" in verification_content


def test_agent_driver_writes_guardrail_report_when_repair_still_fails(tmp_path):
    config = AgentDriverConfig(
        storage_path=tmp_path,
        auto_execute=True,
        auto_validate=True,
        auto_learn=True,
    )
    driver = AgentDriver(config=config)

    driver._clarify_requirement = lambda vague_input, callback: ClarifiedRequirement(
        summary="Build a login MVP",
        core_features=["Login form"],
        success_criteria=["Users can log in successfully"],
    )
    driver._generate_hypotheses = lambda requirement: [
        {
            "hypothesis_id": "H-001",
            "statement": "Login flow works",
            "validation_method": "Run smoke test",
            "success_criteria": ["Smoke test passes"],
        }
    ]
    driver._execute_tasks = lambda: [
        {
            "task_id": "task-1",
            "hypothesis_id": "H-001",
            "success": False,
            "state": "failed",
            "errors": ["Smoke test failed"],
        }
    ]
    driver._execute_workflow_tasks = lambda tasks: [
        {
            "task_id": tasks[0].task_id,
            "hypothesis_id": "H-001",
            "success": False,
            "state": "failed",
            "errors": ["Repair wave failed"],
            "repair_wave": True,
        }
    ]

    driver._auto_validate = lambda hypotheses, results: setattr(
        driver.context,
        "validation_results",
        [
            ValidationResult(
                hypothesis_id="H-001",
                state="failed",
                verdict=ValidationVerdict.REFUTED,
                reasoning="The failing path remains unresolved.",
            )
        ],
    )
    driver._extract_learnings = lambda results: [
        ExtractedLearning(
            phase="gap_close",
            insights=["Repair wave did not resolve the issue."],
        )
    ]

    result = driver.run_from_vague_description("Build a login MVP")

    run_dir = tmp_path / ".aop" / "runs" / result.sprint_id
    completion_content = (run_dir / "COMPLETION.md").read_text(encoding="utf-8")
    guardrail_content = (run_dir / "GUARDRAILS.md").read_text(encoding="utf-8")

    assert result.success is False
    assert "needs_follow_up" in completion_content
    assert "Repair budget exhausted" in guardrail_content
