"""Persistent local config store for the desktop runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from aop.primary.workspace import AOP_DIR


DEFAULT_APP_RUNTIME_CONFIG: Dict[str, Any] = {
    "preferred_provider": "",
    "provider_envs": {},
}


class DesktopConfigStore:
    """Read and write desktop-specific runtime settings."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or AOP_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.base_dir / "desktop-runtime.json"

    def load(self) -> Dict[str, Any]:
        """Load persisted desktop config."""
        if not self.config_path.exists():
            return dict(DEFAULT_APP_RUNTIME_CONFIG)
        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return dict(DEFAULT_APP_RUNTIME_CONFIG)
        if not isinstance(payload, dict):
            return dict(DEFAULT_APP_RUNTIME_CONFIG)
        merged = dict(DEFAULT_APP_RUNTIME_CONFIG)
        merged.update(payload)
        if not isinstance(merged.get("provider_envs"), dict):
            merged["provider_envs"] = {}
        return merged

    def save(self, payload: Dict[str, Any]) -> None:
        """Persist desktop config."""
        merged = dict(DEFAULT_APP_RUNTIME_CONFIG)
        merged.update(payload)
        self.config_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update_provider(self, provider_id: str, values: Dict[str, str]) -> Dict[str, Any]:
        """Update stored env-style values for a provider."""
        payload = self.load()
        provider_envs = dict(payload.get("provider_envs", {}))
        current = dict(provider_envs.get(provider_id, {}))
        for key, value in values.items():
            key_name = str(key).strip()
            if not key_name:
                continue
            if value:
                current[key_name] = value
            else:
                current.pop(key_name, None)
        if current:
            provider_envs[provider_id] = current
        else:
            provider_envs.pop(provider_id, None)
        payload["provider_envs"] = provider_envs
        self.save(payload)
        return payload

    def set_preferred_provider(self, provider_id: str) -> Dict[str, Any]:
        """Persist preferred provider selection."""
        payload = self.load()
        payload["preferred_provider"] = provider_id
        self.save(payload)
        return payload
