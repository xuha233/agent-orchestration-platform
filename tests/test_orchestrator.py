"""Tests for AgentOrchestrator with multi-executor support"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from aop.agent.orchestrator import (
    AgentOrchestrator,
    OrchestrationConfig,
    orchestrate,
)
from aop.agent.executor import (
    ExecutorType,
    ExecutorInfo,
    check_executor,
    discover_all,
    get_available_executors,
    get_best_executor,
)
from aop.agent.types import SprintState, SprintContext, ClarifiedRequirement, SprintResult


class TestExecutorType:
    """Tests for ExecutorType enum"""

    def test_executor_types_exist(self):
        """Test all expected executor types exist"""
        assert ExecutorType.CLAUDE_CODE.value == "claude-code"
        assert ExecutorType.OPENCODE.value == "opencode"
        assert ExecutorType.CODEX.value == "codex"

    def test_executor_type_count(self):
        """Test we have exactly 3 executor types"""
        assert len(list(ExecutorType)) == 3


class TestExecutorInfo:
    """Tests for ExecutorInfo dataclass"""

    def test_executor_info_creation(self):
        """Test creating ExecutorInfo"""
        info = ExecutorInfo(
            executor_type=ExecutorType.CLAUDE_CODE,
            available=True,
            binary_name="claude",
            binary_path="/usr/bin/claude",
            version="1.0.0",
        )
        assert info.executor_type == ExecutorType.CLAUDE_CODE
        assert info.available is True
        assert info.version == "1.0.0"
        assert info.binary_path == "/usr/bin/claude"
        assert info.error is None

    def test_executor_info_with_error(self):
        """Test ExecutorInfo with error"""
        info = ExecutorInfo(
            executor_type=ExecutorType.OPENCODE,
            available=False,
            error="Command not found",
        )
        assert info.available is False
        assert info.error == "Command not found"


class TestExecutorDiscovery:
    """Tests for executor discovery functions"""

    @patch('shutil.which')
    def test_check_executor_available(self, mock_which):
        """Test checking an available executor"""
        mock_which.return_value = "/usr/bin/claude"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="claude version 1.0.0\n"
            )

            info = check_executor(ExecutorType.CLAUDE_CODE)

            assert info.available is True
            assert info.binary_path == "/usr/bin/claude"
            assert "1.0.0" in info.version

    @patch('shutil.which')
    def test_check_executor_not_available(self, mock_which):
        """Test checking an unavailable executor"""
        mock_which.return_value = None

        info = check_executor(ExecutorType.OPENCODE)

        assert info.available is False
        assert "not found" in info.error

    @patch('shutil.which')
    def test_discover_all(self, mock_which):
        """Test discovering all executors"""
        mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}" if cmd == "claude" else None

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="1.0.0")

            results = discover_all()

            assert len(results) == 3
            assert ExecutorType.CLAUDE_CODE in results
            assert ExecutorType.OPENCODE in results
            assert ExecutorType.CODEX in results

    @patch('aop.agent.executor.check_executor')
    def test_get_available_executors(self, mock_check):
        """Test getting list of available executors"""
        mock_check.side_effect = lambda et: ExecutorInfo(
            executor_type=et,
            available=(et == ExecutorType.CLAUDE_CODE),
            binary_path="/usr/bin/claude" if et == ExecutorType.CLAUDE_CODE else None,
        )

        available = get_available_executors()

        assert ExecutorType.CLAUDE_CODE in available
        assert ExecutorType.OPENCODE not in available

    @patch('aop.agent.executor.check_executor')
    def test_get_best_executor(self, mock_check):
        """Test getting best executor"""
        mock_check.side_effect = lambda et: ExecutorInfo(
            executor_type=et,
            available=(et == ExecutorType.OPENCODE),
        )

        best = get_best_executor()

        # Should return OPENCODE since CLAUDE_CODE is not available
        assert best == ExecutorType.OPENCODE


class TestOrchestrationConfig:
    """Tests for OrchestrationConfig"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = OrchestrationConfig()
        
        assert config.executor == ExecutorType.CLAUDE_CODE
        assert config.exec_timeout == 600
        assert config.exec_max_parallel == 5
        assert config.auto_clarify is True
        assert config.auto_generate_hypotheses is True
        assert config.auto_execute is True
        assert config.auto_validate is True
        assert config.auto_learn is True
        assert config.dry_run is False
        assert config.verbose is False
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = OrchestrationConfig(
            executor=ExecutorType.OPENCODE,
            exec_timeout=1200,
            dry_run=True,
            verbose=True,
        )
        
        assert config.executor == ExecutorType.OPENCODE
        assert config.exec_timeout == 1200
        assert config.dry_run is True
        assert config.verbose is True


