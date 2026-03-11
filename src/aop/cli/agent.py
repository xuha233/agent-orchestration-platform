"""
Agent automation CLI commands.

Full automated Agent team driven execution.
"""

from __future__ import annotations

import click
from pathlib import Path
from typing import Optional, List
import concurrent.futures
import time

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None

from ..agent import AgentDriver, AgentDriverConfig

if HAS_RICH:
    console = Console()
else:
    console = None

# Agent profiles registry
AGENT_PROFILES = {
    "reviewer": {
        "name": "Code Reviewer",
        "description": "Reviews code for quality, bugs, and best practices",
        "capabilities": ["code_review", "bug_detection", "style_check"]
    },
    "tester": {
        "name": "Test Engineer",
        "description": "Creates and runs tests, validates functionality",
        "capabilities": ["test_creation", "test_execution", "coverage_analysis"]
    },
    "implementer": {
        "name": "Implementer",
        "description": "Implements features and fixes based on specifications",
        "capabilities": ["code_writing", "refactoring", "feature_implementation"]
    },
    "architect": {
        "name": "Architect",
        "description": "Designs system architecture and structure",
        "capabilities": ["architecture_design", "pattern_recommendation", "scalability_analysis"]
    },
    "analyzer": {
        "name": "Code Analyzer",
        "description": "Analyzes codebase for patterns and issues",
        "capabilities": ["static_analysis", "dependency_analysis", "complexity_metrics"]
    },
    "documenter": {
        "name": "Documenter",
        "description": "Creates and maintains documentation",
        "capabilities": ["documentation", "api_docs", "readme_generation"]
    }
}


@click.group()
def agent():
    """
    Agent automation commands.

    Full automated Agent team driven execution.

    Commands:
      run       Run automated agent team task
      status    View current sprint status
      next      Get AI suggested next steps
      list      List available agent profiles
      dispatch  Parallel dispatch to multiple agents
    """
    pass


@agent.command("run")
@click.argument("description", required=False)
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with clarifications")
@click.option("--providers", "-P", default="claude", help="Providers to use")
@click.option("--storage", "-s", default=".aop", help="Storage path")
@click.option("--resume", "-r", default=None, help="Resume a specific sprint ID")
@click.option(
    "--orchestrator", "-o",
    type=click.Choice(["claude-code", "opencode", "openclaw", "api", "auto"]),
    default=None,
    help="Orchestrator type to use"
)
def run_agent(description: str, interactive: bool, providers: str, storage: str, resume: str, orchestrator: str):
    """Start automated Agent team execution."""
    orch_type = orchestrator or "auto"
    if orch_type == "auto":
        try:
            from ..orchestrator import get_best_orchestrator
            orch_type = get_best_orchestrator()
        except Exception:
            orch_type = "api"

    config = AgentDriverConfig(
        storage_path=Path(storage),
        auto_execute=True,
        parallel_execution=True,
        auto_validate=True,
        auto_learn=True,
        orchestrator_type=orch_type,
    )

    if HAS_RICH:
        console.print(f"[dim]Using orchestrator: {orch_type}[/dim]")
    else:
        click.echo(f"Using orchestrator: {orch_type}")

    driver = AgentDriver(config)

    if resume:
        if HAS_RICH:
            console.print(f"[cyan]Resuming sprint: {resume}[/cyan]")
        else:
            click.echo(f"Resuming sprint: {resume}")
        result = driver.resume_sprint(resume)

    elif description:
        if interactive:
            def clarifications_callback(question: str) -> str:
                return click.prompt(f"\n{question}", type=str)

            if HAS_RICH:
                console.print(Panel(f"[bold]Task:[/] {description}"))
                console.print("[cyan]Starting requirement clarification...[/cyan]")

            def progress_callback(stage: str, message: str):
                if HAS_RICH:
                    console.print(f"  [{stage}] {message}")
                else:
                    click.echo(f"  [{stage}] {message}")

            config.progress_callback = progress_callback
            result = driver.run_from_vague_description(
                description,
                clarifications_callback=clarifications_callback,
            )
        else:
            if HAS_RICH:
                console.print(Panel(f"[bold]Task:[/] {description}"))
                console.print("[cyan]Starting auto mode...[/cyan]")

            def progress_callback(stage: str, message: str):
                if HAS_RICH:
                    console.print(f"  [{stage}] {message}")
                else:
                    click.echo(f"  [{stage}] {message}")

            config.progress_callback = progress_callback
            result = driver.run_from_vague_description(description)

    else:
        if HAS_RICH:
            console.print("[red]Please provide task description, or use --resume to resume sprint[/red]")
        else:
            click.echo("Error: Please provide task description, or use --resume to resume sprint")
        raise SystemExit(1)

    if HAS_RICH:
        console.print("\n" + "=" * 50)
        console.print(Panel(
            f"[bold green]Sprint completed[/bold green]\n\n"
            f"ID: {result.sprint_id}\n"
            f"Status: {'Success' if result.success else 'Failed'}\n"
            f"Hypotheses: {len(result.hypotheses)}\n"
            f"Learnings: {len(result.learnings)}",
            title="Execution Result",
        ))

        if result.next_steps:
            console.print("\n[bold]Suggested next steps:[/bold]")
            for step in result.next_steps:
                console.print(f"  * {step}")
    else:
        click.echo("\n" + "=" * 50)
        click.echo(f"Sprint completed")
        click.echo(f"ID: {result.sprint_id}")
        click.echo(f"Status: {'Success' if result.success else 'Failed'}")
        click.echo(f"Hypotheses: {len(result.hypotheses)}")
        click.echo(f"Learnings: {len(result.learnings)}")


