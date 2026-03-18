"""Workflow phase coordination for AOP."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List

from .types import WorkflowPhase

if TYPE_CHECKING:
    from ..agent.types import ClarifiedRequirement, SprintContext, SprintResult


class WorkflowCoordinator:
    """Coordinates phase progression while the driver remains a facade."""

    def __init__(
        self,
        sprint_state_enum: Any,
        report_progress: Callable[[str, str], None],
        initialize_tracking: Callable[[], None],
        save_context: Callable[[], None],
        build_result: Callable[[], SprintResult],
        finalize_workflow_run: Callable[[str], None],
        sync_workflow_run_metadata: Callable[[], None],
        update_workflow_phase: Callable[[WorkflowPhase, str], None],
        write_plan_artifact: Callable[[], None],
        write_execution_artifact: Callable[[str, List[Dict[str, Any]]], None],
        write_verification_artifact: Callable[[], None],
        write_learnings_artifact: Callable[[], None],
        run_gap_closure_cycle: Callable[[], None],
        clarify_requirement: Callable[[str, Callable[[str], str] | None], ClarifiedRequirement],
        generate_hypotheses: Callable[[ClarifiedRequirement], List[Any]],
        execute_tasks: Callable[[], List[Dict[str, Any]]],
        auto_validate: Callable[[List[Any], List[Dict[str, Any]]], None],
        extract_learnings: Callable[[List[Dict[str, Any]]], List[Any]],
    ):
        self.sprint_state = sprint_state_enum
        self.report_progress = report_progress
        self.initialize_tracking = initialize_tracking
        self.save_context = save_context
        self.build_result = build_result
        self.finalize_workflow_run = finalize_workflow_run
        self.sync_workflow_run_metadata = sync_workflow_run_metadata
        self.update_workflow_phase = update_workflow_phase
        self.write_plan_artifact = write_plan_artifact
        self.write_execution_artifact = write_execution_artifact
        self.write_verification_artifact = write_verification_artifact
        self.write_learnings_artifact = write_learnings_artifact
        self.run_gap_closure_cycle = run_gap_closure_cycle
        self.clarify_requirement = clarify_requirement
        self.generate_hypotheses = generate_hypotheses
        self.execute_tasks = execute_tasks
        self.auto_validate = auto_validate
        self.extract_learnings = extract_learnings

    def run_new(
        self,
        context: SprintContext,
        vague_input: str,
        clarifications_callback: Callable[[str], str] | None,
        auto_execute: bool,
        auto_validate: bool,
        auto_learn: bool,
    ) -> SprintResult:
        """Run a new sprint from vague user input."""
        self.initialize_tracking()
        self.save_context()

        try:
            self.report_progress("clarifying", "澄清需求中...")
            self.update_workflow_phase(WorkflowPhase.CLARIFY, "running")
            clarified = self.clarify_requirement(vague_input, clarifications_callback)
            context.clarified_requirement = clarified
            context.state = self.sprint_state.CLARIFIED
            self.sync_workflow_run_metadata()
            self.save_context()

            self.report_progress("generating_hypotheses", "生成假设中...")
            hypotheses = self.generate_hypotheses(clarified)
            context.hypotheses = hypotheses
            context.state = self.sprint_state.HYPOTHESES_GENERATED
            self.sync_workflow_run_metadata()
            self.save_context()
            self.write_plan_artifact()

            self.report_progress("decomposing_tasks", "分解任务中...")
            context.state = self.sprint_state.TASKS_DECOMPOSED
            self.save_context()

            if auto_execute:
                self._continue_from_execution(
                    context=context,
                    auto_validate_enabled=auto_validate,
                    auto_learn_enabled=auto_learn,
                )

            self.finalize_workflow_run("completed")
            return self.build_result()
        except Exception:
            context.state = self.sprint_state.FAILED
            self.save_context()
            self.finalize_workflow_run("failed")
            raise

    def run_from_clarified(
        self,
        context: SprintContext,
        auto_execute: bool,
        auto_validate: bool,
        auto_learn: bool,
    ) -> SprintResult:
        """Run from a pre-clarified requirement."""
        if context.clarified_requirement is None:
            raise ValueError("clarified requirement is required")

        self.initialize_tracking()
        self.save_context()

        hypotheses = self.generate_hypotheses(context.clarified_requirement)
        context.hypotheses = hypotheses
        self.save_context()

        if auto_execute:
            self._continue_from_execution(
                context=context,
                auto_validate_enabled=auto_validate,
                auto_learn_enabled=auto_learn,
            )

        return self.build_result()

    def resume(
        self,
        context: SprintContext,
        auto_execute: bool,
        auto_validate: bool,
        auto_learn: bool,
    ) -> SprintResult:
        """Resume a persisted sprint context."""
        self.report_progress("resuming", f"恢复冲刺 {context.sprint_id}，当前状态: {context.state.value}")

        if context.state == self.sprint_state.INITIALIZED:
            return self.run_new(
                context=context,
                vague_input=context.original_input,
                clarifications_callback=None,
                auto_execute=auto_execute,
                auto_validate=auto_validate,
                auto_learn=auto_learn,
            )

        if context.state == self.sprint_state.CLARIFIED:
            if context.clarified_requirement is None:
                raise ValueError("clarified requirement is required to resume")
            self.report_progress("generating_hypotheses", "生成假设中...")
            hypotheses = self.generate_hypotheses(context.clarified_requirement)
            context.hypotheses = hypotheses
            context.state = self.sprint_state.HYPOTHESES_GENERATED
            self.save_context()
            return self._continue_from_hypotheses(
                context=context,
                auto_execute=auto_execute,
                auto_validate=auto_validate,
                auto_learn=auto_learn,
            )

        if context.state == self.sprint_state.HYPOTHESES_GENERATED:
            return self._continue_from_hypotheses(
                context=context,
                auto_execute=auto_execute,
                auto_validate=auto_validate,
                auto_learn=auto_learn,
            )

        if context.state == self.sprint_state.TASKS_DECOMPOSED:
            return self._continue_from_execution(
                context=context,
                auto_validate_enabled=auto_validate,
                auto_learn_enabled=auto_learn,
            )

        if context.state == self.sprint_state.EXECUTED:
            return self._continue_from_validation(context, auto_learn)

        if context.state == self.sprint_state.VALIDATED:
            return self._continue_from_learning(context)

        if context.state == self.sprint_state.COMPLETED:
            self.report_progress("completed", "冲刺已完成")
            return self.build_result()

        if context.state == self.sprint_state.FAILED:
            self.report_progress("failed", "冲刺之前失败，请检查错误日志")
            return self.build_result()

        return self.build_result()

    def _continue_from_hypotheses(
        self,
        context: SprintContext,
        auto_execute: bool,
        auto_validate: bool,
        auto_learn: bool,
    ) -> SprintResult:
        self.report_progress("decomposing_tasks", "分解任务中...")
        context.state = self.sprint_state.TASKS_DECOMPOSED
        self.save_context()
        self.write_plan_artifact()

        if auto_execute:
            return self._continue_from_execution(
                context=context,
                auto_validate_enabled=auto_validate,
                auto_learn_enabled=auto_learn,
            )
        return self.build_result()

    def _continue_from_execution(
        self,
        context: SprintContext,
        auto_validate_enabled: bool,
        auto_learn_enabled: bool,
    ) -> SprintResult:
        self.report_progress("executing", "并行执行中...")
        self.update_workflow_phase(WorkflowPhase.EXECUTE, "running")
        results = self.execute_tasks()
        context.execution_results = results
        context.state = self.sprint_state.EXECUTED
        self.save_context()
        self.write_execution_artifact(context.sprint_id, results)

        if auto_validate_enabled:
            return self._continue_from_validation(context, auto_learn_enabled)
        return self.build_result()

    def _continue_from_validation(
        self,
        context: SprintContext,
        auto_learn_enabled: bool,
    ) -> SprintResult:
        self.report_progress("validating", "验证结果中...")
        self.update_workflow_phase(WorkflowPhase.VERIFY, "running")
        self.auto_validate(context.hypotheses, context.execution_results)
        context.state = self.sprint_state.VALIDATED
        self.save_context()
        self.write_verification_artifact()
        self.run_gap_closure_cycle()

        if auto_learn_enabled:
            return self._continue_from_learning(context)
        return self.build_result()

    def _continue_from_learning(self, context: SprintContext) -> SprintResult:
        self.report_progress("learning", "提取学习中...")
        self.update_workflow_phase(WorkflowPhase.LEARN, "running")
        learnings = self.extract_learnings(context.execution_results)
        context.learnings = learnings
        context.state = self.sprint_state.COMPLETED
        self.save_context()
        self.write_learnings_artifact()
        self.finalize_workflow_run("completed")
        return self.build_result()
