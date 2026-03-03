"""Review engine for AOP.

Provides parallel execution across multiple providers with:
- Stall timeout detection
- Cross-provider deduplication
- Token usage statistics
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..adapter import get_adapter_registry, extract_final_text_from_output, extract_token_usage_from_output, normalize_findings_from_text, inspect_contract_output
from ..artifacts import expected_paths, task_artifact_root
from ...config import ReviewPolicy
from ..retry import RetryPolicy
from ..types import ErrorKind, TaskState, NormalizedFinding, Evidence, NormalizeContext
from ..types.contracts import ProviderId, TaskInput, SEVERITY_ORDER


STRICT_JSON_CONTRACT = (
    "Return JSON only. Use this exact shape: "
    '{"findings":[{"finding_id":"<id>","severity":"critical|high|medium|low","category":"bug|security|performance|maintainability|test-gap","title":"<title>",'
    '"evidence":{"file":"<path>","line":null,"symbol":null,"snippet":"<snippet>"},'
    '"recommendation":"<fix>","confidence":0.0,"fingerprint":"<stable-hash>"}]}. '
    'If no findings, return {"findings":[]}.'
)


@dataclass(frozen=True)
class ReviewRequest:
    """Request for a review."""
    repo_root: str
    prompt: str
    providers: List[ProviderId]
    artifact_base: str
    policy: ReviewPolicy
    task_id: Optional[str] = None
    target_paths: Optional[List[str]] = None
    include_token_usage: bool = False
    synthesize: bool = False
    synthesis_provider: Optional[ProviderId] = None


@dataclass(frozen=True)
class ReviewResult:
    """Result of a review."""
    task_id: str
    artifact_root: Optional[str]
    decision: str
    terminal_state: str
    provider_results: Dict[str, Dict[str, object]]
    findings_count: int
    parse_success_count: int
    parse_failure_count: int
    schema_valid_count: int
    dropped_findings_count: int
    findings: List[Dict[str, object]] = field(default_factory=list)
    token_usage_summary: Optional[Dict[str, object]] = None
    synthesis: Optional[Dict[str, object]] = None


def _sha(value: str) -> str:
    """Generate SHA-256 hash of a string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_payload_hash(payload: object) -> str:
    """Generate a stable hash of a payload."""
    serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return _sha(serialized)


def _default_task_id(repo_root: str, prompt: str) -> str:
    """Generate a default task ID."""
    return f"task-{_sha(f'{repo_root}:{prompt}')[:16]}"


def _build_prompt(user_prompt: str, target_paths: List[str]) -> str:
    """Build a prompt with scope information."""
    scope = ", ".join(target_paths) if target_paths else "."
    return f"{user_prompt}\n\nScope: {scope}\n\n{STRICT_JSON_CONTRACT}"


# Use SEVERITY_ORDER from core.types.contracts


def _normalize_for_dedupe(value: str) -> str:
    """Normalize a string for deduplication."""
    return re.sub(r"\s+", " ", value.strip().lower())


def _finding_dedupe_key(item: NormalizedFinding) -> str:
    """Generate a deduplication key for a finding."""
    line_value = str(item.evidence.line) if isinstance(item.evidence.line, int) else ""
    symbol_value = _normalize_for_dedupe(item.evidence.symbol or "")
    return _sha(
        "||".join([
            _normalize_for_dedupe(item.category),
            _normalize_for_dedupe(item.title),
            _normalize_for_dedupe(item.evidence.file.replace("\\", "/")),
            line_value,
            symbol_value,
        ])
    )


