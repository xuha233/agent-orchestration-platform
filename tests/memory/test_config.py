# -*- coding: utf-8 -*-
"""Tests for memory configuration."""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import yaml

from aop.memory.config import (
    MemoryBackend,
    MemoryConfig,
    create_default_config,
    DEFAULT_CONFIG_TEMPLATE,
)


class TestMemoryBackend:
    """Test MemoryBackend enum."""
    
    def test_backend_values(self):
        """Test that backend enum has expected values."""
        assert MemoryBackend.FILE.value == "file"
        assert MemoryBackend.MEM0_LOCAL.value == "mem0_local"
        assert MemoryBackend.MEM0_QDRANT.value == "mem0_qdrant"
        assert MemoryBackend.MEM0_CHROMA.value == "mem0_chroma"
    
    def test_backend_from_string(self):
        """Test creating backend from string."""
        assert MemoryBackend("file") == MemoryBackend.FILE
        assert MemoryBackend("mem0_local") == MemoryBackend.MEM0_LOCAL


class TestMemoryConfig:
    """Test MemoryConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MemoryConfig()
        
        # 默认禁用 mem0（向后兼容）
        assert config.enabled is False
        assert config.backend == MemoryBackend.FILE
        assert config.project_id == "default"
        assert config.search_top_k == 5
        assert config.search_threshold == 0.7
    
    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "enabled": True,
            "backend": "mem0_local",
            "project_id": "test-project",
            "search_top_k": 10,
        }
        
        config = MemoryConfig.from_dict(data)
        
        assert config.enabled is True
        assert config.backend == MemoryBackend.MEM0_LOCAL
        assert config.project_id == "test-project"
        assert config.search_top_k == 10
    
    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = MemoryConfig(
            enabled=True,
            backend=MemoryBackend.MEM0_LOCAL,
            project_id="my-project",
        )
        
        data = config.to_dict()
        
        assert data["enabled"] is True
        assert data["backend"] == "mem0_local"
        assert data["project_id"] == "my-project"
    
    def test_config_yaml_roundtrip(self):
        """Test saving and loading config from YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "memory_config.yaml"
            
            original = MemoryConfig(
                enabled=True,
                backend=MemoryBackend.MEM0_LOCAL,
                project_id="yaml-test",
                search_top_k=15,
            )
            
            original.to_yaml(config_path)
            
            # Verify file exists
            assert config_path.exists()
            
            # Load and compare
            loaded = MemoryConfig.from_yaml(config_path)
            
            assert loaded.enabled == original.enabled
            assert loaded.backend == original.backend
            assert loaded.project_id == original.project_id
            assert loaded.search_top_k == original.search_top_k
    
    def test_get_mem0_user_id(self):
        """Test mem0 user ID generation for project isolation."""
        config = MemoryConfig(project_id="my-project")
        assert config.get_mem0_user_id() == "my-project"
        
        config = MemoryConfig(
            project_id="my-project",
            agent_namespace="reviewer",
        )
        assert config.get_mem0_user_id() == "my-project_reviewer"
    
    def test_invalid_backend_falls_back_to_file(self):
        """Test that invalid backend string falls back to FILE."""
        data = {"backend": "invalid_backend"}
        config = MemoryConfig.from_dict(data)
        assert config.backend == MemoryBackend.FILE


class TestCreateDefaultConfig:
    """Test default config creation."""
    
    def test_create_default_config(self):
        """Test creating default config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "memory_config.yaml"
            
            create_default_config(config_path)
            
            assert config_path.exists()
            
            # Verify content is valid YAML
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            assert data["enabled"] is False
            assert data["backend"] == "mem0_local"
    
    def test_default_config_template(self):
        """Test that default template contains expected fields."""
        assert "enabled: false" in DEFAULT_CONFIG_TEMPLATE
        assert "backend: mem0_local" in DEFAULT_CONFIG_TEMPLATE
        assert "project_id" in DEFAULT_CONFIG_TEMPLATE
