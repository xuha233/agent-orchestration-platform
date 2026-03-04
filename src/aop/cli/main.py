"""AOP CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.engine import ExecutionEngine, ReviewEngine
from ..workflow.hypothesis import HypothesisManager
from ..workflow.learning import LearningLog
from ..workflow.team import TeamOrchestrator
from ..config import AOPConfig, ReviewPolicy, load_config
from ..report import format_report, format_markdown_pr, format_sarif, format_json, format_summary

console = Console()

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_CONFIG_NOT_FOUND = 2
EXIT_PROVIDER_UNAVAILABLE = 3
EXIT_INCONCLUSIVE = 3

# Default policy for CLI defaults
DEFAULT_POLICY = ReviewPolicy()


def _get_default_providers() -> str:
    """Get default providers from config or fallback."""
    config = load_config()
    return ",".join(config.providers)


def _parse_providers(raw: str) -> List[str]:
    """Parse comma-separated providers list."""
    seen = set()
    providers: List[str] = []
    for item in raw.split(","):
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        providers.append(value)
    return providers


def _parse_provider_timeouts(raw: str) -> Dict[str, int]:
    """Parse provider-specific timeouts from CLI argument.
    
    Format: "claude=120,codex=90"
    """
    result: Dict[str, int] = {}
    if not raw.strip():
        return result
    for chunk in raw.split(","):
        pair = chunk.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(f"invalid provider timeout entry: {pair}")
        provider, timeout_text = pair.split("=", 1)
        provider_name = provider.strip()
        if not provider_name:
            raise ValueError(f"invalid provider timeout entry: {pair}")
        try:
            timeout = int(timeout_text.strip())
        except Exception:
            raise ValueError(f"invalid timeout value for provider '{provider_name}': {timeout_text.strip()}") from None
        if timeout <= 0:
            raise ValueError(f"timeout must be > 0 for provider '{provider_name}'")
        result[provider_name] = timeout
    return result


def _parse_paths(raw: str) -> List[str]:
    """Parse comma-separated paths."""
    paths = [item.strip() for item in raw.split(",") if item.strip()]
    return paths if paths else ["."]


def _parse_provider_permissions_json(raw: str) -> Dict[str, Dict[str, str]]:
    """Parse provider permissions from JSON string."""
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        raise ValueError("--provider-permissions-json must be valid JSON") from None
    if not isinstance(payload, dict):
        raise ValueError("--provider-permissions-json root must be an object")

    result: Dict[str, Dict[str, str]] = {}
    for provider, permissions in payload.items():
        provider_name = str(provider).strip()
        if not provider_name:
            raise ValueError("--provider-permissions-json contains empty provider name")
        if not isinstance(permissions, dict):
            raise ValueError(f"permissions for provider '{provider_name}' must be an object")
        normalized: Dict[str, str] = {}
        for key, value in permissions.items():
            key_name = str(key).strip()
            if not key_name:
                raise ValueError(f"provider '{provider_name}' contains empty permission key")
            normalized[key_name] = str(value)
        result[provider_name] = normalized
    return result


def _merge_provider_permissions(
    base: Dict[str, Dict[str, str]],
    override: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    """Merge base and override provider permissions."""
    merged: Dict[str, Dict[str, str]] = {provider: dict(values) for provider, values in base.items()}
    for provider, permissions in override.items():
        current = merged.get(provider, {})
        current.update(permissions)
        merged[provider] = current
    return merged


def _resolve_policy(
    config: AOPConfig,
    stall_timeout: int,
    review_hard_timeout: int,
    poll_interval: float,
    provider_timeouts: str,
    allow_paths: str,
    enforcement_mode: str,
    strict_contract: bool,
    max_provider_parallelism: int,
    provider_permissions_json: str,
) -> ReviewPolicy:
    """Resolve ReviewPolicy from config and CLI overrides."""
    # Parse CLI overrides
    parsed_provider_timeouts = dict(config.policy.provider_timeouts)
    parsed_provider_timeouts.update(_parse_provider_timeouts(provider_timeouts))
    
    parsed_allow_paths = _parse_paths(allow_paths) if allow_paths else list(config.policy.allow_paths)
    
    parsed_provider_permissions = _merge_provider_permissions(
        config.policy.provider_permissions,
        _parse_provider_permissions_json(provider_permissions_json),
    )
    
    # Resolve values (CLI takes precedence)
    final_stall_timeout = stall_timeout if stall_timeout > 0 else config.policy.stall_timeout_seconds
    final_hard_timeout = review_hard_timeout if review_hard_timeout >= 0 else config.policy.review_hard_timeout_seconds
    final_poll_interval = poll_interval if poll_interval > 0 else config.policy.poll_interval_seconds
    final_max_parallelism = max_provider_parallelism if max_provider_parallelism >= 0 else config.policy.max_provider_parallelism
    final_enforcement_mode = enforcement_mode or config.policy.enforcement_mode
    
    return ReviewPolicy(
        timeout_seconds=config.policy.timeout_seconds,
        stall_timeout_seconds=final_stall_timeout,
        poll_interval_seconds=final_poll_interval,
        review_hard_timeout_seconds=final_hard_timeout,
        enforce_findings_contract=strict_contract or config.policy.enforce_findings_contract,
        max_retries=config.policy.max_retries,
        high_escalation_threshold=config.policy.high_escalation_threshold,
        require_non_empty_findings=config.policy.require_non_empty_findings,
        max_provider_parallelism=final_max_parallelism,
        provider_timeouts=parsed_provider_timeouts,
        allow_paths=parsed_allow_paths,
        provider_permissions=parsed_provider_permissions,
        enforcement_mode=final_enforcement_mode,
    )


def _show_next_steps():
    """Show next steps after init."""
    steps = """