def _merge_findings_across_providers(findings: List[NormalizedFinding]) -> List[Dict[str, object]]:
    """Merge findings from multiple providers, deduplicating by fingerprint."""
    merged: Dict[str, Dict[str, object]] = {}
    for item in findings:
        key = _finding_dedupe_key(item)
        existing = merged.get(key)
        if existing is None:
            payload = asdict(item)
            payload["detected_by"] = [item.provider]
            merged[key] = payload
            continue

        detected_by = existing.get("detected_by")
        if not isinstance(detected_by, list):
            detected_by = []
            existing["detected_by"] = detected_by
        if item.provider not in detected_by:
            detected_by.append(item.provider)

        current_confidence = float(existing.get("confidence", 0.0))
        if item.confidence > current_confidence:
            existing["confidence"] = item.confidence

        current_severity = str(existing.get("severity", "low")).lower()
        if SEVERITY_ORDER.get(item.severity, 99) < SEVERITY_ORDER.get(current_severity, 99):
            existing["severity"] = item.severity

    merged_findings = list(merged.values())
    for payload in merged_findings:
        detected_by = payload.get("detected_by")
        if isinstance(detected_by, list):
            payload["detected_by"] = sorted({str(item) for item in detected_by if str(item)})

    def _sort_key(entry: Dict[str, object]) -> Tuple[int, str, int, str]:
        severity = str(entry.get("severity", "low")).lower()
        evidence = entry.get("evidence")
        file_path = ""
        line = 0
        if isinstance(evidence, dict):
            file_path = str(evidence.get("file", ""))
            line_raw = evidence.get("line")
            line = line_raw if isinstance(line_raw, int) else 0
        return (
            SEVERITY_ORDER.get(severity, 99),
            file_path,
            line,
            str(entry.get("title", "")),
        )

    merged_findings.sort(key=_sort_key)
    return merged_findings


def _output_text(stdout_text: str, stderr_text: str) -> str:
    """Get the output text from stdout or stderr."""
    return stdout_text if stdout_text.strip() else stderr_text


def _response_quality(success: bool, output_text: str, final_text: str) -> Tuple[bool, str]:
    """Assess the quality of a response."""
    if not success:
        return (False, "provider_failed")
    if not final_text.strip():
        return (False, "empty_final_text")
    if final_text.strip() == output_text.strip():
        return (True, "raw_text")
    return (True, "extracted_final_text")


def _aggregate_token_usage_summary(provider_results: Dict[str, Dict[str, object]]) -> Dict[str, object]:
    """Aggregate token usage across providers."""
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    provider_count = len(provider_results)
    providers_with_usage = 0

    for details in provider_results.values():
        usage = details.get("token_usage")
        if isinstance(usage, dict):
            providers_with_usage += 1
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = usage.get(key)
                if isinstance(value, int):
                    totals[key] += value

    summary_completeness = "unavailable" if providers_with_usage == 0 else (
        "full" if providers_with_usage == provider_count else "partial"
    )

    return {
        "providers_with_usage": providers_with_usage,
        "provider_count": provider_count,
        "completeness": summary_completeness,
        "totals": totals,
    }