@agent.command("status")
@click.option("--sprint-id", "-s", default=None, help="Sprint ID")
def agent_status(sprint_id: str):
    """View current sprint status."""
    driver = AgentDriver()

    if sprint_id:
        driver.context = driver._load_context(sprint_id)

    if not driver.context:
        if HAS_RICH:
            console.print("[yellow]No active sprint[/yellow]")
            console.print("Use [cyan]aop agent run \"task description\"[/cyan] to start new sprint")
        else:
            click.echo("No active sprint")
            click.echo("Use 'aop agent run \"task description\"' to start new sprint")
        return

    if HAS_RICH:
        table = Table(title=f"Sprint Status: {driver.context.sprint_id}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Status", driver.context.state.value)
        table.add_row("Original Input", driver.context.original_input[:50] + "...")
        table.add_row("Hypotheses", str(len(driver.context.hypotheses)))
        table.add_row("Results", str(len(driver.context.execution_results)))
        table.add_row("Learnings", str(len(driver.context.learnings)))

        console.print(table)
    else:
        click.echo(f"Sprint status: {driver.context.sprint_id}")
        click.echo(f"  Status: {driver.context.state.value}")
        click.echo(f"  Original Input: {driver.context.original_input[:50]}...")
        click.echo(f"  Hypotheses: {len(driver.context.hypotheses)}")


@agent.command("next")
def agent_next():
    """Get AI suggested next steps."""
    driver = AgentDriver()
    next_steps = driver.get_next_steps()

    if HAS_RICH:
        console.print("[bold]Suggested next steps:[/bold]")
        for i, step in enumerate(next_steps, 1):
            console.print(f"  {i}. {step}")
    else:
        click.echo("Suggested next steps:")
        for i, step in enumerate(next_steps, 1):
            click.echo(f"  {i}. {step}")


