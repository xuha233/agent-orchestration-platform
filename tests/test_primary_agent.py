"""Tests for the primary agent abstraction layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from aop.primary import (
    AgentContext,
    AgentRegistry,
    ClaudeCodeAgent,
    OpenCodeAgent,
    PrimaryAgent,
    get_registry,
    reset_registry,
)


class TestAgentContext:
    """Tests for AgentContext."""

    def test_context_creation(self) -> None:
        """Test basic context creation."""
        ctx = AgentContext(workspace_path=Path("/tmp/test"))
        assert ctx.workspace_path == Path("/tmp/test")
        assert ctx.session_id is None
        assert ctx.history == []

    def test_context_with_session(self) -> None:
        """Test context with session ID."""
        ctx = AgentContext(
            workspace_path=Path("/tmp/test"),
            session_id="test-session-123",
        )
        assert ctx.session_id == "test-session-123"

    def test_context_with_history(self) -> None:
        """Test context with history."""
        history = [{"role": "user", "content": "Hello"}]
        ctx = AgentContext(
            workspace_path=Path("/tmp/test"),
            history=history,
        )
        assert ctx.history == history

    def test_context_default_history(self) -> None:
        """Test that history defaults to empty list."""
        ctx = AgentContext(workspace_path=Path("/tmp/test"))
        # Each call should return the same list instance
        assert ctx.history == []
        ctx.history.append("test")
        assert ctx.history == ["test"]


class TestClaudeCodeAgent:
    """Tests for ClaudeCodeAgent."""

    def test_agent_attributes(self) -> None:
        """Test agent has correct attributes."""
        agent = ClaudeCodeAgent()
        assert agent.id == "claude_code"
        assert agent.name == "Claude Code"
        assert agent.description == "Anthropic's Claude Code CLI agent"

    @patch("shutil.which")
    def test_is_available_true(self, mock_which: MagicMock) -> None:
        """Test is_available returns True when claude is found."""
        mock_which.return_value = "/usr/bin/claude"
        agent = ClaudeCodeAgent()
        assert agent.is_available() is True
        mock_which.assert_called_once_with("claude")

    @patch("shutil.which")
    def test_is_available_false(self, mock_which: MagicMock) -> None:
        """Test is_available returns False when claude is not found."""
        mock_which.return_value = None
        agent = ClaudeCodeAgent()
        assert agent.is_available() is False

    def test_get_session_id_initial(self) -> None:
        """Test initial session ID is None."""
        agent = ClaudeCodeAgent()
        assert agent.get_session_id() is None

    def test_resume_session(self) -> None:
        """Test resuming a session."""
        agent = ClaudeCodeAgent()
        result = agent.resume_session("test-session-456")
        assert result is True
        assert agent.get_session_id() == "test-session-456"

    def test_clear_session(self) -> None:
        """Test clearing a session."""
        agent = ClaudeCodeAgent()
        agent.resume_session("test-session-789")
        agent.clear_session()
        assert agent.get_session_id() is None

    @pytest.mark.asyncio
    async def test_chat_basic(
        self,
        tmp_path: Path,
    ) -> None:
        """Test basic chat functionality."""
        with patch("shutil.which", return_value="/usr/bin/claude"):
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                # Mock the subprocess
                mock_process = AsyncMock()
                mock_process.communicate = AsyncMock(
                    return_value=(b"Hello, I am Claude!", b"")
                )
                mock_process.returncode = 0  # Must be int, not AsyncMock
                mock_subprocess.return_value = mock_process

                agent = ClaudeCodeAgent()
                context = AgentContext(workspace_path=tmp_path)

                # Call chat
                result = await agent.chat("Hello", context)

                assert result == "Hello, I am Claude!"

                # Verify command was called correctly
                mock_subprocess.assert_called_once()
                call_args = mock_subprocess.call_args
                assert "claude" in call_args[0]
                assert "-p" in call_args[0]
                assert "Hello" in call_args[0]


class TestOpenCodeAgent:
    """Tests for OpenCodeAgent."""

    def test_agent_attributes(self) -> None:
        """Test agent has correct attributes."""
        agent = OpenCodeAgent()
        assert agent.id == "opencode"
        assert agent.name == "OpenCode"
        assert agent.description == "OpenCode CLI agent"

    @patch("shutil.which")
    def test_is_available_true(self, mock_which: MagicMock) -> None:
        """Test is_available returns True when opencode is found."""
        mock_which.return_value = "/usr/bin/opencode"
        agent = OpenCodeAgent()
        assert agent.is_available() is True
        mock_which.assert_called_once_with("opencode")

    @patch("shutil.which")
    def test_is_available_false(self, mock_which: MagicMock) -> None:
        """Test is_available returns False when opencode is not found."""
        mock_which.return_value = None
        agent = OpenCodeAgent()
        assert agent.is_available() is False

    def test_session_management(self) -> None:
        """Test session management."""
        agent = OpenCodeAgent()
        assert agent.get_session_id() is None

        agent.resume_session("opencode-session")
        assert agent.get_session_id() == "opencode-session"

        agent.clear_session()
        assert agent.get_session_id() is None


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    def test_empty_registry(self) -> None:
        """Test empty registry."""
        registry = AgentRegistry()
        assert registry.count() == 0
        assert registry.list_all() == []
        assert registry.list_available() == []
        assert registry.get_default() is None

    def test_register_agent(self) -> None:
        """Test registering an agent."""
        registry = AgentRegistry()
        agent = ClaudeCodeAgent()
        registry.register(agent)

        assert registry.count() == 1
        assert registry.get("claude_code") is agent

    def test_unregister_agent(self) -> None:
        """Test unregistering an agent."""
        registry = AgentRegistry()
        agent = ClaudeCodeAgent()
        registry.register(agent)

        assert registry.unregister("claude_code") is True
        assert registry.count() == 0
        assert registry.get("claude_code") is None

    def test_unregister_nonexistent(self) -> None:
        """Test unregistering a non-existent agent."""
        registry = AgentRegistry()
        assert registry.unregister("nonexistent") is False

    @patch.object(ClaudeCodeAgent, "is_available", return_value=True)
    @patch.object(OpenCodeAgent, "is_available", return_value=False)
    def test_list_available(
        self,
        mock_opencode_available: MagicMock,
        mock_claude_available: MagicMock,
    ) -> None:
        """Test listing available agents."""
        registry = AgentRegistry()
        registry.register(ClaudeCodeAgent())
        registry.register(OpenCodeAgent())

        available = registry.list_available()
        assert len(available) == 1
        assert available[0].id == "claude_code"

    @patch.object(ClaudeCodeAgent, "is_available", return_value=True)
    @patch.object(OpenCodeAgent, "is_available", return_value=False)
    def test_get_default(
        self,
        mock_opencode: MagicMock,
        mock_claude: MagicMock,
    ) -> None:
        """Test getting default agent."""
        registry = AgentRegistry()
        registry.register(OpenCodeAgent())
        registry.register(ClaudeCodeAgent())

        default = registry.get_default()
        assert default is not None
        assert default.id == "claude_code"

    @patch.object(ClaudeCodeAgent, "is_available", return_value=False)
    @patch.object(OpenCodeAgent, "is_available", return_value=False)
    def test_get_default_none_available(
        self,
        mock_opencode: MagicMock,
        mock_claude: MagicMock,
    ) -> None:
        """Test getting default when no agent is available."""
        registry = AgentRegistry()
        registry.register(ClaudeCodeAgent())
        registry.register(OpenCodeAgent())

        assert registry.get_default() is None

    def test_has_available(self) -> None:
        """Test has_available method."""
        registry = AgentRegistry()

        with patch.object(ClaudeCodeAgent, "is_available", return_value=True):
            registry.register(ClaudeCodeAgent())
            assert registry.has_available() is True

    def test_count_available(self) -> None:
        """Test count_available method."""
        registry = AgentRegistry()

        with patch.object(ClaudeCodeAgent, "is_available", return_value=True):
            with patch.object(OpenCodeAgent, "is_available", return_value=False):
                registry.register(ClaudeCodeAgent())
                registry.register(OpenCodeAgent())
                assert registry.count_available() == 1


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_registry()

    def teardown_method(self) -> None:
        """Reset registry after each test."""
        reset_registry()

    def test_get_registry_creates_instance(self) -> None:
        """Test get_registry creates a registry."""
        registry = get_registry()
        assert isinstance(registry, AgentRegistry)

    def test_get_registry_returns_same_instance(self) -> None:
        """Test get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2

    @patch.object(ClaudeCodeAgent, "is_available", return_value=True)
    def test_registry_auto_registers_agents(
        self,
        mock_available: MagicMock,
    ) -> None:
        """Test that get_registry auto-registers default agents."""
        registry = get_registry()
        assert registry.get("claude_code") is not None
        assert registry.get("opencode") is not None

    def test_reset_registry(self) -> None:
        """Test reset_registry creates new instance."""
        registry1 = get_registry()
        reset_registry()
        registry2 = get_registry()
        assert registry1 is not registry2


class TestPrimaryAgentProtocol:
    """Tests for PrimaryAgent protocol compliance."""

    def test_claude_code_is_primary_agent(self) -> None:
        """Test ClaudeCodeAgent implements PrimaryAgent."""
        agent: PrimaryAgent = ClaudeCodeAgent()
        assert hasattr(agent, "id")
        assert hasattr(agent, "name")
        assert hasattr(agent, "description")
        assert callable(agent.is_available)
        assert callable(agent.get_session_id)
        assert callable(agent.resume_session)
        assert callable(agent.clear_session)

    def test_opencode_is_primary_agent(self) -> None:
        """Test OpenCodeAgent implements PrimaryAgent."""
        agent: PrimaryAgent = OpenCodeAgent()
        assert hasattr(agent, "id")
        assert hasattr(agent, "name")
        assert hasattr(agent, "description")
        assert callable(agent.is_available)
        assert callable(agent.get_session_id)
        assert callable(agent.resume_session)
        assert callable(agent.clear_session)