def _read_text(path: Path) -> str:
    """Read text from a file if it exists."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _write_json(path: Path, payload: object) -> None:
    """Write JSON to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    """Write text to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _deserialize_findings(payload: object) -> List[NormalizedFinding]:
    """Deserialize findings from a payload."""
    findings: List[NormalizedFinding] = []
    findings_payload = payload if isinstance(payload, list) else []
    serialized_findings = [item for item in findings_payload if isinstance(item, dict)]

    for item in serialized_findings:
        try:
            evidence_raw = item.get("evidence", {})
            if not isinstance(evidence_raw, dict):
                continue
            evidence = Evidence(
                file=str(evidence_raw.get("file", "")),
                line=evidence_raw.get("line") if isinstance(evidence_raw.get("line"), int) else None,
                snippet=str(evidence_raw.get("snippet", "")),
                symbol=evidence_raw.get("symbol") if isinstance(evidence_raw.get("symbol"), str) else None,
            )
            finding = NormalizedFinding(
                task_id=str(item["task_id"]),
                provider=item["provider"],
                finding_id=str(item["finding_id"]),
                severity=item["severity"],
                category=item["category"],
                title=str(item["title"]),
                evidence=evidence,
                recommendation=str(item.get("recommendation", "")),
                confidence=float(item.get("confidence", 0.0)),
                fingerprint=str(item.get("fingerprint", "")),
                raw_ref=str(item.get("raw_ref", "")),
            )
        except Exception:
            continue
        findings.append(finding)
    return findings


class ReviewEngine:
    """Engine for running code reviews across multiple providers."""

    def __init__(self, providers: Optional[List[ProviderId]] = None, default_timeout: int = 600):
        self.providers = providers or ["claude", "codex"]
        self.default_timeout = default_timeout
        self._registry = get_adapter_registry()

    def _run_single_provider(
        self,
        request: ReviewRequest,
        provider: ProviderId,
        task_id: str,
        artifact_base: str,
        full_prompt: str,
        target_paths: List[str],
    ) -> Dict[str, object]:
        """Run a single provider and return the result."""
        adapter = self._registry.get(provider)
        if adapter is None:
            return {"success": False, "reason": "adapter_not_implemented"}

        presence = adapter.detect()
        if not presence.detected or not presence.auth_ok:
            return {
                "success": False,
                "reason": "provider_unavailable",
                "detected": presence.detected,
                "auth_ok": presence.auth_ok,
            }

        provider_stall_timeout = request.policy.provider_timeouts.get(provider, request.policy.stall_timeout_seconds)
        poll_interval = request.policy.poll_interval_seconds

        try:
            metadata = {
                "artifact_root": artifact_base,
                "allow_paths": request.policy.allow_paths,
            }
            input_task = TaskInput(
                task_id=task_id,
                prompt=full_prompt,
                repo_root=request.repo_root,
                target_paths=target_paths,
                timeout_seconds=provider_stall_timeout,
                metadata=metadata,
            )
            run_ref = adapter.run(input_task)
            started = time.time()
            last_progress_at = started
            status = None

            while True:
                status = adapter.poll(run_ref)
                now = time.time()
                if status.completed:
                    break

                if (now - last_progress_at) > provider_stall_timeout:
                    try:
                        adapter.cancel(run_ref)
                    except Exception:
                        pass
                    return {
                        "success": False,
                        "reason": "stall_timeout",
                        "wall_clock_seconds": round(now - started, 3),
                    }

                time.sleep(poll_interval)

            raw_dir = Path(run_ref.artifact_path) / "raw"
            raw_stdout = _read_text(raw_dir / f"{provider}.stdout.log")
            raw_stderr = _read_text(raw_dir / f"{provider}.stderr.log")

            findings: List[NormalizedFinding] = []
            contract_info = inspect_contract_output(raw_stdout)
            parse_ok = bool(contract_info["parse_ok"])
            schema_valid_count = int(contract_info["schema_valid_count"])
            dropped_count = int(contract_info["dropped_count"])

            success = status.attempt_state == "SUCCEEDED"

            if success:
                findings = adapter.normalize(
                    raw_stdout,
                    NormalizeContext(
                        task_id=task_id,
                        provider=provider,
                        repo_root=request.repo_root,
                        raw_ref=f"raw/{provider}.stdout.log",
                    ),
                )

            output_text = _output_text(raw_stdout, raw_stderr)
            final_text = extract_final_text_from_output(output_text)
            token_usage = extract_token_usage_from_output(output_text) if request.include_token_usage else None

            return {
                "success": success,
                "wall_clock_seconds": round(time.time() - started, 3),
                "output_text": output_text,
                "final_text": final_text,
                "parse_ok": parse_ok,
                "schema_valid_count": schema_valid_count,
                "dropped_count": dropped_count,
                "findings_count": len(findings),
                "findings": [asdict(f) for f in findings],
                "token_usage": token_usage,
            }

        except Exception as e:
            return {
                "success": False,
                "reason": str(e),
                "error_kind": "internal_error",
                "traceback": traceback.format_exc(),
            }

    def review(
        self,
        prompt: str,
        repo_root: str = ".",
        artifact_base: Optional[str] = None,
        target_paths: Optional[List[str]] = None,
        policy: Optional[ReviewPolicy] = None,
        task_id: Optional[str] = None,
        include_token_usage: bool = False,
        synthesize: bool = False,
        synthesis_provider: Optional[ProviderId] = None,
        strict_contract: bool = False,
    ) -> ReviewResult:
        """Run a review across multiple providers."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        policy = policy or ReviewPolicy()
        task_id = task_id or _default_task_id(repo_root, prompt)
        artifact_base = artifact_base or tempfile.mkdtemp(prefix="aop-")
        artifact_root = str(task_artifact_root(artifact_base, task_id))
        Path(artifact_root).mkdir(parents=True, exist_ok=True)

        normalized_targets = target_paths or ["."]
        full_prompt = _build_prompt(prompt, normalized_targets)

        provider_order = sorted(set(self.providers))
        provider_results: Dict[str, Dict[str, object]] = {}
        required_provider_success: Dict[str, bool] = {}
        aggregated_findings: List[NormalizedFinding] = []
        parse_success_count = 0
        parse_failure_count = 0
        schema_valid_count = 0
        dropped_findings_count = 0

        max_workers = max(1, min(len(provider_order), policy.max_provider_parallelism))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._run_single_provider,
                    ReviewRequest(
                        repo_root=repo_root,
                        prompt=prompt,
                        providers=provider_order,
                        artifact_base=artifact_base,
                        policy=policy,
                        task_id=task_id,
                        target_paths=normalized_targets,
                    ),
                    provider,
                    task_id,
                    artifact_base,
                    full_prompt,
                    normalized_targets,
                ): provider
                for provider in provider_order
            }

            for future in as_completed(futures):
                provider = futures[future]
                try:
                    result = future.result()
                    provider_results[provider] = result
                    required_provider_success[provider] = bool(result.get("success"))

                    if result.get("parse_ok"):
                        parse_success_count += 1
                    else:
                        parse_failure_count += 1
                    schema_valid_count += int(result.get("schema_valid_count", 0))
                    dropped_findings_count += int(result.get("dropped_count", 0))

                    findings_payload = result.get("findings", [])
                    if isinstance(findings_payload, list):
                        aggregated_findings.extend(_deserialize_findings(findings_payload))

                except Exception as e:
                    provider_results[provider] = {"success": False, "reason": str(e)}
                    required_provider_success[provider] = False
                    parse_failure_count += 1

        token_usage_summary = _aggregate_token_usage_summary(provider_results) if policy.include_token_usage else None

        # Evaluate terminal state
        successes = sum(1 for ok in required_provider_success.values() if ok)
        if successes == 0:
            terminal_state = TaskState.FAILED
        elif successes == len(required_provider_success):
            terminal_state = TaskState.COMPLETED
        else:
            terminal_state = TaskState.PARTIAL_SUCCESS

        merged_findings = _merge_findings_across_providers(aggregated_findings)

        # Determine decision
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in merged_findings:
            severity = str(finding.get("severity", "")).lower()
            if severity in counts:
                counts[severity] += 1

        if counts["critical"] > 0:
            decision = "FAIL"
        elif counts["high"] >= policy.high_escalation_threshold:
            decision = "ESCALATE"
        elif terminal_state == TaskState.FAILED:
            decision = "FAIL"
        elif terminal_state == TaskState.PARTIAL_SUCCESS:
            decision = "PARTIAL"
        else:
            decision = "PASS"

        # Write artifacts
        root_path = Path(artifact_root)
        _write_json(root_path / "findings.json", merged_findings)
        _write_json(root_path / "run.json", {
            "task_id": task_id,
            "terminal_state": terminal_state.value,
            "decision": decision,
            "provider_results": provider_results,
            "findings_count": len(merged_findings),
        })

        summary = [
            f"# Review Summary ({task_id})",
            "",
            f"- Decision: {decision}",
            f"- Terminal state: {terminal_state.value}",
            f"- Findings: {len(merged_findings)}",
            "",
            "## Severity Counts",
            f"- critical: {counts['critical']}",
            f"- high: {counts['high']}",
            f"- medium: {counts['medium']}",
            f"- low: {counts['low']}",
        ]
        _write_text(root_path / "summary.md", "\n".join(summary))

        return ReviewResult(
            task_id=task_id,
            artifact_root=artifact_root,
            decision=decision,
            terminal_state=terminal_state.value,
            provider_results=provider_results,
            findings_count=len(merged_findings),
            parse_success_count=parse_success_count,
            parse_failure_count=parse_failure_count,
            schema_valid_count=schema_valid_count,
            dropped_findings_count=dropped_findings_count,
            findings=merged_findings,
            token_usage_summary=token_usage_summary,
        )


__all__ = [
    "ReviewPolicy",
    "ReviewRequest",
    "ReviewResult",
    "ReviewEngine",
]


