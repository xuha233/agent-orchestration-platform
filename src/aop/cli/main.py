"""AOP CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.engine import ExecutionEngine, ReviewEngine
from ..core.types import HypothesisState, ProjectType
from ..workflow.hypothesis import HypothesisManager
from ..workflow.learning import LearningLog
from ..workflow.team import TeamOrchestrator
from ..config import AOPConfig, find_config, load_config

console = Console()

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_CONFIG_NOT_FOUND = 2
EXIT_PROVIDER_UNAVAILABLE = 3


def _get_default_providers() -> str:
    """Get default providers from config or fallback."""
    config = load_config()
    return ",".join(config.providers)


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


@cli.command()
@click.option("--prompt", "-p", required=True, 
              help="The prompt/question for multi-agent review")
@click.option("--providers", "-P", default=None,
              help="Comma-separated provider list. Default: claude,codex (from config)")
@click.option("--repo", "-r", default=".",
              help="Repository root path. Default: current directory")
@click.option("--timeout", "-t", default=600,
              help="Timeout in seconds for each provider. Default: 600")
@click.option("--format", "-f", "output_format", default="report",
              type=click.Choice(["report", "json", "summary"]),
              help="Output format. Default: report")
def review(prompt: str, providers: Optional[str], repo: str, timeout: int, output_format: str):
    """Run multi-agent code review.
    
    \b
    Examples:
      aop review -p "Review the authentication module"
      aop review -p "Check for security issues" -P claude,gemini
      aop review -p "Analyze performance" -f json
    
    \b
    Exit Codes:
      0 - Review completed successfully
      1 - Review failed
    """
    # Load config and merge with CLI options
    config = load_config()
    provider_list = [p.strip() for p in (providers or ",".join(config.providers)).split(",")]
    
    console.print(Panel(f"[bold]Running review with:[/] {', '.join(provider_list)}"))
    
    engine = ReviewEngine(providers=provider_list, default_timeout=timeout)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing...", total=None)
        result = engine.review(prompt, repo_root=repo)
        progress.update(task, description="Complete")
    
    # Summary by severity
    if result.deduplicated_findings:
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in result.deduplicated_findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        
        console.print("\n[bold]Findings Summary:[/bold]")
        for sev in ["critical", "high", "medium", "low"]:
            count = severity_counts.get(sev, 0)
            color = {"critical": "red", "high": "yellow", "medium": "blue", "low": "dim"}[sev]
            console.print(f"  [{color}]{sev.upper()}: {count}[/{color}]")
    
    # Top findings
    if result.deduplicated_findings:
        sorted_findings = sorted(result.deduplicated_findings, 
                                 key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.severity, 4))
        console.print("\n[bold]Top Findings:[/bold]")
        for i, f in enumerate(sorted_findings[:5], 1):
            color = {"critical": "red", "high": "yellow", "medium": "blue", "low": "dim"}[f.severity]
            console.print(f"  {i}. [{color}][{f.severity.upper()}][/{color}] {f.title}")
            console.print(f"     [dim]{f.evidence.file}:{f.evidence.line or '-'}[/dim]")
    
    # Output based on format
    if output_format == "json":
        output = {
            "task_id": result.task_id,
            "success": result.success,
            "duration_seconds": result.duration_seconds,
            "findings_count": len(result.deduplicated_findings),
            "findings": [
                {
                    "id": f.finding_id,
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "file": f.evidence.file,
                    "line": f.evidence.line,
                    "recommendation": f.recommendation,
                    "detected_by": list(f.detected_by)
                }
                for f in result.deduplicated_findings
            ],
            "errors": result.errors
        }
        console.print_json(data=output)
    elif output_format == "summary":
        console.print(f"\n[bold]Task:[/] {result.task_id}")
        console.print(f"[bold]Duration:[/] {result.duration_seconds:.2f}s")
        console.print(f"[bold]Status:[/] {'[green]Success[/green]' if result.success else '[red]Failed[/red]'}")
        console.print(f"[bold]Total Findings:[/] {len(result.deduplicated_findings)}")
    else:
        console.print(f"\n[bold]Task:[/] {result.task_id}")
        console.print(f"[bold]Duration:[/] {result.duration_seconds:.2f}s")
        console.print(f"[bold]Status:[/] {'[green]Success[/green]' if result.success else '[red]Failed[/red]'}")
    
    if result.errors:
        console.print("\n[yellow]Warnings:[/yellow]")
        for err in result.errors:
            console.print(f"  * {err}")
    
    sys.exit(EXIT_SUCCESS if result.success else EXIT_ERROR)


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
    manager = HypothesisManager()
    h = manager.create(statement, priority=priority)
    console.print(f"[green]Created {h.hypothesis_id}[/green]")
    console.print(f"  Statement: {statement}")
    console.print(f"  Priority: {priority}")


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
    
    console.print("[bold green]Project Type: " + config.project_type.value + "[/bold green]")
    console.print("[bold]Team:[/bold] " + ", ".join(config.agents))
    console.print("[bold]Iteration Length:[/bold] " + config.iteration_length)


@cli.group()
def learning():
    """Capture and manage learnings.
    
    \b
    Commands:
      capture  Capture learnings from a phase
    
    \b
    Examples:
      aop learning capture -p exploration -w "Daily standups" -i "Short cycles work"
    """
    pass


@learning.command("capture")
@click.option("--phase", "-p", required=True, help="Phase name (e.g., exploration, implementation)")
@click.option("--worked", "-w", multiple=True, help="What worked (can specify multiple)")
@click.option("--failed", "-f", multiple=True, help="What failed (can specify multiple)")
@click.option("--insight", "-i", multiple=True, help="Key insights (can specify multiple)")
def capture_learning(phase: str, worked: tuple, failed: tuple, insight: tuple):
    """Capture learning from a phase.
    
    \b
    Examples:
      aop learning capture -p exploration -w "Daily standups" -w "Code reviews"
      aop learning capture -p implementation -f "Long meetings" -i "Short cycles work"
    
    \b
    Exit Codes:
      0 - Learning captured successfully
      1 - Failed to capture learning
    """
    log = LearningLog()
    learning = log.capture(phase=phase, what_worked=list(worked), what_failed=list(failed), insights=list(insight))
    console.print(f"[green]Captured learning from: {phase}[/green]")
    if worked:
        console.print(f"  [bold]What worked:[/] {', '.join(worked)}")
    if failed:
        console.print(f"  [bold]What failed:[/] {', '.join(failed)}")
    if insight:
        console.print(f"  [bold]Insights:[/] {', '.join(insight)}")


if __name__ == "__main__":
    cli()
