"""Tests for config module."""

import pytest
from pathlib import Path
import tempfile
import os

from aop.config import AOPConfig, ReviewPolicy, find_config, load_config


class TestReviewPolicy:
    """Test ReviewPolicy dataclass."""
    
    def test_default_values(self):
        """Test default policy values."""
        policy = ReviewPolicy()
        assert policy.timeout_seconds == 180
        assert policy.stall_timeout_seconds == 900
        assert policy.poll_interval_seconds == 1.0
        assert policy.review_hard_timeout_seconds == 1800
        assert policy.enforce_findings_contract == False
        assert policy.max_retries == 1
        assert policy.high_escalation_threshold == 1
        assert policy.require_non_empty_findings == True
        assert policy.max_provider_parallelism == 0
        assert policy.provider_timeouts == {}
        assert policy.allow_paths == ["."]
        assert policy.provider_permissions == {}
        assert policy.enforcement_mode == "strict"
    
    def test_custom_values(self):
        """Test custom policy values."""
        policy = ReviewPolicy(
            timeout_seconds=300,
            stall_timeout_seconds=600,
            poll_interval_seconds=2.0,
            review_hard_timeout_seconds=900,
            enforce_findings_contract=True,
            max_retries=3,
            high_escalation_threshold=2,
            require_non_empty_findings=False,
            max_provider_parallelism=4,
            provider_timeouts={"claude": 120, "codex": 90},
            allow_paths=["src", "lib"],
            provider_permissions={"claude": {"permission_mode": "acceptEdits"}},
            enforcement_mode="best_effort",
        )
        assert policy.timeout_seconds == 300
        assert policy.stall_timeout_seconds == 600
        assert policy.poll_interval_seconds == 2.0
        assert policy.review_hard_timeout_seconds == 900
        assert policy.enforce_findings_contract == True
        assert policy.max_retries == 3
        assert policy.high_escalation_threshold == 2
        assert policy.require_non_empty_findings == False
        assert policy.max_provider_parallelism == 4
        assert policy.provider_timeouts == {"claude": 120, "codex": 90}
        assert policy.allow_paths == ["src", "lib"]
        assert policy.provider_permissions == {"claude": {"permission_mode": "acceptEdits"}}
        assert policy.enforcement_mode == "best_effort"
    
    def test_frozen(self):
        """Test that ReviewPolicy is immutable (frozen)."""
        policy = ReviewPolicy()
        with pytest.raises(Exception):  # FrozenInstanceError
            policy.timeout_seconds = 500


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
        assert config.artifact_base == "reports/review"
        assert isinstance(config.policy, ReviewPolicy)
    
    def test_custom_values(self):
        """Test custom configuration values."""
        policy = ReviewPolicy(timeout_seconds=300)
        config = AOPConfig(
            project_type="exploratory",
            providers=["claude", "gemini"],
            default_timeout=300,
            max_parallel=2,
            output_dir="output",
            artifact_base="artifacts",
            policy=policy,
        )
        assert config.project_type == "exploratory"
        assert config.providers == ["claude", "gemini"]
        assert config.default_timeout == 300
        assert config.max_parallel == 2
        assert config.output_dir == "output"
        assert config.artifact_base == "artifacts"
        assert config.policy.timeout_seconds == 300
    
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
  artifact_base: custom_artifacts
policy:
  timeout_seconds: 240
  stall_timeout_seconds: 600
  poll_interval_seconds: 0.5
  review_hard_timeout_seconds: 900
  enforce_findings_contract: true
  max_retries: 3
  high_escalation_threshold: 2
  require_non_empty_findings: false
  max_provider_parallelism: 4
  provider_timeouts:
    claude: 120
    codex: 90
  allow_paths:
    - src
    - lib
  provider_permissions:
    claude:
      permission_mode: acceptEdits
  enforcement_mode: best_effort
