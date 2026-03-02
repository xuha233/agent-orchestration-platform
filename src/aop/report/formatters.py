"""Output formatters for AOP review results.

Provides multiple output formats for CI/CD integration:
- format_report: Human-readable console report
- format_markdown_pr: GitHub PR comment format
- format_sarif: SARIF 2.1.0 for GitHub Code Scanning

Reference: MCO runtime/formatters.py
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..core.types.contracts import SEVERITY_LEVELS, SEVERITY_ORDER

if TYPE_CHECKING:
    from ..core.engine.review import ReviewResult


# Use SEVERITY_LEVELS and SEVERITY_ORDER from core.types.contracts
_SARIF_LEVEL_BY_SEVERITY = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
}


def _escape_markdown_cell(value: object) -> str:
    """Escape special characters in markdown table cells."""
    text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def _finding_location(finding: Dict[str, object]) -> str:
    """Extract location string from a finding."""
    evidence = finding.get("evidence")
    if not isinstance(evidence, dict):
        return "-"
    file_path = str(evidence.get("file", "")).strip()
    line = evidence.get("line")
    if not file_path:
        return "-"
    if isinstance(line, int) and line > 0:
        return f"{file_path}:{line}"
    return file_path


def format_report(result: "ReviewResult") -> str:
    """Generate human-readable report for console output.
    
    Args:
        result: ReviewResult from ReviewEngine
        
    Returns:
        Formatted text report suitable for console display
    """
    lines: List[str] = [
        "=" * 60,
        "AOP Review Report",
        "=" * 60,
        "",
        f"Task ID: {result.task_id}",
        f"Decision: {result.decision}",
        f"Terminal State: {result.terminal_state}",
        f"Findings: {result.findings_count}",
        f"Parsed Successfully: {result.parse_success_count}/{result.parse_success_count + result.parse_failure_count}",
        "",
    ]
    
    if result.artifact_root:
        lines.append(f"Artifacts: {result.artifact_root}")
        lines.append("")
    
    # Severity breakdown
    counts = {level: 0 for level in SEVERITY_LEVELS}
    for finding in result.findings:
        severity = str(finding.get("severity", "")).lower()
        if severity in counts:
            counts[severity] += 1
    
    lines.append("-" * 40)
    lines.append("Severity Breakdown")
    lines.append("-" * 40)
    for level in SEVERITY_LEVELS:
        indicator = "!" if counts[level] > 0 else " "
        lines.append(f"  [{indicator}] {level.upper()}: {counts[level]}")
    lines.append("")
    
    # Provider results summary
    lines.append("-" * 40)
    lines.append("Provider Results")
    lines.append("-" * 40)
    for provider, details in sorted(result.provider_results.items()):
        success = details.get("success", False)
        status = "OK" if success else "FAILED"
        findings_count = details.get("findings_count", 0)
        lines.append(f"  {provider}: [{status}] {findings_count} findings")
    lines.append("")
    
    # Token usage if available
    if result.token_usage_summary:
        usage = result.token_usage_summary
        totals = usage.get("totals", {})
        lines.append("-" * 40)
        lines.append("Token Usage")
        lines.append("-" * 40)
        lines.append(f"  Prompt tokens: {totals.get('prompt_tokens', 0)}")
        lines.append(f"  Completion tokens: {totals.get('completion_tokens', 0)}")
        lines.append(f"  Total tokens: {totals.get('total_tokens', 0)}")
        lines.append("")
    
    # Top findings
    if result.findings:
        lines.append("-" * 40)
        lines.append("Findings Detail")
        lines.append("-" * 40)
        
        sorted_findings = sorted(
            result.findings,
            key=lambda item: (
                SEVERITY_LEVELS.index(str(item.get("severity", "low")).lower())
                if str(item.get("severity", "low")).lower() in SEVERITY_LEVELS
                else len(SEVERITY_LEVELS),
                _finding_location(item),
                str(item.get("title", "")),
            ),
        )
        
        for finding in sorted_findings:
            severity = str(finding.get("severity", "low")).lower()
            title = str(finding.get("title", "Untitled"))
            category = str(finding.get("category", "-"))
            location = _finding_location(finding)
            recommendation = str(finding.get("recommendation", ""))
            detected_by = finding.get("detected_by", [])
            
            severity_indicator = {"critical": "[!]", "high": "[!]", "medium": "[-]", "low": "[i]"}
            indicator = severity_indicator.get(severity, "[ ]")
            
            lines.append(f"")
            lines.append(f"{indicator} {severity.upper()}: {title}")
            lines.append(f"    Category: {category}")
            lines.append(f"    Location: {location}")
            if detected_by:
                detected_str = ", ".join(str(p) for p in detected_by) if isinstance(detected_by, list) else str(detected_by)
                lines.append(f"    Detected by: {detected_str}")
            if recommendation:
                lines.append(f"    Recommendation: {recommendation}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def format_markdown_pr(result: "ReviewResult") -> str:
    """Generate markdown formatted PR comment.
    
    Args:
        result: ReviewResult from ReviewEngine
        
    Returns:
        Markdown formatted text suitable for GitHub PR comments
    """
    counts = {level: 0 for level in SEVERITY_LEVELS}
    for finding in result.findings:
        severity = str(finding.get("severity", "")).lower()
        if severity in counts:
            counts[severity] += 1
    
    # Header
    lines: List[str] = [
        "## AOP Review Summary",
        "",
        f"- Decision: **{result.decision}**",
        f"- Terminal State: {result.terminal_state}",
        f"- Parsed Successfully: {result.parse_success_count} / failure {result.parse_failure_count}",
        f"- Findings: {result.findings_count}",
        "",
        "### Severity Breakdown",
        "",
        "| Severity | Count |",
        "|---|---:|",
    ]
    
    for level in SEVERITY_LEVELS:
        lines.append(f"| {level} | {counts[level]} |")
    
    lines.append("")
    
    # Provider results
    lines.append("### Provider Results")
    lines.append("")
    lines.append("| Provider | Status | Findings |")
    lines.append("|---|---|---:|")
    
    for provider, details in sorted(result.provider_results.items()):
        success = details.get("success", False)
        status = "OK" if success else "FAILED"
        findings_count = details.get("findings_count", 0)
        lines.append(f"| {provider} | {status} | {findings_count} |")
    
    lines.append("")
    
    # Findings
    lines.append("### Findings")
    lines.append("")
    
    if not result.findings:
        lines.append("_No findings reported._")
        return "\n".join(lines)
    
    lines.extend(
        [
            "| Severity | Category | Title | Location | Confidence | Recommendation |",
            "|---|---|---|---|---:|---|",
        ]
    )
    
    ordered_findings = sorted(
        result.findings,
        key=lambda item: (
            SEVERITY_LEVELS.index(str(item.get("severity", "low")).lower())
            if str(item.get("severity", "low")).lower() in SEVERITY_LEVELS
            else len(SEVERITY_LEVELS),
            _finding_location(item),
            str(item.get("title", "")),
        ),
    )
    
    for finding in ordered_findings:
        confidence_value = finding.get("confidence")
        if isinstance(confidence_value, (int, float)):
            confidence_text = f"{float(confidence_value):.2f}"
        else:
            confidence_text = "-"
        
        lines.append(
            "| "
            + " | ".join(
                [
                    f"{_escape_markdown_cell(str(finding.get('severity', '-')).lower())}",
                    _escape_markdown_cell(finding.get("category", "-")),
                    _escape_markdown_cell(finding.get("title", "-")),
                    f"{_escape_markdown_cell(_finding_location(finding))}",
                    confidence_text,
                    _escape_markdown_cell(finding.get("recommendation", "-")),
                ]
            )
            + " |"
        )
    
    # Token usage if available
    if result.token_usage_summary:
        usage = result.token_usage_summary
        totals = usage.get("totals", {})
        lines.append("")
        lines.append("### Token Usage")
        lines.append("")
        lines.append(f"- Prompt tokens: **{totals.get('prompt_tokens', 0)}**")
        lines.append(f"- Completion tokens: **{totals.get('completion_tokens', 0)}**")
        lines.append(f"- Total tokens: **{totals.get('total_tokens', 0)}**")
        lines.append(f"- Completeness: {usage.get('completeness', 'unknown')}")
    
    lines.append("")
    lines.append(f"_Generated by AOP - Task ID: {result.task_id}_")
    
    return "\n".join(lines)


def _normalize_rule_name(category: str, title: str) -> str:
    """Normalize category and title into a rule name."""
    normalized = re.sub(
        r"[^a-zA-Z0-9]+", "-", f"{category}-{title}".strip().lower()
    ).strip("-")
    return normalized or "finding"


def _rule_id_for_finding(finding: Dict[str, object], prefix: str = "aop") -> str:
    """Generate a stable rule ID for a finding."""
    category = str(finding.get("category", "general")).strip().lower() or "general"
    title = str(finding.get("title", "finding")).strip()
    suffix = hashlib.sha256(f"{category}||{title}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}/{_normalize_rule_name(category, title)}/{suffix}"


def format_sarif(result: "ReviewResult") -> Dict[str, object]:
    """Generate SARIF 2.1.0 format for GitHub Code Scanning.
    
    Args:
        result: ReviewResult from ReviewEngine
        
    Returns:
        SARIF 2.1.0 compliant dictionary
    """
    rules_by_id: Dict[str, Dict[str, object]] = {}
    results: List[Dict[str, object]] = []
    
    for finding in result.findings:
        rule_id = _rule_id_for_finding(finding, prefix="aop")
        title = str(finding.get("title", "Finding")).strip() or "Finding"
        recommendation = str(finding.get("recommendation", "")).strip()
        category = str(finding.get("category", "")).strip().lower()
        severity = str(finding.get("severity", "low")).strip().lower()
        level = _SARIF_LEVEL_BY_SEVERITY.get(severity, "note")
        confidence = finding.get("confidence")
        confidence_value = float(confidence) if isinstance(confidence, (int, float)) else 0.0
        detected_by = finding.get("detected_by")
        
        if isinstance(detected_by, list):
            detected_by_value = [str(item) for item in detected_by if str(item)]
        else:
            provider = finding.get("provider")
            detected_by_value = [str(provider)] if isinstance(provider, str) and provider else []
        
        # Add rule if not exists
        if rule_id not in rules_by_id:
            rule_payload: Dict[str, object] = {
                "id": rule_id,
                "name": _normalize_rule_name(category, title),
                "shortDescription": {"text": title},
                "properties": {"category": category},
            }
            if recommendation:
                rule_payload["help"] = {"text": recommendation}
            rules_by_id[rule_id] = rule_payload
        
        # Build result
        result_payload: Dict[str, object] = {
            "ruleId": rule_id,
            "level": level,
            "message": {"text": title},
            "properties": {
                "category": category,
                "severity": severity,
                "confidence": confidence_value,
                "detected_by": detected_by_value,
                "fingerprint": str(finding.get("fingerprint", "")),
            },
        }
        
        # Add location
        evidence = finding.get("evidence")
        if isinstance(evidence, dict):
            file_path = str(evidence.get("file", "")).strip()
            line = evidence.get("line")
            snippet = str(evidence.get("snippet", "")).strip()
            
            if file_path:
                region: Dict[str, object] = {}
                if isinstance(line, int) and line > 0:
                    region["startLine"] = line
                if snippet:
                    region["snippet"] = {"text": snippet}
                
                location = {
                    "physicalLocation": {
                        "artifactLocation": {"uri": file_path},
                        "region": region,
                    }
                }
                result_payload["locations"] = [location]
        
        results.append(result_payload)
    
    # Build SARIF document
    sarif: Dict[str, object] = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AOP",
                        "informationUri": "https://github.com/xuha233/agent-orchestration-platform",
                        "rules": list(rules_by_id.values()),
                    }
                },
                "properties": {
                    "task_id": result.task_id,
                    "decision": result.decision,
                    "terminal_state": result.terminal_state,
                    "findings_count": result.findings_count,
                    "parse_success_count": result.parse_success_count,
                    "parse_failure_count": result.parse_failure_count,
                },
                "results": results,
            }
        ],
    }
    
    # Add invocation details
    if result.token_usage_summary:
        sarif["runs"][0]["properties"]["token_usage"] = result.token_usage_summary
    
    return sarif


def format_json(result: "ReviewResult") -> Dict[str, Any]:
    """Generate JSON output format.
    
    Args:
        result: ReviewResult from ReviewEngine
        
    Returns:
        JSON-serializable dictionary
    """
    output: Dict[str, Any] = {
        "task_id": result.task_id,
        "decision": result.decision,
        "terminal_state": result.terminal_state,
        "findings_count": result.findings_count,
        "parse_success_count": result.parse_success_count,
        "parse_failure_count": result.parse_failure_count,
        "findings": result.findings,
        "provider_results": {
            provider: {
                "success": details.get("success"),
                "findings_count": details.get("findings_count"),
                "wall_clock_seconds": details.get("wall_clock_seconds"),
            }
            for provider, details in result.provider_results.items()
        },
    }
    
    if result.artifact_root:
        output["artifact_root"] = result.artifact_root
    
    if result.token_usage_summary:
        output["token_usage_summary"] = result.token_usage_summary
    
    if result.synthesis:
        output["synthesis"] = result.synthesis
    
    return output


def format_summary(result: "ReviewResult") -> str:
    """Generate a brief one-line summary.
    
    Args:
        result: ReviewResult from ReviewEngine
        
    Returns:
        Brief summary string
    """
    counts = {level: 0 for level in SEVERITY_LEVELS}
    for finding in result.findings:
        severity = str(finding.get("severity", "")).lower()
        if severity in counts:
            counts[severity] += 1
    
    severity_parts = []
    for level in SEVERITY_LEVELS:
        if counts[level] > 0:
            severity_parts.append(f"{counts[level]} {level}")
    
    severity_summary = ", ".join(severity_parts) if severity_parts else "no findings"
    
    return f"AOP: {result.decision} | {severity_summary} | Task: {result.task_id}"


__all__ = [
    "format_report",
    "format_markdown_pr",
    "format_sarif",
    "format_json",
    "format_summary",
]

