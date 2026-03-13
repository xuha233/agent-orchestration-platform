# -*- coding: utf-8 -*-
"""Tests for memory service."""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import json

from aop.memory.config import MemoryConfig, MemoryBackend
from aop.memory.service import MemoryService


class TestMemoryService:
    """Test MemoryService class."""
    
    def test_service_initialization_default(self):
        """Test service initialization with default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = MemoryService(workspace_path=Path(tmpdir))
            
            assert service.config.enabled is False
            assert service.current_backend == MemoryBackend.FILE
    
    def test_service_initialization_with_config(self):
        """Test service initialization with custom config."""
        config = MemoryConfig(
            enabled=False,
            project_id="test-project",
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            assert service.config.project_id == "test-project"
    
    def test_add_memory_to_file(self):
        """Test adding memory to file storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            memory_id = service.add(
                "Test memory content",
                metadata={"type": "test", "phase": "build"},
            )
            
            assert memory_id is not None
            assert memory_id.startswith("mem_")
    
    def test_search_memory_from_file(self):
        """Test searching memory from file storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            # Add some memories
            service.add("Authentication works correctly", metadata={"type": "finding"})
            service.add("Database connection issue", metadata={"type": "issue"})
            service.add("Cache improves performance", metadata={"type": "finding"})
            
            # Search
            results = service.search("authentication")
            
            assert len(results) >= 1
            assert any("authentication" in r["content"].lower() for r in results)
    
    def test_get_memory_from_file(self):
        """Test getting a specific memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            memory_id = service.add("Specific memory", metadata={"type": "test"})
            
            memory = service.get(memory_id)
            
            assert memory is not None
            assert memory["content"] == "Specific memory"
            assert memory["metadata"]["type"] == "test"
    
    def test_delete_memory_from_file(self):
        """Test deleting a memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            memory_id = service.add("Memory to delete", metadata={"type": "test"})
            
            # Delete
            assert service.delete(memory_id) is True
            
            # Verify deleted
            assert service.get(memory_id) is None
    
    def test_list_memories_from_file(self):
        """Test listing all memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            # Add memories
            service.add("Memory 1", metadata={"type": "test"})
            service.add("Memory 2", metadata={"type": "finding"})
            service.add("Memory 3", metadata={"type": "test"})
            
            # List all
            all_memories = service.list_all(limit=100)
            assert len(all_memories) == 3
            
            # Filter by type
            test_memories = service.list_all(
                metadata_filter={"type": "test"},
                limit=100
            )
            assert len(test_memories) == 2
    
    def test_clear_memories_from_file(self):
        """Test clearing all memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            # Add memories
            service.add("Memory 1", metadata={"type": "test"})
            service.add("Memory 2", metadata={"type": "test"})
            
            # Clear
            count = service.clear()
            
            # Verify cleared
            memories = service.list_all(limit=100)
            assert len(memories) == 0
    
    def test_hypotheses_compatibility(self):
        """Test hypotheses API compatibility."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = MemoryService(workspace_path=Path(tmpdir))
            
            hypotheses = {
                "H-001": {
                    "statement": "Test hypothesis",
                    "state": "pending",
                }
            }
            
            service.save_hypotheses(hypotheses)
            loaded = service.load_hypotheses()
            
            assert "H-001" in loaded
            assert loaded["H-001"]["statement"] == "Test hypothesis"
    
    def test_learnings_compatibility(self):
        """Test learnings API compatibility."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = MemoryService(workspace_path=Path(tmpdir))
            
            learnings = [
                {
                    "phase": "build",
                    "what_worked": ["TDD approach"],
                    "what_failed": ["Big design upfront"],
                }
            ]
            
            service.save_learnings(learnings)
            loaded = service.load_learnings()
            
            assert len(loaded) == 1
            assert loaded[0]["phase"] == "build"
    
    def test_get_status(self):
        """Test getting service status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(
                enabled=False,
                project_id="status-test",
            )
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            status = service.get_status()
            
            assert status["enabled"] is False
            assert status["backend"] == "file"
            assert status["project_id"] == "status-test"
            assert "workspace" in status
    
    def test_mem0_not_available_fallback(self):
        """Test that service falls back to file when mem0 is not available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 启用 mem0 但不安装
            config = MemoryConfig(enabled=True, backend=MemoryBackend.MEM0_LOCAL)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            # mem0 不可用，应该回退到文件
            assert service.is_mem0_available is False
            assert service.current_backend == MemoryBackend.FILE
            
            # 操作应该仍然成功
            memory_id = service.add("Fallback test", metadata={"type": "test"})
            assert memory_id is not None


class TestMemoryServiceSearch:
    """Test memory search functionality."""
    
    def test_keyword_search(self):
        """Test keyword-based search in file storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            service.add("The authentication system uses JWT tokens", metadata={"type": "architecture"})
            service.add("Database authentication failed", metadata={"type": "issue"})
            service.add("Cache strategy for session data", metadata={"type": "architecture"})
            
            # 搜索包含 "authentication" 的记忆
            results = service.search("authentication")
            
            assert len(results) >= 2
    
    def test_search_with_metadata_filter(self):
        """Test search with metadata filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            service.add("Error in login flow", metadata={"type": "issue", "phase": "auth"})
            service.add("Error in payment flow", metadata={"type": "issue", "phase": "payment"})
            service.add("Success in login flow", metadata={"type": "success", "phase": "auth"})
            
            # 搜索 "error" 并过滤 type=issue
            results = service.search("error", metadata_filter={"type": "issue"})
            
            assert len(results) >= 2
            for r in results:
                assert r["metadata"]["type"] == "issue"
    
    def test_search_limit(self):
        """Test search result limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            
            # 添加多个匹配的记忆
            for i in range(10):
                service.add(f"Test memory {i}", metadata={"type": "test"})
            
            results = service.search("test", top_k=3)
            
            assert len(results) == 3
