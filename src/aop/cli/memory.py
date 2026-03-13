"""Memory CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..memory import (
    MemoryService,
    MemoryConfig,
    MemoryMigrator,
    create_default_config,
)

console = Console()


@click.group()
def memory():
    """Memory management commands (mem0 integration)."""
    pass


@memory.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing config")
def init(force: bool):
    """Initialize memory configuration.
    
    Creates .aop/memory_config.yaml with default settings.
    mem0 is disabled by default for backward compatibility.
    """
    config_path = Path.cwd() / ".aop" / "memory_config.yaml"
    
    if config_path.exists() and not force:
        console.print("[yellow]Config already exists. Use --force to overwrite.[/yellow]")
        return
    
    create_default_config(config_path)
    console.print(f"[green]Created memory config:[/green] {config_path}")
    console.print("\n[bold]To enable mem0:[/bold]")
    console.print("  1. Install: [cyan]pip install mem0ai faiss-cpu[/cyan]")
    console.print("  2. Edit [cyan].aop/memory_config.yaml[/cyan]")
    console.print("  3. Set [cyan]enabled: true[/cyan]")


@memory.command()
def status():
    """Show memory service status."""
    config_path = Path.cwd() / ".aop" / "memory_config.yaml"
    
    if config_path.exists():
        config = MemoryConfig.from_yaml(config_path)
    else:
        config = MemoryConfig()
    
    service = MemoryService(config, workspace_path=Path.cwd())
    status_info = service.get_status()
    
    console.print(Panel.fit(
        f"[bold cyan]Memory Service Status[/bold cyan]\n\n"
        f"[bold]Backend:[/bold] {status_info['backend']}\n"
        f"[bold]mem0 Enabled:[/bold] {status_info['enabled']}\n"
        f"[bold]mem0 Available:[/bold] {'[green]Yes[/green]' if status_info['mem0_available'] else '[red]No[/red]'}\n"
        f"[bold]Project ID:[/bold] {status_info['project_id']}\n"
        f"[bold]Workspace:[/bold] {status_info['workspace']}"
        + (f"\n\n[yellow]Error:[/yellow] {status_info['init_error']}" if status_info.get('init_error') else ""),
        title="Memory Status",
        border_style="blue",
    ))
    
    # Show memory stats
    memories = service.list_all(limit=1000)
    if memories:
        console.print(f"\n[bold]Total memories:[/bold] {len(memories)}")
        
        # Group by type
        type_counts = {}
        for mem in memories:
            mem_type = mem.get("metadata", {}).get("type", "unknown")
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
        
        if type_counts:
            console.print("\n[bold]By type:[/bold]")
            for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
                console.print(f"  - {t}: {count}")


@memory.command()
@click.argument("content")
@click.option("--type", "-t", default="general", help="Memory type")
@click.option("--phase", "-p", default="", help="Phase (for learnings)")
@click.option("--hypothesis-id", "-h", default="", help="Related hypothesis ID")
def add(content: str, type: str, phase: str, hypothesis_id: str):
    """Add a new memory.
    
    Example:
        aop memory add "Using dataclasses improves code clarity" --type learning --phase build
    """
    config_path = Path.cwd() / ".aop" / "memory_config.yaml"
    
    if config_path.exists():
        config = MemoryConfig.from_yaml(config_path)
    else:
        config = MemoryConfig()
    
    service = MemoryService(config, workspace_path=Path.cwd())
    
    metadata = {"type": type}
    if phase:
        metadata["phase"] = phase
    if hypothesis_id:
        metadata["hypothesis_id"] = hypothesis_id
    
    memory_id = service.add(content, metadata=metadata)
    
    if memory_id:
        console.print(f"[green]Added memory:[/green] {memory_id}")
        console.print(f"  Content: {content[:80]}{'...' if len(content) > 80 else ''}")
        console.print(f"  Type: {type}")
    else:
        console.print("[red]Failed to add memory[/red]")
        sys.exit(1)


@memory.command()
@click.argument("query")
@click.option("--top-k", "-k", default=5, help="Number of results")
@click.option("--type", "-t", default=None, help="Filter by type")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def search(query: str, top_k: int, type: Optional[str], json_output: bool):
    """Search memories.
    
    Uses semantic search if mem0 is enabled, otherwise falls back to keyword search.
    
    Example:
        aop memory search "authentication" --top-k 10
        aop memory search "error" --type learning
    """
    config_path = Path.cwd() / ".aop" / "memory_config.yaml"
    
    if config_path.exists():
        config = MemoryConfig.from_yaml(config_path)
    else:
        config = MemoryConfig()
    
    service = MemoryService(config, workspace_path=Path.cwd())
    
    metadata_filter = {"type": type} if type else None
    results = service.search(query, top_k=top_k, metadata_filter=metadata_filter)
    
    if not results:
        console.print(f"[yellow]No memories found for: {query}[/yellow]")
        return
    
    if json_output:
        console.print_json(data={
            "query": query,
            "count": len(results),
            "results": results,
        })
        return
    
    console.print(f"\n[bold]Found {len(results)} memories:[/bold]\n")
    
    for i, mem in enumerate(results, 1):
        score = mem.get("score", 1.0)
        content = mem.get("content", "")
        mem_type = mem.get("metadata", {}).get("type", "unknown")
        
        console.print(f"[cyan]{i}.[/cyan] [{score:.2f}] [{mem_type}]")
        console.print(f"   {content[:100]}{'...' if len(content) > 100 else ''}")
        console.print()


@memory.command()
@click.option("--type", "-t", default=None, help="Filter by type")
@click.option("--limit", "-l", default=20, help="Max results")
def list(type: Optional[str], limit: int):
    """List all memories."""
    config_path = Path.cwd() / ".aop" / "memory_config.yaml"
    
    if config_path.exists():
        config = MemoryConfig.from_yaml(config_path)
    else:
        config = MemoryConfig()
    
    service = MemoryService(config, workspace_path=Path.cwd())
    
    metadata_filter = {"type": type} if type else None
    memories = service.list_all(metadata_filter=metadata_filter, limit=limit)
    
    if not memories:
        console.print("[yellow]No memories found[/yellow]")
        return
    
    table = Table(title=f"Memories ({len(memories)})")
    table.add_column("ID", style="cyan", max_width=15)
    table.add_column("Type", style="green", max_width=12)
    table.add_column("Content", max_width=50)
    table.add_column("Created", style="dim", max_width=12)
    
    for mem in memories:
        mem_id = mem.get("id", "")[:12]
        mem_type = mem.get("metadata", {}).get("type", "unknown")
        content = mem.get("content", "")[:50]
        created = mem.get("metadata", {}).get("timestamp", "")[:10]
        
        table.add_row(mem_id, mem_type, content, created)
    
    console.print(table)


@memory.command()
@click.argument("memory_id")
def get(memory_id: str):
    """Get a specific memory by ID."""
    config_path = Path.cwd() / ".aop" / "memory_config.yaml"
    
    if config_path.exists():
        config = MemoryConfig.from_yaml(config_path)
    else:
        config = MemoryConfig()
    
    service = MemoryService(config, workspace_path=Path.cwd())
    
    memory = service.get(memory_id)
    
    if not memory:
        console.print(f"[red]Memory not found:[/red] {memory_id}")
        sys.exit(1)
    
    console.print(Panel.fit(
        f"[bold cyan]Memory: {memory_id}[/bold cyan]\n\n"
        f"[bold]Content:[/bold]\n{memory.get('content', '')}\n\n"
        f"[bold]Metadata:[/bold]\n{json.dumps(memory.get('metadata', {}), indent=2, ensure_ascii=False)}",
        title="Memory Details",
        border_style="blue",
    ))


@memory.command()
@click.argument("memory_id")
@click.confirmation_option(prompt="Are you sure you want to delete this memory?")
def delete(memory_id: str):
    """Delete a memory."""
    config_path = Path.cwd() / ".aop" / "memory_config.yaml"
    
    if config_path.exists():
        config = MemoryConfig.from_yaml(config_path)
    else:
        config = MemoryConfig()
    
    service = MemoryService(config, workspace_path=Path.cwd())
    
    if service.delete(memory_id):
        console.print(f"[green]Deleted memory:[/green] {memory_id}")
    else:
        console.print(f"[red]Failed to delete memory:[/red] {memory_id}")
        sys.exit(1)


@memory.command()
@click.option("--dry-run", is_flag=True, help="Simulate migration without making changes")
@click.option("--include-hypotheses", is_flag=True, default=True, help="Migrate hypotheses")
@click.option("--include-learnings", is_flag=True, default=True, help="Migrate learnings")
@click.option("--include-project-memory", is_flag=True, default=True, help="Migrate PROJECT_MEMORY.md")
def migrate(dry_run: bool, include_hypotheses: bool, include_learnings: bool, include_project_memory: bool):
    """Migrate existing memories to mem0.
    
    Migrates:
    - hypotheses.json -> mem0 memories
    - learning.json -> mem0 memories
    - PROJECT_MEMORY.md -> mem0 memories
    
    Example:
        aop memory migrate --dry-run
        aop memory migrate
    """
    config_path = Path.cwd() / ".aop" / "memory_config.yaml"
    
    if config_path.exists():
        config = MemoryConfig.from_yaml(config_path)
    else:
        config = MemoryConfig()
    
    # Check if mem0 is available
    service = MemoryService(config, workspace_path=Path.cwd())
    
    if not service.is_mem0_available and not dry_run:
        console.print("[yellow]mem0 is not available. Running in dry-run mode.[/yellow]")
        console.print("To enable mem0:")
        console.print("  1. Install: [cyan]pip install mem0ai faiss-cpu[/cyan]")
        console.print("  2. Edit [cyan].aop/memory_config.yaml[/cyan]")
        console.print("  3. Set [cyan]enabled: true[/cyan]")
        dry_run = True
    
    migrator = MemoryMigrator(service, workspace_path=Path.cwd())
    
    # Analyze first
    console.print("\n[bold]Analyzing existing memories...[/bold]\n")
    analysis = migrator.analyze()
    
    if not analysis["files"]:
        console.print("[yellow]No memories found to migrate[/yellow]")
        return
    
    for filename, info in analysis["files"].items():
        if "count" in info:
            console.print(f"  - {filename}: {info['count']} entries")
        elif "lines" in info:
            console.print(f"  - {filename}: {info['lines']} lines")
    
    if analysis["issues"]:
        console.print("\n[yellow]Issues:[/yellow]")
        for issue in analysis["issues"]:
            console.print(f"  - {issue}")
    
    if dry_run:
        console.print("\n[bold cyan]Dry run - simulating migration...[/bold cyan]\n")
    else:
        console.print("\n[bold cyan]Migrating...[/bold cyan]\n")
    
    # Perform migration
    result = migrator.migrate_all(
        dry_run=dry_run,
        include_hypotheses=include_hypotheses,
        include_learnings=include_learnings,
        include_project_memory=include_project_memory,
    )
    
    # Show results
    if result["hypotheses"]:
        console.print(f"[green]Hypotheses:[/green] {result['hypotheses']['count']} migrated")
    
    if result["learnings"]:
        console.print(f"[green]Learnings:[/green] {result['learnings']['count']} migrated")
    
    if result["project_memory"]:
        console.print(f"[green]Project memory:[/green] {result['project_memory']['count']} sections migrated")
    
    console.print(f"\n[bold]Total migrated:[/bold] {result['total']}")
    
    if result["errors"]:
        console.print("\n[red]Errors:[/red]")
        for err in result["errors"]:
            console.print(f"  - {err}")
    
    if dry_run:
        console.print("\n[dim]This was a dry run. Remove --dry-run to actually migrate.[/dim]")


@memory.command()
def export():
    """Export memory migration report."""
    config_path = Path.cwd() / ".aop" / "memory_config.yaml"
    
    if config_path.exists():
        config = MemoryConfig.from_yaml(config_path)
    else:
        config = MemoryConfig()
    
    service = MemoryService(config, workspace_path=Path.cwd())
    migrator = MemoryMigrator(service, workspace_path=Path.cwd())
    
    output_path = Path.cwd() / ".aop" / "memory_migration_report.md"
    report = migrator.export_migration_report(output_path)
    
    console.print(f"[green]Exported migration report to:[/green] {output_path}")