[bold cyan]Next Steps:[/bold cyan]

  1. Edit [green].aop.yaml[/green] to configure your providers and settings
  2. Add your hypotheses to [green]hypotheses.md[/green]
  3. Run [blue]aop doctor[/blue] to check provider availability
  4. Run [blue]aop review -p "your prompt"[/blue] to start a review

[dim]Documentation: https://github.com/your-org/aop[/dim]
"""
    console.print(steps)


@click.group()
@click.version_option(version="0.1.0", prog_name="aop")
def cli():
    """Agent Orchestration Platform.
    
    A unified platform for multi-agent code review and analysis.
    """
    pass


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--fix", "show_fix", is_flag=True, help="Show fix suggestions for issues")
def doctor(json_output: bool, show_fix: bool):
    """Check provider availability and configuration.
    
    \b
    Exit Codes:
      0 - All providers available
      1 - Some providers unavailable
      3 - No providers available
    """
    engine = ExecutionEngine()
    results = engine.detect_providers()
    
    # Get provider details (version, auth status)
    provider_info = {}
    from ..core.adapter import get_adapter_registry
    registry = get_adapter_registry()
    
    for pid, presence in results.items():
        adapter = registry.get(pid)
        info = {
            "detected": presence.detected,
            "version": None,
            "auth_status": None,
            "fix_suggestion": None
        }
        
        if adapter and hasattr(adapter, "get_info"):
            try:
                adapter_info = adapter.get_info()
                info["version"] = adapter_info.get("version")
                info["auth_status"] = adapter_info.get("auth_status")
            except Exception:
                pass
        
        if not presence.detected:
            info["fix_suggestion"] = f"Install or configure {pid} provider"
            if pid == "claude":
                info["fix_suggestion"] = "Run 'claude auth' or set ANTHROPIC_API_KEY"
            elif pid == "codex":
                info["fix_suggestion"] = "Run 'codex auth' or set OPENAI_API_KEY"
        
        provider_info[pid] = info
    
    if json_output:
        output = {
            "providers": provider_info,
            "all_available": all(p["detected"] for p in provider_info.values()),
            "available_count": sum(1 for p in provider_info.values() if p["detected"]),
            "total_count": len(provider_info)
        }
        console.print_json(data=output)
        return
    
    table = Table(title="Provider Status")
    table.add_column("Provider")
    table.add_column("Status")
    table.add_column("Version")
    table.add_column("Auth")
    
    for pid, info in provider_info.items():
        status = "[green]Available[/green]" if info["detected"] else "[red]Not found[/red]"
        version = info["version"] or "-"
        auth = info["auth_status"] or ("[green]OK[/green]" if info["detected"] else "-")
        table.add_row(pid, status, version, auth)
    
    console.print(table)
    
    # Show fix suggestions if requested
    if show_fix:
        issues = [(pid, info) for pid, info in provider_info.items() if not info["detected"]]
        if issues:
            console.print("\n[bold yellow]Fix Suggestions:[/bold yellow]")
            for pid, info in issues:
                if info["fix_suggestion"]:
                    console.print(f"  * {pid}: {info['fix_suggestion']}")
    
    # Return appropriate exit code
    available_count = sum(1 for p in provider_info.values() if p["detected"])
    if available_count == 0:
        sys.exit(EXIT_PROVIDER_UNAVAILABLE)
    elif available_count < len(provider_info):
        sys.exit(EXIT_ERROR)


# Common review/run options (shared between review and run commands)
def _add_common_execution_options(f):
    """Add common execution options to a command."""
    # Execution Scope
    f = click.option("--prompt", "-p", required=True, 
                     help="The prompt/question for multi-agent review")(f)
    f = click.option("--providers", "-P", default=None,
                     help="Comma-separated provider list. Default: claude,codex (from config)")(f)
    f = click.option("--repo", "-r", default=".",
                     help="Repository root path. Default: current directory")(f)
    f = click.option("--target-paths", default=".",
                     help="Comma-separated task scope paths (default: .)")(f)
    f = click.option("--task-id", default="",
                     help="Optional stable task id")(f)
    
    # Timeout and Parallelism
    f = click.option("--timeout", "-t", default=600,
                     help="Timeout in seconds for each provider. Default: 600")(f)
    f = click.option("--stall-timeout", type=int, default=DEFAULT_POLICY.stall_timeout_seconds,
                     help="Cancel a provider when output progress is idle for N seconds (default: 900)")(f)
    f = click.option("--review-hard-timeout", type=int, default=DEFAULT_POLICY.review_hard_timeout_seconds,
                     help="Review-mode hard deadline in seconds, 0 disables (default: 1800)")(f)
    f = click.option("--poll-interval", type=float, default=DEFAULT_POLICY.poll_interval_seconds,
                     help="Provider status polling interval in seconds (default: 1.0)")(f)
    f = click.option("--max-provider-parallelism", type=int, default=DEFAULT_POLICY.max_provider_parallelism,
                     help="Provider fan-out concurrency. 0 means full parallelism (default: 0)")(f)
    f = click.option("--provider-timeouts", default="",
                     help="Provider-specific stall-timeout overrides, e.g. claude=120,codex=90")(f)
    
    # Output
    f = click.option("--format", "-f", "output_format", default="report",
                     type=click.Choice(["report", "json", "summary", "sarif", "markdown-pr"]),
                     help="Output format. Default: report. sarif/markdown-pr are review-only")(f)
    f = click.option("--result-mode", type=click.Choice(["stdout", "artifact", "both"]),
                     default="stdout",
                     help="artifact: write files, stdout: print payload, both: do both (default: stdout)")(f)
    f = click.option("--artifact-base", default="reports/review",
                     help="Artifact base directory (default: reports/review)")(f)
    f = click.option("--include-token-usage", is_flag=True,
                     help="Best-effort token usage extraction (provider and aggregate)")(f)
    f = click.option("--save-artifacts", is_flag=True,
                     help="Force artifact writes when result-mode is stdout")(f)
    f = click.option("--json", "json_output", is_flag=True,
                     help="Print machine-readable JSON output")(f)
    
    # Synthesis
    f = click.option("--synthesize", is_flag=True,
                     help="Run one extra synthesis pass to produce consensus/divergence summary")(f)
    f = click.option("--synth-provider", default="",
                     help="Provider to run synthesis pass (must be in --providers). Defaults to claude when available")(f)
    
    # Access and Contracts
    f = click.option("--allow-paths", default=".",
                     help="Comma-separated allowed paths under repo root (default: .)")(f)
    f = click.option("--enforcement-mode", type=click.Choice(["strict", "best_effort"]),
                     default=DEFAULT_POLICY.enforcement_mode,
                     help="strict fails closed when permission requirements are unmet (default: strict)")(f)
    f = click.option("--provider-permissions-json", default="",
                     help="Provider permission mapping JSON, e.g. '{\"codex\":{\"sandbox\":\"workspace-write\"}}'")(f)
    f = click.option("--strict-contract", is_flag=True,
                     help="Review mode only: enforce strict findings JSON contract")(f)
    
    return f


@cli.command()
@_add_common_execution_options
def review(
    prompt: str,
    providers: Optional[str],
    repo: str,
    target_paths: str,
    task_id: str,
    timeout: int,
    stall_timeout: int,
    review_hard_timeout: int,
    poll_interval: float,
    max_provider_parallelism: int,
    provider_timeouts: str,
    output_format: str,
    result_mode: str,
    artifact_base: str,
    include_token_usage: bool,
    save_artifacts: bool,
    json_output: bool,
    synthesize: bool,
    synth_provider: str,
    allow_paths: str,
    enforcement_mode: str,
    provider_permissions_json: str,
    strict_contract: bool,
):
    """Run multi-agent code review.
    
    \b
    Examples:
      aop review -p "Review the authentication module"
      aop review -p "Check for security issues" -P claude,gemini
      aop review -p "Analyze performance" -f json
      aop review -p "Review for bugs" --synthesize --synth-provider claude
      aop review -p "Review for bugs" --format sarif --result-mode artifact
      aop review -p "Review runtime/" --target-paths runtime --strict-contract
    
    \b
    Exit Codes:
      0 - Review completed successfully (PASS)
      1 - Review failed (FAIL)
      3 - Review inconclusive (INCONCLUSIVE, review mode only)
    """
    # Load config and merge with CLI options
    config = load_config()
    provider_list = _parse_providers(providers or ",".join(config.providers))
    
    # Resolve policy from config and CLI overrides
    policy = _resolve_policy(
        config=config,
        stall_timeout=stall_timeout,
        review_hard_timeout=review_hard_timeout,
        poll_interval=poll_interval,
        provider_timeouts=provider_timeouts,
        allow_paths=allow_paths,
        enforcement_mode=enforcement_mode,
        strict_contract=strict_contract,
        max_provider_parallelism=max_provider_parallelism,
        provider_permissions_json=provider_permissions_json,
    )
    
    # Validate synthesis provider
    synth_provider_name = synth_provider.strip() if synth_provider else ""
    do_synthesize = bool(synthesize or synth_provider_name)
    if synth_provider_name and synth_provider_name not in provider_list:
        console.print("[red]Error: --synth-provider must be one of selected providers[/red]")
        sys.exit(EXIT_ERROR)
    
    console.print(Panel(f"[bold]Running review with:[/] {', '.join(provider_list)}"))
    
    engine = ReviewEngine(
        providers=provider_list, 
        default_timeout=timeout,
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing...", total=None)
        result = engine.review(
            prompt, 
            repo_root=repo,
            target_paths=_parse_paths(target_paths),
            task_id=task_id or None,
            include_token_usage=include_token_usage,
            synthesize=do_synthesize,
            synthesis_provider=synth_provider_name or None,
            strict_contract=strict_contract,
        )
        progress.update(task, description="Complete")
    
    # Determine effective result mode
    effective_result_mode = result_mode
    if save_artifacts and effective_result_mode == "stdout":
        effective_result_mode = "both"
    
    # Summary by severity
    if result.findings:
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in result.findings:
            sev = f.get("severity", "low") if isinstance(f, dict) else f.severity
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        console.print("\n[bold]Findings Summary:[/bold]")
        for sev in ["critical", "high", "medium", "low"]:
            count = severity_counts.get(sev, 0)
            color = {"critical": "red", "high": "yellow", "medium": "blue", "low": "dim"}[sev]
            console.print(f"  [{color}]{sev.upper()}: {count}[/{color}]")
    
    # Top findings
    if result.findings:
        sorted_findings = sorted(result.findings, 
                                 key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.get("severity", "low") if isinstance(f, dict) else f.severity, 4))
        console.print("\n[bold]Top Findings:[/bold]")
        for i, f in enumerate(sorted_findings[:5], 1):
            sev = f.get("severity", "low") if isinstance(f, dict) else f.severity
            title = f.get("title", "") if isinstance(f, dict) else f.title
            evidence = f.get("evidence", {}) if isinstance(f, dict) else f.evidence
            file_path = evidence.get("file", "") if isinstance(evidence, dict) else evidence.file
            line = evidence.get("line") if isinstance(evidence, dict) else evidence.line
            color = {"critical": "red", "high": "yellow", "medium": "blue", "low": "dim"}[sev]
            console.print(f"  {i}. [{color}][{sev.upper()}][/{color}] {title}")
            console.print(f"     [dim]{file_path}:{line or '-'}[/dim]")
    
    # Output based on format
    if output_format == "json" or json_output:
        # Determine success based on decision
        is_success = result.decision == "PASS"
        output = {
            "command": "review",
            "task_id": result.task_id,
            "decision": result.decision,
            "terminal_state": result.terminal_state,
            "success": is_success,
            "findings_count": result.findings_count,
            "result_mode": effective_result_mode,
            "artifact_root": result.artifact_root,
            "findings": result.findings,
        }
        if result.token_usage_summary is not None:
            output["token_usage_summary"] = result.token_usage_summary
        if result.synthesis is not None:
            output["synthesis"] = result.synthesis
        console.print_json(data=output)
    elif output_format == "summary":
        console.print(format_summary(result))
    elif output_format == "sarif":
        # SARIF output for GitHub Code Scanning
        sarif_output = _format_sarif(result)
        console.print_json(data=sarif_output)
    elif output_format == "markdown-pr":
        # Markdown PR comment format
        md_output = _format_markdown_pr(result)
        console.print(md_output)
    elif output_format == "report":
        # Use the new report formatter for report format
        console.print(format_report(result))
    else:
        # Default report format
        console.print(format_report(result))
    
    # Exit codes based on decision
    if result.decision == "FAIL":
        sys.exit(EXIT_ERROR)
    if result.decision == "INCONCLUSIVE":
        sys.exit(EXIT_INCONCLUSIVE)
    sys.exit(EXIT_SUCCESS)


@cli.command("run")
@_add_common_execution_options
def run_command(
    prompt: str,
    providers: Optional[str],
    repo: str,
    target_paths: str,
    task_id: str,
    timeout: int,
    stall_timeout: int,
    review_hard_timeout: int,
    poll_interval: float,
    max_provider_parallelism: int,
    provider_timeouts: str,
    output_format: str,
    result_mode: str,
    artifact_base: str,
    include_token_usage: bool,
    save_artifacts: bool,
    json_output: bool,
    synthesize: bool,
    synth_provider: str,
    allow_paths: str,
    enforcement_mode: str,
    provider_permissions_json: str,
    strict_contract: bool,
):
    """Run general multi-provider task execution.
    
    Unlike 'review', this command does not enforce findings schema.
    
    \b
    Examples:
      aop run -p "Summarize the architecture"
      aop run -p "List risky files" -P claude,codex --json
      aop run -p "Compare provider outputs" -P claude,codex,qwen --synthesize
      aop run -p "Analyze runtime" --save-artifacts --json
    
    \b
    Exit Codes:
      0 - Success
      1 - Failed
      2 - Input/config/runtime failure
    """
    # Load config and merge with CLI options
    config = load_config()
    provider_list = _parse_providers(providers or ",".join(config.providers))
    
    # Resolve policy from config and CLI overrides
    policy = _resolve_policy(
        config=config,
        stall_timeout=stall_timeout,
        review_hard_timeout=review_hard_timeout,
        poll_interval=poll_interval,
        provider_timeouts=provider_timeouts,
        allow_paths=allow_paths,
        enforcement_mode=enforcement_mode,
        strict_contract=False,  # run mode doesn't enforce contract
        max_provider_parallelism=max_provider_parallelism,
        provider_permissions_json=provider_permissions_json,
    )
    
    # Validate synthesis provider
    synth_provider_name = synth_provider.strip() if synth_provider else ""
    do_synthesize = bool(synthesize or synth_provider_name)
    if synth_provider_name and synth_provider_name not in provider_list:
        console.print("[red]Error: --synth-provider must be one of selected providers[/red]")
        sys.exit(EXIT_ERROR)
    
    # Validate format
    if output_format in ("sarif", "markdown-pr"):
        console.print(f"[red]Error: --format {output_format} is supported only for review command[/red]")
        sys.exit(EXIT_ERROR)
    
    console.print(Panel(f"[bold]Running task with:[/] {', '.join(provider_list)}"))
    
    engine = ExecutionEngine(
        providers=provider_list,
        default_timeout=timeout,
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing...", total=None)
        result = engine.run(
            prompt,
            repo_root=repo,
            target_paths=_parse_paths(target_paths),
            task_id=task_id or None,
            include_token_usage=include_token_usage,
            synthesize=do_synthesize,
            synthesis_provider=synth_provider_name or None,
        )
        progress.update(task, description="Complete")
    
    # Determine effective result mode
    effective_result_mode = result_mode
    if save_artifacts and effective_result_mode == "stdout":
        effective_result_mode = "both"
    
    # Output
    if output_format == "json" or json_output:
        output = {
            "command": "run",
            "task_id": result.task_id,
            "decision": result.decision,
            "terminal_state": result.terminal_state,
            "success": result.success,
            "duration_seconds": result.duration_seconds,
            "result_mode": effective_result_mode,
            "artifact_root": str(Path(artifact_base) / result.task_id) if effective_result_mode in ("artifact", "both") else None,
            "provider_results": result.provider_results,
            "errors": result.errors
        }
        if result.token_usage_summary is not None:
            output["token_usage_summary"] = result.token_usage_summary
        if result.synthesis is not None:
            output["synthesis"] = result.synthesis
        console.print_json(data=output)
    elif output_format == "summary":
        console.print(f"\n[bold]Task:[/] {result.task_id}")
        console.print(f"[bold]Duration:[/] {result.duration_seconds:.2f}s")
        console.print(f"[bold]Status:[/] {'[green]Success[/green]' if result.success else '[red]Failed[/red]'}")
    else:
        console.print(f"\n[bold]Task:[/] {result.task_id}")
        console.print(f"[bold]Duration:[/] {result.duration_seconds:.2f}s")
        console.print(f"[bold]Status:[/] {'[green]Success[/green]' if result.success else '[red]Failed[/red]'}")
        
        # Show provider outputs in report mode
        if result.provider_results:
            console.print("\n[bold]Provider Results:[/bold]")
            for provider, details in sorted(result.provider_results.items()):
                success = details.get("success", False)
                status = "[green]Success[/green]" if success else "[red]Failed[/red]"
                console.print(f"  {provider}: {status}")
    
    if result.errors:
        console.print("\n[yellow]Warnings:[/yellow]")
        for err in result.errors:
            console.print(f"  * {err}")
    
    sys.exit(EXIT_SUCCESS if result.success else EXIT_ERROR)


def _format_decision(decision: str) -> str:
    """Format decision for display."""
    colors = {
        "PASS": "green",
        "FAIL": "red",
        "ESCALATE": "yellow",
        "PARTIAL": "yellow",
        "INCONCLUSIVE": "dim",
    }
    color = colors.get(decision, "white")
    return f"[{color}]{decision}[/{color}]"


def _format_sarif(result) -> dict:
    """Format result as SARIF 2.1.0 for GitHub Code Scanning."""
    # Use the imported formatter - result is ReviewResult with findings attribute
    return format_sarif(result)



def _format_markdown_pr(result) -> str:
    """Format result as Markdown PR comment."""
    # Use the imported formatter - result is ReviewResult with findings attribute
    return format_markdown_pr(result)


@cli.command()
@click.option("--name", "-n", help="Project name")
@click.option("--providers", "-P", help="Comma-separated providers (default: claude,codex)")
@click.option("--project-type", "-t", type=click.Choice(["exploratory", "optimization", "transformation", "compliance_sensitive"]),
              default="transformation", help="Project type. Default: transformation")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
def init(name: Optional[str], providers: Optional[str], project_type: str, force: bool):
    """Initialize a new AOP project with config file.
    
    Creates:
      - .aop.yaml configuration file
      - runs/ directory for outputs
      - hypotheses.md template
    
    \b
    Examples:
      aop init --name myproject
      aop init -n myproject -P claude,gemini -t exploratory
      aop init  # Interactive mode
    
    \b
    Exit Codes:
      0 - Project initialized successfully
      1 - Configuration file already exists (use --force to overwrite)
      2 - Failed to create project
    """
    config_path = Path(".aop.yaml")
    
    # Check if config exists
    if config_path.exists() and not force:
        console.print("[red]Error: .aop.yaml already exists. Use --force to overwrite.[/red]")
        sys.exit(EXIT_ERROR)
    
    # Interactive prompts if not provided
    if not name:
        name = click.prompt("Project name", default=Path.cwd().name)
    
    provider_list = None
    if not providers:
        providers_input = click.prompt("Providers (comma-separated)", default="claude,codex")
        provider_list = [p.strip() for p in providers_input.split(",")]
    else:
        provider_list = [p.strip() for p in providers.split(",")]
    
    # Create config
    config = AOPConfig(
        project_type=project_type,
        providers=provider_list
    )
    
    try:
        # Save config
        config.to_yaml(config_path)
        console.print(f"[green]Created {config_path}[/green]")
        
        # Create runs directory
        runs_dir = Path("runs")
        runs_dir.mkdir(exist_ok=True)
        console.print(f"[green]Created {runs_dir}/ directory[/green]")
        
        # Create hypotheses template
        hypotheses_path = Path("hypotheses.md")
        if not hypotheses_path.exists() or force:
            hypotheses_content = f"""# Hypotheses - {name}

