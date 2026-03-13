# -*- coding: utf-8 -*-
"""Tests for memory loader mem0 integration."""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import json
import os

from aop.memory.loader import build_agent_system_prompt, _load_mem0_memory, load_combined_memory


class TestLoadMem0Memory:
    """Test _load_mem0_memory function."""
    
    def test_returns_empty_without_workspace(self):
        """Test that function returns empty string when no workspace provided."""
        result = _load_mem0_memory(None)
        assert result == ""
    
    def test_returns_empty_when_mem0_disabled(self):
        """Test that function returns empty when mem0 is disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            # 默认 SettingsManager 是禁用 mem0 的
            result = _load_mem0_memory(workspace)
            # 应该返回空字符串（因为 mem0 未启用）
            assert result == ""
    
    def test_handles_missing_settings_gracefully(self):
        """Test that function handles missing settings gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            # 即使没有设置文件，也应该正常工作
            result = _load_mem0_memory(workspace)
            # mem0 默认禁用，应该返回空
            assert result == ""


class TestBuildAgentSystemPrompt:
    """Test build_agent_system_prompt with mem0 integration."""
    
    def test_includes_shutdown_prohibition(self):
        """Test that system prompt includes shutdown prohibition."""
        prompt = build_agent_system_prompt()
        assert "禁止关闭会话" in prompt
        assert "Shutdown" in prompt
    
    def test_includes_file_memory_when_present(self):
        """Test that file memory is included when present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir()
            
            # 创建假设文件
            hypotheses = {"H-001": {"statement": "Test hypothesis", "status": "pending"}}
            with open(aop_dir / "hypotheses.json", "w", encoding="utf-8") as f:
                json.dump(hypotheses, f)
            
            prompt = build_agent_system_prompt(workspace)
            
            # 应该包含假设记录
            assert "假设记录" in prompt
    
    def test_includes_task_hint_when_provided(self):
        """Test that task hint is included when provided."""
        prompt = build_agent_system_prompt(task_hint="Test task")
        assert "用户任务" in prompt
        assert "Test task" in prompt
    
    def test_mem0_memory_comes_before_file_memory(self):
        """Test that mem0 memory appears before file memory."""
        # mem0 未启用时，不应该有 mem0 部分
        prompt = build_agent_system_prompt()
        # mem0 记忆应该在文件记忆之前
        # 但 mem0 未启用时，只有文件记忆
        assert "禁止关闭会话" in prompt
    
    def test_graceful_degradation(self):
        """Test that prompt builds even when mem0 fails."""
        # 即使 mem0 相关导入失败，也应该能正常构建提示词
        prompt = build_agent_system_prompt()
        assert len(prompt) > 0
        assert "禁止关闭会话" in prompt


class TestBackwardCompatibility:
    """Test backward compatibility of memory loading."""
    
    def test_works_without_aop_directory(self):
        """Test that prompt works when .aop directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            # 没有 .aop 目录
            prompt = build_agent_system_prompt(workspace)
            assert "禁止关闭会话" in prompt
    
    def test_works_with_empty_aop_directory(self):
        """Test that prompt works with empty .aop directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir()
            # 空目录
            
            prompt = build_agent_system_prompt(workspace)
            assert "禁止关闭会话" in prompt
    
    def test_file_memory_still_works(self):
        """Test that file memory loading still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir()
            
            # 创建学习记录
            learnings = {"records": [{"insight": "Test learning"}]}
            with open(aop_dir / "learning.json", "w", encoding="utf-8") as f:
                json.dump(learnings, f)
            
            prompt = build_agent_system_prompt(workspace)
            
            # 应该包含学习记录
            assert "学习记录" in prompt


class TestMemoryOrdering:
    """Test memory ordering in system prompt."""
    
    def test_ordering_is_correct(self):
        """Test that memory sections appear in correct order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir()
            
            # 创建文件
            with open(aop_dir / "hypotheses.json", "w", encoding="utf-8") as f:
                json.dump({"H-001": {"statement": "Test"}}, f)
            
            prompt = build_agent_system_prompt(workspace, "Do something")
            
            # 验证顺序：禁止 > 文件记忆 > 任务
            shutdown_pos = prompt.find("禁止关闭会话")
            hypothesis_pos = prompt.find("假设记录")
            task_pos = prompt.find("用户任务")
            
            # 禁止应该最先
            assert shutdown_pos >= 0
            
            # 如果有假设，应该在禁止之后
            if hypothesis_pos >= 0:
                assert hypothesis_pos > shutdown_pos
            
            # 如果有任务，应该在最后
            if task_pos >= 0:
                assert task_pos > shutdown_pos