""")
            config = AOPConfig.from_yaml(config_path)
            assert config.project_type == "optimization"
            assert config.providers == ["claude", "gemini"]
            assert config.default_timeout == 300
            assert config.max_parallel == 2
            assert config.output_dir == "custom_output"
            assert config.artifact_base == "custom_artifacts"
            # Policy values
            assert config.policy.timeout_seconds == 240
            assert config.policy.stall_timeout_seconds == 600
            assert config.policy.poll_interval_seconds == 0.5
            assert config.policy.review_hard_timeout_seconds == 900
            assert config.policy.enforce_findings_contract == True
            assert config.policy.max_retries == 3
            assert config.policy.high_escalation_threshold == 2
            assert config.policy.require_non_empty_findings == False
            assert config.policy.max_provider_parallelism == 4
            assert config.policy.provider_timeouts == {"claude": 120, "codex": 90}
            assert config.policy.allow_paths == ["src", "lib"]
            assert config.policy.provider_permissions == {"claude": {"permission_mode": "acceptEdits"}}
            assert config.policy.enforcement_mode == "best_effort"
    
    def test_from_yaml_nonexistent(self):
        """Test loading from nonexistent YAML file returns defaults."""
        config = AOPConfig.from_yaml(Path("/nonexistent/.aop.yaml"))
        assert config.project_type == "transformation"
        assert config.providers == ["claude", "codex"]
        assert isinstance(config.policy, ReviewPolicy)
    
    def test_to_yaml(self):
        """Test saving to YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".aop.yaml"
            policy = ReviewPolicy(
                timeout_seconds=240,
                stall_timeout_seconds=600,
                provider_timeouts={"claude": 120},
            )
            config = AOPConfig(
                project_type="exploratory",
                providers=["claude", "gemini"],
                policy=policy,
            )
            config.to_yaml(config_path)
            
            assert config_path.exists()
            content = config_path.read_text()
            assert "exploratory" in content
            assert "claude" in content
            assert "gemini" in content
            assert "timeout_seconds: 240" in content
            assert "stall_timeout_seconds: 600" in content
    
    def test_to_yaml_includes_policy(self):
        """Test that to_yaml includes policy configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".aop.yaml"
            policy = ReviewPolicy(
                enforce_findings_contract=True,
                max_provider_parallelism=4,
                enforcement_mode="best_effort",
            )
            config = AOPConfig(policy=policy)
            config.to_yaml(config_path)
            
            content = config_path.read_text()
            assert "enforce_findings_contract: true" in content
            assert "max_provider_parallelism: 4" in content
            assert "enforcement_mode: best_effort" in content


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
policy:
  stall_timeout_seconds: 600
""")
            
            config = load_config(Path(tmpdir))
            assert config.project_type == "compliance_sensitive"
            assert config.providers == ["claude"]
            assert config.policy.stall_timeout_seconds == 600
    
    def test_load_missing_config_returns_defaults(self):
        """Test loading missing config returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_config(Path(tmpdir))
            assert config.project_type == "transformation"
            assert config.providers == ["claude", "codex"]
            assert isinstance(config.policy, ReviewPolicy)


class TestMCOCompatibility:
    """Test MCO configuration compatibility."""
    
    def test_review_policy_matches_mco_fields(self):
        """Test that ReviewPolicy has all MCO fields."""
        policy = ReviewPolicy()
        # All fields from MCO ReviewPolicy
        assert hasattr(policy, 'timeout_seconds')
        assert hasattr(policy, 'stall_timeout_seconds')
        assert hasattr(policy, 'poll_interval_seconds')
        assert hasattr(policy, 'review_hard_timeout_seconds')
        assert hasattr(policy, 'enforce_findings_contract')
        assert hasattr(policy, 'max_retries')
        assert hasattr(policy, 'high_escalation_threshold')
        assert hasattr(policy, 'require_non_empty_findings')
        assert hasattr(policy, 'max_provider_parallelism')
        assert hasattr(policy, 'provider_timeouts')
        assert hasattr(policy, 'allow_paths')
        assert hasattr(policy, 'provider_permissions')
        assert hasattr(policy, 'enforcement_mode')
    
    def test_default_values_match_mco(self):
        """Test that default values match MCO defaults."""
        policy = ReviewPolicy()
        # These should match MCO defaults
        assert policy.timeout_seconds == 180
        assert policy.stall_timeout_seconds == 900
        assert policy.poll_interval_seconds == 1.0
        assert policy.review_hard_timeout_seconds == 1800
        assert policy.enforce_findings_contract == False
        assert policy.max_retries == 1
        assert policy.enforcement_mode == "strict"