@agent.command("list")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--available", is_flag=True, help="Show only available agents")
def agent_list(json_output: bool, available: bool):
    """List available agent profiles.
    
    Shows all registered agent profiles with their capabilities.
    
    Examples:
      aop agent list
      aop agent list --json
      aop agent list --available
    """
    # Get available orchestrators/agents
    available_agents = []
    try:
        from ..orchestrator import discover_orchestrators, get_available_orchestrators
        discovered = discover_orchestrators()
        available_agents = get_available_orchestrators()
    except Exception:
        pass
    
    if json_output:
        import json
        output = {
            "profiles": AGENT_PROFILES,
            "orchestrators": {
                "available": available_agents,
                "all": list(discovered.keys()) if "discovered" in dir() else []
            }
        }
        if HAS_RICH:
            console.print_json(data=output)
        else:
            click.echo(json.dumps(output, indent=2, ensure_ascii=False))
        return
    
    # Display agent profiles table
    if HAS_RICH:
        table = Table(title="Agent Profiles")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Description", style="dim")
        table.add_column("Capabilities", style="green")
        
        for agent_id, profile in AGENT_PROFILES.items():
            caps = ", ".join(profile["capabilities"][:2])
            if len(profile["capabilities"]) > 2:
                caps += "..."
            table.add_row(agent_id, profile["name"], profile["description"][:40] + "...", caps)
        
        console.print(table)
        
        # Display orchestrator availability
        if available_agents:
            orch_table = Table(title="Available Orchestrators/Agents")
            orch_table.add_column("Provider", style="cyan")
            orch_table.add_column("Status", style="green")
            
            for orch in available_agents:
                orch_table.add_row(orch, "[green]Available[/green]")
            
            console.print(orch_table)
        else:
            console.print("\n[yellow]No orchestrators available. Install one of: claude-code, opencode, openclaw[/yellow]")
    else:
        click.echo("Agent Profiles:\n")
        for agent_id, profile in AGENT_PROFILES.items():
            click.echo(f"  {agent_id}: {profile['name']}")
            click.echo(f"    {profile['description']}")
            click.echo(f"    Capabilities: {', '.join(profile['capabilities'])}")
        
        if available_agents:
            click.echo(f"\nAvailable Orchestrators: {', '.join(available_agents)}")
        else:
            click.echo("\nNo orchestrators available. Install one of: claude-code, opencode, openclaw")