class TestSprintResult:
    """Tests for SprintResult"""
    
    def test_sprint_result_creation(self):
        """Test creating SprintResult"""
        result = SprintResult(
            sprint_id="sprint-abc123",
            success=True,
            state=SprintState.COMPLETED,
            clarified_requirement={"summary": "Test"},
            hypotheses=[{"statement": "H1"}],
            execution_results=[],
            learnings=[],
            next_steps=[],
            summary="Test completed",
        )
        
        assert result.sprint_id == "sprint-abc123"
        assert result.success is True
        assert result.state == SprintState.COMPLETED


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator class"""
    
    def test_init_default_config(self):
        """Test orchestrator initialization with default config"""
        orchestrator = AgentOrchestrator()
        
        assert orchestrator.config is not None
        assert orchestrator.config.executor == ExecutorType.CLAUDE_CODE
        assert orchestrator.llm is None
    
    def test_init_custom_config(self):
        """Test orchestrator initialization with custom config"""
        config = OrchestrationConfig(executor=ExecutorType.OPENCODE)
        orchestrator = AgentOrchestrator(config=config)
        
        assert orchestrator.config.executor == ExecutorType.OPENCODE
    
    def test_discover_executors(self):
        """Test executor discovery method"""
        orchestrator = AgentOrchestrator()

        with patch('aop.agent.orchestrator.discover_all') as mock_discover:
            mock_discover.return_value = {
                ExecutorType.CLAUDE_CODE: ExecutorInfo(
                    executor_type=ExecutorType.CLAUDE_CODE,
                    available=True,
                )
            }

            result = orchestrator.discover_executors()

            assert len(result) == 1
            assert ExecutorType.CLAUDE_CODE in result

    def test_get_available_executors(self):
        """Test getting available executors from orchestrator"""
        orchestrator = AgentOrchestrator()

        with patch('aop.agent.orchestrator.discover_all') as mock_discover:
            mock_discover.return_value = {
                ExecutorType.CLAUDE_CODE: ExecutorInfo(
                    executor_type=ExecutorType.CLAUDE_CODE,
                    available=True,
                ),
                ExecutorType.OPENCODE: ExecutorInfo(
                    executor_type=ExecutorType.OPENCODE,
                    available=False,
                ),
            }

            available = orchestrator.get_available_executors()

            assert ExecutorType.CLAUDE_CODE in available
            assert ExecutorType.OPENCODE not in available
    
    @patch('aop.agent.orchestrator.SprintPersistence')
    @patch('aop.agent.orchestrator.RequirementClarifier')
    @patch('aop.agent.orchestrator.HypothesisGenerator')
    def test_orchestrate_dry_run(self, mock_hg, mock_clarifier, mock_persistence):
        """Test orchestration in dry run mode"""
        config = OrchestrationConfig(dry_run=True, verbose=True)
        orchestrator = AgentOrchestrator(config=config)
        
        # Mock the clarifier
        mock_clarifier_instance = MagicMock()
        mock_clarified = MagicMock()
        mock_clarified.summary = "Test requirement"
        mock_clarifier_instance.clarify.return_value = mock_clarified
        orchestrator.clarifier = mock_clarifier_instance
        
        # Mock the hypothesis generator
        mock_hg_instance = MagicMock()
        mock_hg_instance.generate.return_value = []
        orchestrator.hypothesis_generator = mock_hg_instance
        
        # Mock persistence
        mock_persistence_instance = MagicMock()
        orchestrator.persistence = mock_persistence_instance
        
        result = orchestrator.orchestrate("Build a test system")
        
        assert result.sprint_id.startswith("sprint-")
    
    def test_status_no_active_sprint(self):
        """Test status when no active sprint"""
        orchestrator = AgentOrchestrator()
        
        with patch.object(orchestrator.persistence, 'get_latest_active') as mock_get:
            mock_get.return_value = None
            
            status = orchestrator.status()
            
            assert status["status"] == "no_active_sprint"
    
    def test_status_with_sprint(self):
        """Test status with active sprint"""
        orchestrator = AgentOrchestrator()
        
        mock_context = MagicMock()
        mock_context.sprint_id = "sprint-abc123"
        mock_context.state = SprintState.CLARIFIED
        mock_context.hypotheses = []
        
        orchestrator.context = mock_context
        
        status = orchestrator.status()
        
        assert status["sprint_id"] == "sprint-abc123"
        assert status["state"] == "clarified"
        assert status["hypotheses_count"] == 0


class TestOrchestrateFunction:
    """Tests for the convenience orchestrate function"""
    
    @patch('aop.agent.orchestrator.AgentOrchestrator')
    def test_orchestrate_function(self, mock_orchestrator_class):
        """Test the convenience orchestrate function"""
        mock_instance = MagicMock()
        mock_result = MagicMock()
        mock_instance.orchestrate.return_value = mock_result
        mock_orchestrator_class.return_value = mock_instance
        
        result = orchestrate(
            "Build a test system",
            executor=ExecutorType.OPENCODE,
        )
        
        assert result == mock_result
        mock_orchestrator_class.assert_called_once()


class TestBackwardCompatibility:
    """Tests for backward compatibility with AgentDriver"""
    
    def test_orchestrator_uses_same_types(self):
        """Test that orchestrator uses same types as AgentDriver"""
        from aop.agent.types import (
            SprintContext,
            SprintState,
            SprintResult as TypesSprintResult,
        )
        
        # Verify types are compatible
        assert SprintState.CLARIFIED.value == "clarified"
        assert SprintState.COMPLETED.value == "completed"
    
    def test_executor_type_string_values(self):
        """Test executor type string values match expected"""
        assert ExecutorType.CLAUDE_CODE.value == "claude-code"
        assert ExecutorType.OPENCODE.value == "opencode"
        assert ExecutorType.CODEX.value == "codex"
