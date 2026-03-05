"""
Orchestrator CLI 命令组

管理和检测中枢 Agent (Orchestrator)

命令:
  aop orchestrator doctor  - 检测所有可用的中枢
  aop orchestrator list    - 列出所有可用的中枢
  aop orchestrator use     - 设置项目使用的中枢类型
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None

from ..orchestrator import (
    discover_orchestrators,
    get_available_orchestrators,
    get_best_orchestrator,
    create_orchestrator,
    ORCHESTRATOR_REGISTRY,
)

if HAS_RICH:
    console = Console()
else:
    console = None


# 项目配置文件路径
PROJECT_CONFIG_FILE = ".aop.yaml"


def _get_project_orchestrator() -> Optional[str]:
    """获取项目配置的中枢类型"""
    config_path = Path(PROJECT_CONFIG_FILE)
    if not config_path.exists():
        return None

    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("orchestrator")
    except Exception:
        return None


def _set_project_orchestrator(orchestrator_type: str) -> bool:
    """设置项目配置的中枢类型"""
    config_path = Path(PROJECT_CONFIG_FILE)

    try:
        import yaml

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        config["orchestrator"] = orchestrator_type

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        return True
    except Exception:
        return False


@click.group()
def orchestrator():
    """
    中枢 Agent (Orchestrator) 管理

    管理和检测可用的中枢类型，支持：
      - claude-code: Claude Code CLI 作为中枢
      - opencode: OpenCode CLI 作为中枢
      - openclaw: OpenClaw 作为中枢
      - api: API 方式作为中枢

    \b
    命令:
      doctor  检测所有可用的中枢
      list    列出所有可用的中枢
      use     设置项目使用的中枢类型

    \b
    示例:
      aop orchestrator doctor
      aop orchestrator list
      aop orchestrator use claude-code
    """
    pass


@orchestrator.command("doctor")
@click.option("--json", "json_output", is_flag=True, help="输出 JSON 格式")
@click.option("--verbose", "-v", is_flag=True, help="显示详细信息")
def doctor(json_output: bool, verbose: bool):
    """
    检测所有可用的中枢

    扫描系统并检测哪些中枢可用，显示详细信息包括：
      - 是否检测到
      - 版本信息
      - 认证状态
      - 支持的能力

    \b
    示例:
      aop orchestrator doctor
      aop orchestrator doctor --json
      aop orchestrator doctor -v

    \b
    退出码:
      0 - 至少有一个中枢可用
      1 - 没有可用的中枢
    """
    discovered = discover_orchestrators()
    available = [t for t, p in discovered.items() if p.detected and p.auth_ok]
    current = _get_project_orchestrator()

    if json_output:
        import json
        output = {
            "orchestrators": {
                orch_type: presence.to_dict()
                for orch_type, presence in discovered.items()
            },
            "available": available,
            "best": get_best_orchestrator(),
            "current_project_setting": current,
        }
        if HAS_RICH:
            console.print_json(data=output)
        else:
            click.echo(json.dumps(output, indent=2, ensure_ascii=False))
        return

    if HAS_RICH:
        table = Table(title="Orchestrator Status")
        table.add_column("Type", style="cyan")
        table.add_column("Status")
        table.add_column("Version")
        table.add_column("Auth")
        table.add_column("Current", style="magenta")

        for orch_type in ORCHESTRATOR_REGISTRY.keys():
            if orch_type == "api":
                # API 类型需要 LLMClient，标记为特殊
                is_current = " (current)" if current == orch_type else ""
                table.add_row(
                    orch_type,
                    "[dim]requires LLMClient[/dim]",
                    "-",
                    "-",
                    "*" if current == orch_type else ""
                )
                continue

            presence = discovered.get(orch_type)
            if not presence:
                table.add_row(orch_type, "[dim]unknown[/dim]", "-", "-", "")
                continue

            if presence.detected:
                status = "[green]Available[/green]"
            else:
                status = "[red]Not Found[/red]"

            version = presence.version or "-"
            auth = "[green]OK[/green]" if presence.auth_ok else "[red]Failed[/red]"

            table.add_row(
                orch_type,
                status,
                version,
                auth,
                "*" if current == orch_type else ""
            )

        console.print(table)

        # 显示当前设置
        if current:
            console.print(f"\n[cyan]Current project setting:[/] {current}")
        else:
            console.print("\n[cyan]Current project setting:[/] [dim]not set (auto)[/dim]")

        # 显示最佳选择
        best = get_best_orchestrator()
        console.print(f"[cyan]Best available:[/] {best}")

        # 显示详细信息
        if verbose:
            console.print("\n[bold]Details:[/bold]")
            for orch_type, presence in discovered.items():
                if presence.detected:
                    console.print(f"\n  [cyan]{orch_type}:[/cyan]")
                    console.print(f"    Binary: {presence.binary_path or 'N/A'}")
                    console.print(f"    Capabilities: {', '.join(c.value for c in presence.capabilities)}")
                    if presence.reason:
                        console.print(f"    Note: {presence.reason}")

        # 显示建议
        if not available:
            console.print("\n[yellow]No orchestrator available![/yellow]")
            console.print("Install one of the following:")
            console.print("  - claude-code: Install Claude CLI and run 'claude auth'")
            console.print("  - opencode: Install OpenCode CLI")
            console.print("  - openclaw: Install and configure OpenClaw")
    else:
        click.echo("Orchestrator Status:\n")
        for orch_type in ORCHESTRATOR_REGISTRY.keys():
            if orch_type == "api":
                click.echo(f"  {orch_type}: requires LLMClient")
                continue

            presence = discovered.get(orch_type)
            if not presence:
                click.echo(f"  {orch_type}: unknown")
                continue

            status = "Available" if presence.detected else "Not Found"
            auth = "OK" if presence.auth_ok else "Failed"
            marker = " (current)" if current == orch_type else ""
            click.echo(f"  {orch_type}: {status}, auth={auth}{marker}")

        if current:
            click.echo(f"\nCurrent project setting: {current}")
        else:
            click.echo("\nCurrent project setting: not set (auto)")

        best = get_best_orchestrator()
        click.echo(f"Best available: {best}")

    # 退出码
    if not available:
        sys.exit(1)
    sys.exit(0)


@orchestrator.command("list")
@click.option("--json", "json_output", is_flag=True, help="输出 JSON 格式")
def list_orchestrators(json_output: bool):
    """
    列出所有可用的中枢

    仅显示已检测且认证通过的中枢类型。

    \b
    示例:
      aop orchestrator list
      aop orchestrator list --json

    \b
    退出码:
      0 - 成功
    """
    discovered = discover_orchestrators()
    available = get_available_orchestrators()
    current = _get_project_orchestrator()

    if json_output:
        import json
        output = {
            "available": available,
            "all_types": list(ORCHESTRATOR_REGISTRY.keys()),
            "current_project_setting": current,
            "details": {
                orch_type: presence.to_dict()
                for orch_type, presence in discovered.items()
            }
        }
        if HAS_RICH:
            console.print_json(data=output)
        else:
            click.echo(json.dumps(output, indent=2, ensure_ascii=False))
        return

    if HAS_RICH:
        table = Table(title="Available Orchestrators")
        table.add_column("Type", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Current", style="magenta")

        for orch_type in ORCHESTRATOR_REGISTRY.keys():
            if orch_type == "api":
                table.add_row(orch_type, "[dim]requires config[/dim]", "*" if current == orch_type else "")
                continue

            is_available = orch_type in available
            status = "[green]Ready[/green]" if is_available else "[dim]Not Ready[/dim]"
            table.add_row(orch_type, status, "*" if current == orch_type else "")

        console.print(table)

        if available:
            console.print(f"\n[cyan]Ready to use:[/] {', '.join(available)}")
        else:
            console.print("\n[yellow]No orchestrators ready. Run 'aop orchestrator doctor' for details.[/yellow]")
    else:
        click.echo("Available Orchestrators:\n")
        for orch_type in ORCHESTRATOR_REGISTRY.keys():
            if orch_type == "api":
                marker = " (current)" if current == orch_type else ""
                click.echo(f"  {orch_type}: requires config{marker}")
                continue

            is_available = orch_type in available
            status = "Ready" if is_available else "Not Ready"
            marker = " (current)" if current == orch_type else ""
            click.echo(f"  {orch_type}: {status}{marker}")

        if available:
            click.echo(f"\nReady to use: {', '.join(available)}")
        else:
            click.echo("\nNo orchestrators ready. Run 'aop orchestrator doctor' for details.")

    sys.exit(0)


@orchestrator.command("use")
@click.argument("orchestrator_type", required=True)
@click.option("--force", "-f", is_flag=True, help="强制设置，即使中枢不可用")
def use_orchestrator(orchestrator_type: str, force: bool):
    """
    设置项目使用的中枢类型

    将指定的中枢类型保存到项目配置文件 (.aop.yaml)。

    \b
    可用类型:
      claude-code  - Claude Code CLI
      opencode     - OpenCode CLI
      openclaw     - OpenClaw
      api          - API 方式 (需要配置 LLMClient)
      auto         - 自动选择最佳可用

    \b
    示例:
      aop orchestrator use claude-code
      aop orchestrator use auto
      aop orchestrator use api --force

    \b
    退出码:
      0 - 设置成功
      1 - 设置失败 (类型无效或不可用)
    """
    # 验证类型
    valid_types = list(ORCHESTRATOR_REGISTRY.keys()) + ["auto"]
    if orchestrator_type not in valid_types:
        if HAS_RICH:
            console.print(f"[red]Error: Invalid orchestrator type '{orchestrator_type}'[/red]")
            console.print(f"Valid types: {', '.join(valid_types)}")
        else:
            click.echo(f"Error: Invalid orchestrator type '{orchestrator_type}'")
            click.echo(f"Valid types: {', '.join(valid_types)}")
        sys.exit(1)

    # 检查可用性（除非 --force）
    if orchestrator_type != "auto" and orchestrator_type != "api":
        available = get_available_orchestrators()
        if orchestrator_type not in available and not force:
            if HAS_RICH:
                console.print(f"[yellow]Warning: '{orchestrator_type}' is not available[/yellow]")
                console.print("Run 'aop orchestrator doctor' for details")
                console.print("Use --force to set anyway")
            else:
                click.echo(f"Warning: '{orchestrator_type}' is not available")
                click.echo("Run 'aop orchestrator doctor' for details")
                click.echo("Use --force to set anyway")
            sys.exit(1)

    # 设置配置
    success = _set_project_orchestrator(orchestrator_type)
    if success:
        if HAS_RICH:
            console.print(f"[green]Set orchestrator to: {orchestrator_type}[/green]")
            console.print(f"[dim]Saved to {PROJECT_CONFIG_FILE}[/dim]")

            # 显示当前状态
            if orchestrator_type == "auto":
                best = get_best_orchestrator()
                console.print(f"[cyan]Auto will use: {best}[/cyan]")
        else:
            click.echo(f"Set orchestrator to: {orchestrator_type}")
            click.echo(f"Saved to {PROJECT_CONFIG_FILE}")

            if orchestrator_type == "auto":
                best = get_best_orchestrator()
                click.echo(f"Auto will use: {best}")

        sys.exit(0)
    else:
        if HAS_RICH:
            console.print(f"[red]Failed to save configuration[/red]")
        else:
            click.echo("Failed to save configuration")
        sys.exit(1)


__all__ = ["orchestrator"]
