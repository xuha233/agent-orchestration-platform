"""Tests for config module."""

import pytest
from pathlib import Path
import tempfile
import os

from aop.config import AOPConfig, find_config, load_config


class TestAOPConfig:
    """Test AOPConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = AOPConfig()
        assert config.project_type == "transformation"
        assert config.providers == ["claude", "codex"]
        assert config.default_timeout == 600
        assert config.max_parallel == 4
        assert config.output_dir == "runs"
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = AOPConfig(
            project_type="exploratory",
            providers=["claude", "gemini"],
            default_timeout=300,
            max_parallel=2,
            output_dir="output"
        )
        assert config.project_type == "exploratory"
        assert config.providers == ["claude", "gemini"]
        assert config.default_timeout == 300
        assert config.max_parallel == 2
        assert config.output_dir == "output"
    
    def test_from_yaml(self):
        """Test loading from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".aop.yaml"
            config_path.write_text("""
project:
  type: optimization
settings:
  providers:
    - claude
    - gemini
  default_timeout: 300
  max_parallel: 2
  output_dir: custom_output
""")
            config = AOPConfig.from_yaml(config_path)
            assert config.project_type == "optimization"
            assert config.providers == ["claude", "gemini"]
            assert config.default_timeout == 300
            assert config.max_parallel == 2
            assert config.output_dir == "custom_output"
    
    def test_from_yaml_nonexistent(self):
        """Test loading from nonexistent YAML file returns defaults."""
        config = AOPConfig.from_yaml(Path("/nonexistent/.aop.yaml"))
        assert config.project_type == "transformation"
        assert config.providers == ["claude", "codex"]
    
    def test_to_yaml(self):
        """Test saving to YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".aop.yaml"
            config = AOPConfig(
                project_type="exploratory",
                providers=["claude", "gemini"]
            )
            config.to_yaml(config_path)
            
            assert config_path.exists()
            content = config_path.read_text()
            assert "exploratory" in content
            assert "claude" in content
            assert "gemini" in content


class TestFindConfig:
    """Test find_config function."""
    
    def test_find_hidden_config(self):
        """Test finding .aop.yaml (hidden config)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".aop.yaml"
            config_path.write_text("project: {}")
            
            result = find_config(Path(tmpdir))
            assert result == config_path
    
    def test_find_regular_config(self):
        """Test finding aop.yaml (regular config)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "aop.yaml"
            config_path.write_text("project: {}")
            
            result = find_config(Path(tmpdir))
            assert result == config_path
    
    def test_hidden_config_takes_precedence(self):
        """Test that .aop.yaml takes precedence over aop.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hidden_path = Path(tmpdir) / ".aop.yaml"
            regular_path = Path(tmpdir) / "aop.yaml"
            hidden_path.write_text("project: {}")
            regular_path.write_text("project: {}")
            
            result = find_config(Path(tmpdir))
            assert result == hidden_path
    
    def test_find_config_in_parent(self):
        """Test finding config in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".aop.yaml"
            config_path.write_text("project: {}")
            
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            
            result = find_config(subdir)
            assert result == config_path
    
    def test_find_config_not_found(self):
        """Test when no config is found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = find_config(Path(tmpdir))
            assert result is None


class TestLoadConfig:
    """Test load_config function."""
    
    def test_load_existing_config(self):
        """Test loading existing configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".aop.yaml"
            config_path.write_text("""
project:
  type: compliance_sensitive
settings:
  providers:
    - claude
""")
            
            config = load_config(Path(tmpdir))
            assert config.project_type == "compliance_sensitive"
            assert config.providers == ["claude"]
    
    def test_load_missing_config_returns_defaults(self):
        """Test loading missing config returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_config(Path(tmpdir))
            assert config.project_type == "transformation"
            assert config.providers == ["claude", "codex"]
