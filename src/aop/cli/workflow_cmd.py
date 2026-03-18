"""Workflow inspection commands for the AOP CLI."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..workflow import WorkflowRunReader

console = Console()


@click.group()
def workflow_group():
    """Inspect persisted workflow run artifacts."""
    pass


@workflow_group.command("show")
def workflow_show():
    """Show the latest workflow run."""
    reader = WorkflowRunReader(Path.cwd())
    run = reader.get_latest_run()
    if run is None:
        console.print("[yellow]No workflow runs found under .aop/runs[/yellow]")
        return

    body = (
        f"[bold]Run ID:[/bold] {run.run_id}\n"
        f"[bold]Status:[/bold] {run.status}\n"
        f"[bold]Phase:[/bold] {run.current_phase}\n"
        f"[bold]Completion:[/bold] {run.completion_status or '-'}\n"
        f"[bold]Verification:[/bold] {run.verification_verdict or '-'}\n"
        f"[bold]Has Gaps:[/bold] {'yes' if run.has_gaps else 'no'}\n"
        f"[bold]Has Guardrails:[/bold] {'yes' if run.has_guardrails else 'no'}\n\n"
        f"[bold]Original Input:[/bold] {run.original_input[:120] or '-'}\n"
        f"[bold]Summary:[/bold] {run.clarified_summary[:120] or '-'}"
    )
    console.print(Panel.fit(body, title="Latest Workflow Run", border_style="magenta"))


@workflow_group.command("list")
@click.option("--limit", "-n", default=5, help="Number of runs to show")
def workflow_list(limit: int):
    """List recent workflow runs."""
    reader = WorkflowRunReader(Path.cwd())
    runs = reader.list_runs(limit=limit)
    if not runs:
        console.print("[yellow]No workflow runs found under .aop/runs[/yellow]")
        return

    table = Table(title="Workflow Runs")
    table.add_column("Run ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Phase", style="yellow")
    table.add_column("Verification")
    table.add_column("Completion")
    table.add_column("Flags")

    for run in runs:
        flags = []
        if run.has_gaps:
            flags.append("gaps")
        if run.has_guardrails:
            flags.append("guardrails")
        table.add_row(
            run.run_id,
            run.status,
            run.current_phase,
            run.verification_verdict or "-",
            run.completion_status or "-",
            ", ".join(flags) if flags else "-",
        )

    console.print(table)
