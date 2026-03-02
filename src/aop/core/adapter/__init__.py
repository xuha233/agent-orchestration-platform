"""Provider adapters."""

from __future__ import annotations

from typing import Dict, List

from ..types import ProviderId, ProviderPresence
from .shim import ShimAdapterBase
from .parsing import extract_final_text_from_output, extract_token_usage_from_output, normalize_findings_from_text, inspect_contract_output


class ClaudeAdapter(ShimAdapterBase):
    """Adapter for Anthropic Claude CLI."""
    
    def __init__(self) -> None:
        from ..types.contracts import CapabilitySet
        super().__init__(
            provider_id="claude",
            binary_name="claude",
            capability_set=CapabilitySet(
                tiers=["C0", "C1", "C2", "C3", "C4", "C5", "C6"],
                supports_native_async=False,
                supports_poll_endpoint=False,
                supports_resume_after_restart=True,
                supports_schema_enforcement=True,
                min_supported_version="2.1.59",
                tested_os=["macos"],
            ),
        )

    def _auth_check_command(self, binary: str) -> List[str]:
        return [binary, "auth", "status"]

    def supported_permission_keys(self) -> List[str]:
        return ["permission_mode"]

    def _build_command(self, input_task) -> List[str]:
        from ..types.contracts import TaskInput
        permission_mode = "plan"
        raw_permissions = input_task.metadata.get("provider_permissions")
        if isinstance(raw_permissions, dict):
            value = raw_permissions.get("permission_mode")
            if isinstance(value, str) and value.strip():
                permission_mode = value.strip()
        return [
            "claude",
            "-p",
            "--permission-mode",
            permission_mode,
            "--output-format",
            "text",
            input_task.prompt,
        ]

    def _build_command_for_record(self) -> List[str]:
        return ["claude", "-p", "--permission-mode", "plan", "--output-format", "text", "<prompt>"]

    def _is_success(self, return_code: int, stdout_text: str, stderr_text: str) -> bool:
        if return_code != 0:
            return False
        text = f"{stdout_text}\n{stderr_text}".lower()
        return "api error" not in text

    def normalize(self, raw, ctx):
        from ..types.contracts import NormalizeContext, NormalizedFinding
        text = raw if isinstance(raw, str) else ""
        return normalize_findings_from_text(text, ctx, "claude")


class CodexAdapter(ShimAdapterBase):
    """Adapter for OpenAI Codex CLI."""
    
    def __init__(self) -> None:
        from ..types.contracts import CapabilitySet
        super().__init__(
            provider_id="codex",
            binary_name="codex",
            capability_set=CapabilitySet(
                tiers=["C0", "C1", "C2", "C3", "C4", "C5"],
                supports_native_async=False,
                supports_poll_endpoint=False,
                supports_resume_after_restart=True,
                supports_schema_enforcement=True,
                min_supported_version="0.46.0",
                tested_os=["macos"],
            ),
        )

    def _auth_check_command(self, binary: str) -> List[str]:
        return [binary, "login", "status"]

    def supported_permission_keys(self) -> List[str]:
        return ["sandbox"]

    def _build_command(self, input_task) -> List[str]:
        sandbox = "workspace-write"
        raw_permissions = input_task.metadata.get("provider_permissions")
        if isinstance(raw_permissions, dict):
            value = raw_permissions.get("sandbox")
            if isinstance(value, str) and value.strip():
                sandbox = value.strip()
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "-C",
            input_task.repo_root,
            "--sandbox",
            sandbox,
            "--json",
        ]
        output_schema_path = input_task.metadata.get("output_schema_path")
        if isinstance(output_schema_path, str) and output_schema_path.strip():
            cmd.extend(["--output-schema", output_schema_path.strip()])
        cmd.append(input_task.prompt)
        return cmd

    def _build_command_for_record(self) -> List[str]:
        return [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "-C",
            "<repo_root>",
            "--sandbox",
            "workspace-write",
            "--json",
            "--output-schema",
            "<schema-path>",
            "<prompt>",
        ]

    def _is_success(self, return_code: int, stdout_text: str, stderr_text: str) -> bool:
        if return_code == 0:
            return True
        if stdout_text.strip() and '"type":"turn.completed"' in stdout_text:
            return True
        if stdout_text.strip() and '"ok":true' in stdout_text:
            return True
        if "mcp client" in stderr_text.lower() and stdout_text.strip():
            return True
        return False

    def normalize(self, raw, ctx):
        from ..types.contracts import NormalizeContext, NormalizedFinding
        text = raw if isinstance(raw, str) else ""
        return normalize_findings_from_text(text, ctx, "codex")


