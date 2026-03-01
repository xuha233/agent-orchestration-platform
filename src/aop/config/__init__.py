"""Configuration management for AOP."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class AOPConfig:
    """AOP configuration."""
    
    project_type: str = "transformation"
    providers: List[str] = field(default_factory=lambda: ["claude", "codex"])
    default_timeout: int = 600
    max_parallel: int = 4
    output_dir: str = "runs"
    
    @classmethod
    def from_yaml(cls, path: Path) -> "AOPConfig":
        """Load configuration from YAML file.
        
        Args:
            path: Path to the YAML configuration file
            
        Returns:
            AOPConfig instance with loaded values or defaults
        """
        if not path.exists():
            return cls()
        
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        project = data.get("project", {})
        settings = data.get("settings", {})
        
        return cls(
            project_type=project.get("type", "transformation"),
            providers=settings.get("providers", ["claude", "codex"]),
            default_timeout=settings.get("default_timeout", 600),
            max_parallel=settings.get("max_parallel", 4),
            output_dir=settings.get("output_dir", "runs"),
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
