"""AOP CLI."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..core.engine import ExecutionEngine
from ..core.types import HypothesisState, ProjectType
from ..workflow.hypothesis import HypothesisManager
from ..workflow.learning import LearningLog
from ..workflow.team import TeamOrchestrator

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="aop")
def cli():
    """Agent Orchestration Platform."""
    pass


@cli.command()
def doctor():
    """Check provider availability."""
    engine = ExecutionEngine()
    results = engine.detect_providers()
    
    table = Table(title="Provider Status")
    table.add_column("Provider")
    table.add_column("Status")
    
    for pid, p in results.items():
        status = "[green]Available[/green]" if p.detected else "[red]Not found[/red]"
        table.add_row(pid, status)
    
    console.print(table)


@cli.command()
@click.option("--prompt", "-p", required=True)
@click.option("--providers", "-P", default="claude,codex")
def review(prompt, providers):
    """Run multi-agent review."""
    from ..core.engine import ReviewEngine
    provider_list = [p.strip() for p in providers.split(",")]
    console.print(Panel("Running review..."))
    
    engine = ReviewEngine(providers=provider_list)
    result = engine.review(prompt)
    
    console.print("Task: " + result.task_id)
    console.print("Duration: " + str(round(result.duration_seconds, 2)) + "s")
    console.print("Status: " + result.terminal_state.value)


@cli.group()
def hypothesis():
    """Manage hypotheses."""
    pass


@hypothesis.command("create")
@click.argument("statement")
def create_hypothesis(statement):
    """Create a hypothesis."""
    manager = HypothesisManager()
    h = manager.create(statement)
    console.print("[green]Created " + h.hypothesis_id + "[/green]")


@cli.group()
def project():
    """Project management."""
    pass


@project.command("assess")
@click.option("--problem-clarity", "-p", default="medium")
@click.option("--data-availability", "-d", default="medium")
@click.option("--tech-novelty", "-t", default="medium")
@click.option("--business-risk", "-b", default="medium")
def assess(problem_clarity, data_availability, tech_novelty, business_risk):
    """Assess project complexity."""
    orchestrator = TeamOrchestrator()
    orchestrator.assess_project(problem_clarity, data_availability, tech_novelty, business_risk)
    config = orchestrator.get_team_config()
    
    console.print("[bold green]Project Type: " + config.project_type.value + "[/bold green]")
    console.print("[bold]Team:[/bold] " + ", ".join(config.agents))


@cli.group()
def learning():
    """Capture and manage learnings."""
    pass


@learning.command("capture")
@click.option("--phase", "-p", required=True)
@click.option("--worked", "-w", multiple=True)
@click.option("--failed", "-f", multiple=True)
@click.option("--insight", "-i", multiple=True)
def capture_learning(phase, worked, failed, insight):
    """Capture learning from a phase."""
    log = LearningLog()
    learning = log.capture(phase=phase, what_worked=list(worked), what_failed=list(failed), insights=list(insight))
    console.print("[green]Captured learning from: " + phase + "[/green]")


if __name__ == "__main__":
    cli()