@agent.command("dispatch")
@click.argument("task", required=True)
@click.option(
    "--agents", "-a",
    required=True,
    help="Comma-separated agent list (e.g., reviewer,tester)"
)
@click.option(
    "--provider",
    type=click.Choice(["opencode", "claude-code", "openclaw", "auto"]),
    default="auto",
    help="Provider to use for execution"
)
@click.option("--parallel/--sequential", default=True, help="Parallel or sequential execution (default: parallel)")
@click.option("--timeout", "-t", default=300, help="Timeout per agent in seconds")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def agent_dispatch(task: str, agents: str, provider: str, parallel: bool, timeout: int, json_output: bool):
    """Dispatch a task to multiple agents in parallel.
    
    Spawns multiple agent instances to work on the same task concurrently.
    
    Examples:
      aop agent dispatch "Review the auth module" --agents reviewer,analyzer
      aop agent dispatch "Implement feature X" --agents implementer,tester --provider claude-code
      aop agent dispatch "Analyze codebase" --agents architect,analyzer --sequential
    """
    agent_list = [a.strip() for a in agents.split(",") if a.strip()]
    
    # Validate agent list
    invalid_agents = [a for a in agent_list if a not in AGENT_PROFILES]
    if invalid_agents:
        if HAS_RICH:
            console.print(f"[red]Invalid agent(s): {', '.join(invalid_agents)}[/red]")
            console.print(f"[dim]Valid agents: {', '.join(AGENT_PROFILES.keys())}[/dim]")
        else:
            click.echo(f"Invalid agent(s): {', '.join(invalid_agents)}")
            click.echo(f"Valid agents: {', '.join(AGENT_PROFILES.keys())}")
        raise SystemExit(1)
    
    # Resolve provider
    actual_provider = provider
    if provider == "auto":
        try:
            from ..orchestrator import get_best_orchestrator
            actual_provider = get_best_orchestrator()
        except Exception:
            actual_provider = "api"
    
    if HAS_RICH:
        console.print(Panel(
            f"[bold]Dispatching task to {len(agent_list)} agents[/]\n\n"
            f"Task: {task[:50]}{'...' if len(task) > 50 else ''}\n"
            f"Agents: {', '.join(agent_list)}\n"
            f"Provider: {actual_provider}\n"
            f"Mode: {'Parallel' if parallel else 'Sequential'}"
        ))
    else:
        click.echo(f"Dispatching task to {len(agent_list)} agents")
        click.echo(f"  Task: {task[:50]}{'...' if len(task) > 50 else ''}")
        click.echo(f"  Agents: {', '.join(agent_list)}")
        click.echo(f"  Provider: {actual_provider}")
        click.echo(f"  Mode: {'Parallel' if parallel else 'Sequential'}")
    
    start_time = time.time()
    results = {}
    errors = []
    
    try:
        from ..orchestrator import create_orchestrator
        
        if parallel:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(agent_list)) as executor:
                futures = {}
                for agent_name in agent_list:
                    orch = create_orchestrator(actual_provider)
                    agent_prompt = f"[{agent_name}] {task}\n\nAct as {AGENT_PROFILES[agent_name]['name']}. {AGENT_PROFILES[agent_name]['description']}."
                    future = executor.submit(orch.execute, prompt=agent_prompt, cwd=".", timeout=timeout)
                    futures[future] = agent_name
                
                for future in concurrent.futures.as_completed(futures):
                    agent_name = futures[future]
                    try:
                        response = future.result()
                        results[agent_name] = {
                            "success": response.success,
                            "output": response.content[:1000] if response.content else None,
                            "duration": getattr(response, 'duration', None)
                        }
                    except Exception as e:
                        results[agent_name] = {"success": False, "error": str(e)}
                        errors.append(f"{agent_name}: {str(e)}")
        else:
            for agent_name in agent_list:
                try:
                    orch = create_orchestrator(actual_provider)
                    agent_prompt = f"[{agent_name}] {task}\n\nAct as {AGENT_PROFILES[agent_name]['name']}. {AGENT_PROFILES[agent_name]['description']}."
                    response = orch.execute(prompt=agent_prompt, cwd=".", timeout=timeout)
                    results[agent_name] = {
                        "success": response.success,
                        "output": response.content[:1000] if response.content else None,
                        "duration": getattr(response, 'duration', None)
                    }
                except Exception as e:
                    results[agent_name] = {"success": False, "error": str(e)}
                    errors.append(f"{agent_name}: {str(e)}")
                    
    except ImportError as e:
        if HAS_RICH:
            console.print(f"[red]Orchestrator module not available: {e}[/red]")
        else:
            click.echo(f"Error: Orchestrator module not available: {e}")
        raise SystemExit(1)
    
    duration = time.time() - start_time
    overall_success = all(r.get("success", False) for r in results.values())
    
    if json_output:
        import json
        output = {
            "task": task,
            "agents": agent_list,
            "provider": actual_provider,
            "parallel": parallel,
            "success": overall_success,
            "duration_seconds": round(duration, 2),
            "results": results,
            "errors": errors
        }
        if HAS_RICH:
            console.print_json(data=output)
        else:
            click.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if HAS_RICH:
            table = Table(title="Dispatch Results")
            table.add_column("Agent", style="cyan")
            table.add_column("Status")
            table.add_column("Output Preview", style="dim")
            
            for agent_name, result in results.items():
                status = "[green]Success[/green]" if result.get("success") else "[red]Failed[/red]"
                preview = (result.get("output") or "")[:50] + "..." if result.get("output") else "-"
                table.add_row(agent_name, status, preview)
            
            console.print(table)
            
            if overall_success:
                console.print(f"\n[bold green]All agents completed successfully[/bold green]")
            else:
                console.print(f"\n[bold yellow]Some agents failed. Check errors above.[/bold yellow]")
            
            console.print(f"[dim]Total duration: {duration:.2f}s[/dim]")
        else:
            click.echo("\nDispatch Results:")
            for agent_name, result in results.items():
                status = "Success" if result.get("success") else "Failed"
                click.echo(f"  {agent_name}: {status}")
            
            if overall_success:
                click.echo("\nAll agents completed successfully")
            else:
                click.echo("\nSome agents failed")
            
            click.echo(f"Total duration: {duration:.2f}s")
    
    sys_exit_code = 0 if overall_success else 1
    raise SystemExit(sys_exit_code)


__all__ = ["agent"]
