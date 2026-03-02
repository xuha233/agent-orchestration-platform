"""Artifact path management for AOP."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

from .types.contracts import ProviderId


ARTIFACT_LAYOUT_VERSION = "stage-a-v1"
ROOT_FILES = ("summary.md", "decision.md", "findings.json", "run.json")
ROOT_DIRS = ("providers", "raw")


def task_artifact_root(base_dir: str, task_id: str) -> Path:
    """Get the artifact root directory for a task."""
    return Path(base_dir) / task_id


def provider_artifact_name(provider: ProviderId) -> str:
    """Get the artifact filename for a provider."""
    return f"{provider}.json"


def expected_paths(base_dir: str, task_id: str, providers: Iterable[ProviderId]) -> Dict[str, Path]:
    """Get all expected artifact paths for a task.
    
    Args:
        base_dir: Base directory for artifacts
        task_id: Task identifier
        providers: Iterable of provider IDs
    
    Returns:
        Dictionary mapping path names to Path objects
    """
    root = task_artifact_root(base_dir, task_id)
    paths: Dict[str, Path] = {"root": root}

    for filename in ROOT_FILES:
        paths[filename] = root / filename

    providers_dir = root / "providers"
    raw_dir = root / "raw"
    paths["providers_dir"] = providers_dir
    paths["raw_dir"] = raw_dir

    for provider in providers:
        paths[f"providers/{provider}.json"] = providers_dir / provider_artifact_name(provider)
        paths[f"raw/{provider}.stdout.log"] = raw_dir / f"{provider}.stdout.log"
        paths[f"raw/{provider}.stderr.log"] = raw_dir / f"{provider}.stderr.log"

    return paths
