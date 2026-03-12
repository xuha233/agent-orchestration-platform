"""Tests for CLI main module."""

import pytest
from click.testing import CliRunner
from aop.cli.main import cli, EXIT_SUCCESS, EXIT_ERROR, EXIT_PROVIDER_UNAVAILABLE


class TestCLI:
    """Test CLI group."""
    
    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Agent Orchestration Platform" in result.output
    
    def test_cli_version(self):
        """Test CLI version output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == EXIT_SUCCESS
        assert "aop, version" in result.output


class TestDoctorCommand:
    """Test doctor command."""
    
    def test_doctor_help(self):
        """Test doctor help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Check provider availability" in result.output
        assert "--json" in result.output
        assert "--fix" in result.output
    
    def test_doctor_json_output(self):
        """Test doctor with JSON output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--json"])
        # Should exit with error if no providers available
        assert result.exit_code in [EXIT_SUCCESS, EXIT_ERROR, EXIT_PROVIDER_UNAVAILABLE]
        # Should have JSON output
        assert "{" in result.output or "Provider Status" in result.output


class TestReviewCommand:
    """Test review command."""
    
    def test_review_help(self):
        """Test review help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["review", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        # Phase 3: review is now a command group with subcommands
        assert "two-stage review" in result.output.lower()
        # Subcommands
        assert "mvp" in result.output
        assert "spec" in result.output
        assert "quality" in result.output
    
    def test_review_requires_subcommand(self):
        """Test review requires a subcommand."""
        runner = CliRunner()
        result = runner.invoke(cli, ["review"])
        # Should show help when no subcommand given
        assert "mvp" in result.output or "Commands" in result.output
    
    def test_review_mvp_help(self):
        """Test review mvp help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["review", "mvp", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "MVP" in result.output
    
    def test_review_spec_help(self):
        """Test review spec help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["review", "spec", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "spec" in result.output.lower()



class TestRunCommand:
    """Test run command."""
    
    def test_run_help(self):
        """Test run help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "task" in result.output.lower()
        # Basic options
        assert "--prompt" in result.output
        assert "--providers" in result.output
        assert "--repo" in result.output
        # New CLI parameters
        assert "--result-mode" in result.output
        assert "--stall-timeout" in result.output
        assert "--synthesize" in result.output
        assert "--target-paths" in result.output
        assert "--save-artifacts" in result.output
    
    def test_run_requires_prompt(self):
        """Test run requires prompt option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run"])
        assert result.exit_code != EXIT_SUCCESS
        assert "Missing option" in result.output or "required" in result.output.lower()


class TestInitCommand:
    """Test init command."""
    
    def test_init_help(self):
        """Test init help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "init" in result.output.lower()
        assert "--name" in result.output
        assert "--providers" in result.output
        assert "--project-type" in result.output
        assert "--force" in result.output
    
    def test_init_creates_files(self):
        """Test init creates configuration files."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "-n", "test-project", "-P", "claude,codex"])
            assert result.exit_code == EXIT_SUCCESS
            assert "Created .aop.yaml" in result.output
            assert "Created runs/" in result.output
            assert "Created hypotheses.md" in result.output
    
    def test_init_fails_on_existing_config(self):
        """Test init fails when config already exists."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # First init
            runner.invoke(cli, ["init", "-n", "test-project", "-P", "claude,codex"])
            # Second init without force
            result = runner.invoke(cli, ["init", "-n", "test-project", "-P", "claude,codex"])
            assert result.exit_code == EXIT_ERROR
            assert "already exists" in result.output
    
    def test_init_force_overwrites(self):
        """Test init with --force overwrites existing files."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # First init
            runner.invoke(cli, ["init", "-n", "test-project", "-P", "claude,codex"])
            # Second init with force
            result = runner.invoke(cli, ["init", "-n", "new-project", "-P", "claude,codex", "--force"])
            assert result.exit_code == EXIT_SUCCESS
            assert "Created .aop.yaml" in result.output


class TestHypothesisCommand:
    """Test hypothesis command group."""
    
    def test_hypothesis_help(self):
        """Test hypothesis help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["hypothesis", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Manage hypotheses" in result.output
    
    def test_hypothesis_create_help(self):
        """Test hypothesis create help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["hypothesis", "create", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Create a hypothesis" in result.output
        assert "--priority" in result.output


class TestProjectCommand:
    """Test project command group."""
    
    def test_project_help(self):
        """Test project help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["project", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Project management" in result.output
    
    def test_project_assess_help(self):
        """Test project assess help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["project", "assess", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Assess project complexity" in result.output
        assert "--problem-clarity" in result.output
        assert "--data-availability" in result.output
        assert "--tech-novelty" in result.output
        assert "--business-risk" in result.output


class TestLearningCommand:
    """Test learning command group."""
    
    def test_learning_help(self):
        """Test learning help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["learning", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Capture and manage learnings" in result.output
    
    def test_learning_capture_help(self):
        """Test learning capture help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["learning", "capture", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Capture learning from a phase" in result.output
        assert "--phase" in result.output
        assert "--worked" in result.output
        assert "--failed" in result.output
        assert "--insight" in result.output


class TestNewCLIParameters:
    """Test new CLI parameters aligned with MCO."""
    
    def test_stall_timeout_option(self):
        """Test --stall-timeout option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--stall-timeout" in result.output
        assert "idle" in result.output.lower()
    
    def test_review_hard_timeout_option(self):
        """Test --review-hard-timeout option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--review-hard-timeout" in result.output
        assert "hard" in result.output.lower() or "deadline" in result.output.lower()
    
    def test_include_token_usage_option(self):
        """Test --include-token-usage option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--include-token-usage" in result.output
    
    def test_synthesize_option(self):
        """Test --synthesize option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--synthesize" in result.output
        assert "synthesis" in result.output.lower()
    
    def test_synth_provider_option(self):
        """Test --synth-provider option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--synth-provider" in result.output
    
    def test_provider_timeouts_option(self):
        """Test --provider-timeouts option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--provider-timeouts" in result.output
    
    def test_target_paths_option(self):
        """Test --target-paths option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--target-paths" in result.output
    
    def test_allow_paths_option(self):
        """Test --allow-paths option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--allow-paths" in result.output
    
    def test_strict_contract_option(self):
        """Test --strict-contract option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--strict-contract" in result.output
    
    def test_save_artifacts_option(self):
        """Test --save-artifacts option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--save-artifacts" in result.output
    
    def test_task_id_option(self):
        """Test --task-id option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--task-id" in result.output
    
    def test_artifact_base_option(self):
        """Test --artifact-base option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--artifact-base" in result.output
    
    def test_enforcement_mode_option(self):
        """Test --enforcement-mode option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])
        assert "--enforcement-mode" in result.output