class GeminiAdapter(ShimAdapterBase):
    """Adapter for Google Gemini CLI."""
    
    def __init__(self) -> None:
        from ..types.contracts import CapabilitySet
        super().__init__(
            provider_id="gemini",
            binary_name="gemini",
            capability_set=CapabilitySet(
                tiers=["C0", "C1", "C2", "C3"],
                supports_native_async=False,
                supports_poll_endpoint=False,
                supports_resume_after_restart=False,
                supports_schema_enforcement=False,
                min_supported_version="0.1.7",
                tested_os=["macos"],
            ),
        )

    def _auth_check_command(self, binary: str) -> List[str]:
        return [binary, "-p", "Reply with exactly OK"]

    def _build_command(self, input_task) -> List[str]:
        return ["gemini", "-p", input_task.prompt]

    def _build_command_for_record(self) -> List[str]:
        return ["gemini", "-p", "<prompt>"]

    def _is_success(self, return_code: int, stdout_text: str, stderr_text: str) -> bool:
        if return_code != 0:
            return False
        text = f"{stdout_text}\n{stderr_text}".lower()
        if "unknown arguments" in text:
            return False
        if "api error" in text:
            return False
        return True

    def normalize(self, raw, ctx):
        from ..types.contracts import NormalizeContext, NormalizedFinding
        text = raw if isinstance(raw, str) else ""
        return normalize_findings_from_text(text, ctx, "gemini")


class OpenCodeAdapter(ShimAdapterBase):
    """Adapter for OpenCode CLI."""
    
    def __init__(self) -> None:
        from ..types.contracts import CapabilitySet
        super().__init__(
            provider_id="opencode",
            binary_name="opencode",
            capability_set=CapabilitySet(
                tiers=["C0", "C1", "C2", "C3", "C4"],
                supports_native_async=True,
                supports_poll_endpoint=True,
                supports_resume_after_restart=True,
                supports_schema_enforcement=False,
                min_supported_version="1.2.11",
                tested_os=["macos"],
            ),
        )

    def _auth_check_command(self, binary: str) -> List[str]:
        return [binary, "auth", "list"]

    def _build_command(self, input_task) -> List[str]:
        return ["opencode", "run", input_task.prompt, "--format", "json"]

    def _build_command_for_record(self) -> List[str]:
        return ["opencode", "run", "<prompt>", "--format", "json"]

    def normalize(self, raw, ctx):
        from ..types.contracts import NormalizeContext, NormalizedFinding
        text = raw if isinstance(raw, str) else ""
        return normalize_findings_from_text(text, ctx, "opencode")


class QwenAdapter(ShimAdapterBase):
    """Adapter for Alibaba Qwen models."""
    
    def __init__(self) -> None:
        from ..types.contracts import CapabilitySet
        super().__init__(
            provider_id="qwen",
            binary_name="qwen",
            capability_set=CapabilitySet(
                tiers=["C0", "C1", "C2", "C3"],
                supports_native_async=False,
                supports_poll_endpoint=False,
                supports_resume_after_restart=True,
                supports_schema_enforcement=False,
                min_supported_version="0.10.6",
                tested_os=["macos"],
            ),
        )

    def _auth_check_command(self, binary: str) -> List[str]:
        return [binary, "Reply with exactly OK", "--output-format", "text", "--auth-type", "qwen-oauth"]

    def _build_command(self, input_task) -> List[str]:
        return ["qwen", input_task.prompt, "--output-format", "json", "--auth-type", "qwen-oauth"]

    def _build_command_for_record(self) -> List[str]:
        return ["qwen", "<prompt>", "--output-format", "json", "--auth-type", "qwen-oauth"]

    def normalize(self, raw, ctx):
        from ..types.contracts import NormalizeContext, NormalizedFinding
        text = raw if isinstance(raw, str) else ""
        return normalize_findings_from_text(text, ctx, "qwen")


def get_adapter_registry() -> Dict[str, ShimAdapterBase]:
    """Get registry of all available adapters."""
    return {
        "claude": ClaudeAdapter(),
        "codex": CodexAdapter(),
        "gemini": GeminiAdapter(),
        "opencode": OpenCodeAdapter(),
        "qwen": QwenAdapter(),
    }


def get_available_providers() -> List[ProviderId]:
    """Get list of available providers."""
    registry = get_adapter_registry()
    available = []
    for pid, adapter in registry.items():
        if adapter.detect().detected:
            available.append(pid)
    return available


__all__ = [
    "ShimAdapterBase",
    "ClaudeAdapter",
    "CodexAdapter",
    "GeminiAdapter",
    "OpenCodeAdapter",
    "QwenAdapter",
    "get_adapter_registry",
    "get_available_providers",
    "extract_final_text_from_output",
    "extract_token_usage_from_output",
    "normalize_findings_from_text",
    "inspect_contract_output",
]
