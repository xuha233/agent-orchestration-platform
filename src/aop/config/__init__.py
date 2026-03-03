"""Configuration management for AOP."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass(frozen=True)
class ReviewPolicy:
    """Fine-grained review policy configuration.
    
    This class aligns with MCO's ReviewPolicy for configuration compatibility.
    """
    timeout_seconds: int = 180
    stall_timeout_seconds: int = 900
    poll_interval_seconds: float = 1.0
    review_hard_timeout_seconds: int = 1800
    enforce_findings_contract: bool = False
    max_retries: int = 1
    high_escalation_threshold: int = 1
    require_non_empty_findings: bool = True
    max_provider_parallelism: int = 0
    provider_timeouts: Dict[str, int] = field(default_factory=dict)
    allow_paths: List[str] = field(default_factory=lambda: ["."])
    provider_permissions: Dict[str, Dict[str, str]] = field(default_factory=dict)
    enforcement_mode: str = "strict"  # "strict" or "best_effort"


@dataclass(frozen=True)
class SubagentConfig:
    """Sub-agent configuration for task delegation."""
    default_timeout: int = 600
    quick_win_timeout: int = 300
    deep_dive_timeout: int = 1800
    max_parallel: int = 3


@dataclass
class AOPConfig:
    """AOP configuration."""
    
    project_type: str = "transformation"
    providers: List[str] = field(default_factory=lambda: ["claude", "codex"])
    default_timeout: int = 600
    max_parallel: int = 4
    output_dir: str = "runs"
    artifact_base: str = "reports/review"
    policy: ReviewPolicy = field(default_factory=ReviewPolicy)
    subagent: SubagentConfig = field(default_factory=SubagentConfig)
    
    @classmethod
    def from_yaml(cls, path: Path | str) -> "AOPConfig":
        """Load configuration from YAML file.
        
        Args:
            path: Path to the YAML configuration file (Path object or string)
            
        Returns:
            AOPConfig instance with loaded values or defaults
        """
        # 支持字符串参数
        if isinstance(path, str):
            path = Path(path)
        
        if not path.exists():
            return cls()
        
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        project = data.get("project", {})
        settings = data.get("settings", {})
        policy_data = data.get("policy", {})
        
        # Build ReviewPolicy from config
        policy = ReviewPolicy(
            timeout_seconds=policy_data.get("timeout_seconds", 180),
            stall_timeout_seconds=policy_data.get("stall_timeout_seconds", 900),
            poll_interval_seconds=policy_data.get("poll_interval_seconds", 1.0),
            review_hard_timeout_seconds=policy_data.get("review_hard_timeout_seconds", 1800),
            enforce_findings_contract=policy_data.get("enforce_findings_contract", False),
            max_retries=policy_data.get("max_retries", 1),
            high_escalation_threshold=policy_data.get("high_escalation_threshold", 1),
            require_non_empty_findings=policy_data.get("require_non_empty_findings", True),
            max_provider_parallelism=policy_data.get("max_provider_parallelism", 0),
            provider_timeouts=policy_data.get("provider_timeouts", {}),
            allow_paths=policy_data.get("allow_paths", ["."]),
            provider_permissions=policy_data.get("provider_permissions", {}),
            enforcement_mode=policy_data.get("enforcement_mode", "strict"),
        )
        
        # Build SubagentConfig from config
        subagent_data = data.get("subagent", {})
        subagent = SubagentConfig(
            default_timeout=subagent_data.get("default_timeout", 600),
            quick_win_timeout=subagent_data.get("quick_win_timeout", 300),
            deep_dive_timeout=subagent_data.get("deep_dive_timeout", 1800),
            max_parallel=subagent_data.get("max_parallel", 3),
        )
        
        return cls(
            project_type=project.get("type", "transformation"),
            providers=settings.get("providers", ["claude", "codex"]),
            default_timeout=settings.get("default_timeout", 600),
            max_parallel=settings.get("max_parallel", 4),
            output_dir=settings.get("output_dir", "runs"),
            artifact_base=settings.get("artifact_base", "reports/review"),
            policy=policy,
            subagent=subagent,
        )
    
    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file.
        
        Args:
            path: Path where to save the configuration file
        """
        data = {
            "project": {"type": self.project_type},
            "settings": {
                "providers": self.providers,
                "default_timeout": self.default_timeout,
                "max_parallel": self.max_parallel,
                "output_dir": self.output_dir,
                "artifact_base": self.artifact_base,
            },
            "policy": {
                "timeout_seconds": self.policy.timeout_seconds,
                "stall_timeout_seconds": self.policy.stall_timeout_seconds,
                "poll_interval_seconds": self.policy.poll_interval_seconds,
                "review_hard_timeout_seconds": self.policy.review_hard_timeout_seconds,
                "enforce_findings_contract": self.policy.enforce_findings_contract,
                "max_retries": self.policy.max_retries,
                "high_escalation_threshold": self.policy.high_escalation_threshold,
                "require_non_empty_findings": self.policy.require_non_empty_findings,
                "max_provider_parallelism": self.policy.max_provider_parallelism,
                "provider_timeouts": self.policy.provider_timeouts,
                "allow_paths": self.policy.allow_paths,
                "provider_permissions": self.policy.provider_permissions,
                "enforcement_mode": self.policy.enforcement_mode,
            }
        }
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def find_config(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Find .aop.yaml or aop.yaml in current or parent directories.
    
    Searches for configuration files in the following order:
    1. .aop.yaml (hidden, preferred)
    2. aop.yaml (alternative)
    
    Args:
        start_dir: Directory to start searching from. Defaults to current directory.
        
    Returns:
        Path to the configuration file, or None if not found.
    """
    current = Path(start_dir or ".").resolve()
    
    for parent in [current] + list(current.parents):
        # Check for .aop.yaml first (preferred)
        hidden_config = parent / ".aop.yaml"
        if hidden_config.exists():
            return hidden_config
        
        # Then check for aop.yaml
        regular_config = parent / "aop.yaml"
        if regular_config.exists():
            return regular_config
    
    return None


def load_config(start_dir: Optional[Path] = None) -> AOPConfig:
    """Load configuration from nearest .aop.yaml or aop.yaml.
    
    Args:
        start_dir: Directory to start searching from. Defaults to current directory.
        
    Returns:
        AOPConfig instance with loaded values or defaults.
    """
    config_path = find_config(start_dir)
    if config_path:
        return AOPConfig.from_yaml(config_path)
    return AOPConfig()