This file tracks your project hypotheses and their validation status.

## Format

- **ID**: H-001, H-002, ...
- **Statement**: What you're testing
- **Validation**: How you'll test it
- **Status**: pending | validating | validated | falsified

## Quick Wins (H-001 - H-010)

| ID | Statement | Validation | Status |
|----|-----------|------------|--------|
| H-001 | Example: Adding a cache layer improves response time | Benchmark before/after | pending |

## Deep Dives (H-011+)

| ID | Statement | Validation | Status |
|----|-----------|------------|--------|
| | | | |

---

Run `aop hypothesis create "your statement"` to add new hypotheses.
"""
            hypotheses_path.write_text(hypotheses_content, encoding="utf-8")
            console.print(f"[green]Created {hypotheses_path} template[/green]")
        
        # Show success and next steps
        console.print(f"\n[bold green]Project '{name}' initialized![/bold green]")
        _show_next_steps()
        
        sys.exit(EXIT_SUCCESS)
        
    except Exception as e:
        console.print(f"[red]Failed to initialize project: {e}[/red]")
        sys.exit(EXIT_CONFIG_NOT_FOUND)


@cli.group()
def hypothesis():
    """Manage hypotheses.
    
    \b
    Commands:
      create  Create a new hypothesis
      list    List all hypotheses
      update  Update hypothesis status
    
    \b
    Examples:
      aop hypothesis create "Adding cache improves performance"
    """
    pass


@hypothesis.command("create")
@click.argument("statement")
@click.option("--priority", "-p", type=click.Choice(["quick_win", "deep_dive"]),
              default="quick_win", help="Hypothesis priority. Default: quick_win")
def create_hypothesis(statement: str, priority: str):
    """Create a hypothesis.
    
    \b
    Examples:
      aop hypothesis create "Adding cache improves performance"
      aop hypothesis create "Refactoring reduces bugs" -p deep_dive
    
    \b
    Exit Codes:
      0 - Hypothesis created successfully
      1 - Failed to create hypothesis
    """
    # 持久化到 .aop/hypotheses.json
    aop_dir = Path.cwd() / ".aop"
    aop_dir.mkdir(exist_ok=True)
    storage_path = aop_dir / "hypotheses.json"
    
    manager = HypothesisManager(storage_path=storage_path)
    h = manager.create(statement, priority=priority)
    manager.save()
    
    console.print(f"[green]Created {h.hypothesis_id}[/green]")
    console.print(f"  Statement: {statement}")
    console.print(f"  Priority: {priority}")
    console.print(f"  Saved to: {storage_path}")



@hypothesis.command("list")
@click.option("--state", "-s", type=click.Choice(["pending", "validated", "refuted", "inconclusive"]),
              default=None, help="Filter by state. Default: all")
def list_hypotheses(state):
    """List all hypotheses."""
    from ..core.types import HypothesisState
    default_path = Path.cwd() / ".aop" / "hypotheses.json"
    manager = HypothesisManager(storage_path=default_path) if default_path.exists() else HypothesisManager()
    state_filter = HypothesisState(state) if state else None
    hypotheses = manager.list_by_state(state_filter)
    if not hypotheses:
        console.print("[yellow]No hypotheses found[/yellow]")
        return
    table = Table(title="Hypotheses")
    table.add_column("ID", style="cyan")
    table.add_column("Statement", style="white")
    table.add_column("Priority", style="magenta")
    table.add_column("State", style="green")
    state_colors = {"pending": "yellow", "validated": "green", "refuted": "red", "inconclusive": "dim"}
    for h in hypotheses:
        state_str = h.state.value if isinstance(h.state, HypothesisState) else str(h.state)
        state_color = state_colors.get(state_str, "white")
        stmt = h.statement[:50] + "..." if len(h.statement) > 50 else h.statement
        table.add_row(h.hypothesis_id, stmt, h.priority, f"[{state_color}]{state_str}[/{state_color}]")
    console.print(table)

@hypothesis.command("update")
@click.argument("hypothesis_id")
@click.option("--state", "-s", type=click.Choice(["pending", "validated", "refuted", "inconclusive"]),
              required=True, help="New state for the hypothesis")
def update_hypothesis(hypothesis_id, state):
    """Update hypothesis status."""
    from ..core.types import HypothesisState
    default_path = Path.cwd() / ".aop" / "hypotheses.json"
    manager = HypothesisManager(storage_path=default_path) if default_path.exists() else HypothesisManager()
    
    # 加载已有假设
    if default_path.exists():
        manager.load()
    new_state = HypothesisState(state)
    h = manager.update_state(hypothesis_id, new_state)
    if not h:
        console.print(f"[red]Hypothesis {hypothesis_id} not found[/red]")
        raise SystemExit(1)
    if manager._persistence:
        manager.save()
    console.print(f"[green]Updated {hypothesis_id}[/green]")
    console.print(f"  New state: {state}")



@cli.group()
def learning():
    """Capture and manage learnings."""
    pass


@learning.command("capture")
@click.option("--phase", "-p", required=True, help="Phase name")
@click.option("--worked", "-w", multiple=True, help="What worked")
@click.option("--failed", "-f", multiple=True, help="What failed")
@click.option("--insight", "-i", multiple=True, help="Key insight")
def capture_learning(phase, worked, failed, insight):
    """Capture learning from a phase."""
    default_path = Path.cwd() / ".aop" / "learning.json"
    log = LearningLog(storage_path=default_path) if default_path.exists() else LearningLog(storage_path=default_path)
    
    log.capture(
        phase=phase,
        what_worked=list(worked),
        what_failed=list(failed),
        insights=list(insight)
    )
    log.save()
    
    console.print(f"[green]Captured learning from phase: {phase}[/green]")
    if worked:
        console.print(f"  What worked: {len(worked)} items")
    if failed:
        console.print(f"  What failed: {len(failed)} items")
    if insight:
        console.print(f"  Insights: {len(insight)} items")


@learning.command("list")
def list_learnings():
    """List all captured learnings."""
    default_path = Path.cwd() / ".aop" / "learning.json"
    if not default_path.exists():
        console.print("[yellow]No learnings captured yet[/yellow]")
        return
    
    log = LearningLog(storage_path=default_path)
    log.load()
    
    if not log.learnings:
        console.print("[yellow]No learnings found[/yellow]")
        return
    
    table = Table(title="Captured Learnings")
    table.add_column("Phase", style="cyan")
    table.add_column("Worked", style="green")
    table.add_column("Failed", style="red")
    table.add_column("Insights", style="yellow")
    
    for l in log.learnings:
        table.add_row(
            l.phase,
            str(len(l.what_worked)),
            str(len(l.what_failed)),
            str(len(l.insights))
        )
    
    console.print(table)


@learning.command("export")
@click.option("--output", "-o", default="LESSONS_LEARNED.md", help="Output file path")
def export_learnings(output):
    """Export lessons learned to markdown."""
    default_path = Path.cwd() / ".aop" / "learning.json"
    if not default_path.exists():
        console.print("[yellow]No learnings to export[/yellow]")
        raise SystemExit(1)
    
    log = LearningLog(storage_path=default_path)
    log.load()
    
    output_path = Path(output)
    log.export_lessons(output_path)
    
    console.print(f"[green]Exported lessons to: {output_path}[/green]")


@cli.group()
def project():
    """Project management.
    
    \b
    Commands:
      assess  Assess project complexity and get team configuration
    
    \b
    Examples:
      aop project assess -p high -d medium -t low -b medium
    """
    pass


@project.command("assess")
@click.option("--problem-clarity", "-p", default="medium",
              type=click.Choice(["low", "medium", "high"]),
              help="Problem clarity level. Default: medium")
@click.option("--data-availability", "-d", default="medium",
              type=click.Choice(["low", "medium", "high"]),
              help="Data availability level. Default: medium")
@click.option("--tech-novelty", "-t", default="medium",
              type=click.Choice(["low", "medium", "high"]),
              help="Technical novelty level. Default: medium")
@click.option("--business-risk", "-b", default="medium",
              type=click.Choice(["low", "medium", "high"]),
              help="Business risk level. Default: medium")
def assess(problem_clarity: str, data_availability: str, tech_novelty: str, business_risk: str):
    """Assess project complexity.
    
    \b
    Examples:
      aop project assess -p high -d medium -t low -b medium
      aop project assess --problem-clarity high --tech-novelty high
    
    \b
    Exit Codes:
      0 - Assessment completed
    """
    orchestrator = TeamOrchestrator()
    orchestrator.assess_project(problem_clarity, data_availability, tech_novelty, business_risk)
    config = orchestrator.get_team_config()
    if config is None:
        console.print("[bold red]Error: Failed to get team config[/bold red]")
        return
    
    console.print("[bold green]Project Type: " + config.project_type.value + "[/bold green]")
    console.print("[bold]Team:[/bold] " + ", ".join(config.agents))
    console.print("[bold]Iteration Length:[/bold] " + config.iteration_length)


@cli.command()
@click.option("--port", "-p", default=8501, help="Port to run dashboard on (default: 8501)")
@click.option("--host", "-h", default="localhost", help="Host to bind (default: localhost)")
@click.option("--open-browser", "-o", is_flag=True, help="Open browser automatically")
def dashboard(port: int, host: str, open_browser: bool):
    """Start the AOP Dashboard web UI.
    
    A visual interface for:
    - Provider status monitoring
    - Task execution history
    - Hypothesis management
    - Learning records
    - Quick start guides
    
    \b
    Examples:
      aop dashboard
      aop dashboard --port 8080
      aop dashboard --open-browser
    
    \b
    Exit Codes:
      0 - Dashboard started successfully
      1 - Failed to start (streamlit not installed or other error)
    """
    try:
        from ..dashboard import run_dashboard
        import webbrowser
        
        console.print(Panel.fit(
            f"[bold cyan]🤖 AOP Dashboard[/bold cyan]\n\n"
            f"Starting at: [link]http://{host}:{port}[/link]\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            title="Dashboard",
            border_style="blue",
        ))
        
        if open_browser:
            webbrowser.open(f"http://{host}:{port}")
        
        run_dashboard(port=port, host=host)
        
    except ImportError:
        console.print("[bold red]Error: streamlit is not installed[/bold red]")
        console.print("\nInstall with:")
        console.print("  [cyan]pip install streamlit[/cyan]")
        console.print("\nOr reinstall AOP with dashboard support:")
        console.print("  [cyan]pip install git+https://github.com/xuha233/agent-orchestration-platform.git[/cyan]")
        sys.exit(EXIT_ERROR)
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped[/dim]")
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        console.print(f"[bold red]Error starting dashboard: {e}[/bold red]")
        sys.exit(EXIT_ERROR)


# Register agent command group
try:
    from .agent import agent as agent_group
    cli.add_command(agent_group, name="agent")
except ImportError:
    pass  # Agent module not available

