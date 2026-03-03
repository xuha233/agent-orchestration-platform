"""Tests for LLM Client Layer"""

import pytest
from aop.llm import LLMClient, LLMProvider, LLMMessage, LLMResponse
from aop.llm.claude_client import ClaudeClient
from aop.llm.local_client import LocalLLMClient


class TestLLMMessage:
    """Test LLMMessage dataclass"""
    
    def test_create_message(self):
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_message_roles(self):
        roles = ["system", "user", "assistant"]
        for role in roles:
            msg = LLMMessage(role=role, content="test")
            assert msg.role == role


class TestLLMResponse:
    """Test LLMResponse dataclass"""
    
    def test_create_response(self):
        response = LLMResponse(
            content="Test response",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            finish_reason="stop"
        )
        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.usage["total_tokens"] == 15
        assert response.raw is None
    
    def test_response_with_raw(self):
        raw_data = {"id": "123", "created": 1234567890}
        response = LLMResponse(
            content="Test",
            model="test-model",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            finish_reason="stop",
            raw=raw_data
        )
        assert response.raw == raw_data


class TestLLMProvider:
    """Test LLMProvider enum"""
    
    def test_provider_values(self):
        assert LLMProvider.CLAUDE.value == "claude"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.LOCAL.value == "local"


class TestClaudeClient:
    """Test ClaudeClient"""
    
    def test_provider_property(self):
        client = ClaudeClient(api_key="test-key")
        assert client.provider == LLMProvider.CLAUDE
    
    def test_default_model(self):
        client = ClaudeClient()
        assert client.model == "claude-sonnet-4-20250514"
    
    def test_custom_model(self):
        client = ClaudeClient(model="claude-opus-4")
        assert client.model == "claude-opus-4"


class TestLocalLLMClient:
    """Test LocalLLMClient"""
    
    def test_provider_property(self):
        client = LocalLLMClient()
        assert client.provider == LLMProvider.LOCAL
    
    def test_default_settings(self):
        client = LocalLLMClient()
        assert client.command == "ollama"
        assert client.model == "llama3"
        assert client.timeout == 300
    
    def test_build_prompt(self):
        client = LocalLLMClient()
        messages = [
            LLMMessage(role="system", content="You are helpful"),
            LLMMessage(role="user", content="Hello"),
            LLMMessage(role="assistant", content="Hi there"),
        ]
        prompt = client._build_prompt(messages)
        assert "System: You are helpful" in prompt
        assert "User: Hello" in prompt
        assert "Assistant: Hi there" in prompt


class TestLLMClientInterface:
    """Test LLMClient abstract interface"""
    
    def test_count_tokens_default(self):
        """Test default token counting"""
        # Use LocalLLMClient to test the inherited method
        client = LocalLLMClient()
        text = "This is a test message"
        tokens = client.count_tokens(text)
        # Default is len(text) // 4
        assert tokens == len(text) // 4
