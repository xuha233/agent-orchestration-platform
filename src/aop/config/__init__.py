"""Configuration management for AOP."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

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
        """Load configuration from YAML file."""
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
        """Save configuration to YAML file."""
        data = {
            "project": {"type": self.project_type},
            "settings": {
                "providers": self.providers,
                "default_timeout": self.default_timeout,
                "max_parallel": self.max_parallel,
                "output_dir": self.output_dir,
            }
        }
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def find_config(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Find aop.yaml in current or parent directories."""
    current = Path(start_dir or ".").resolve()
    
    for parent in [current] + list(current.parents):
        config_path = parent / "aop.yaml"
        if config_path.exists():
            return config_path
    
    return None


def load_config(start_dir: Optional[Path] = None) -> AOPConfig:
    """Load configuration from nearest aop.yaml."""
    config_path = find_config(start_dir)
    if config_path:
        return AOPConfig.from_yaml(config_path)
    return AOPConfig()
