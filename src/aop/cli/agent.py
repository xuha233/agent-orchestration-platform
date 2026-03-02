"""
Agent 自动化 CLI 命令

全自动的 Agent 团队驱动，从模糊需求到交付。
"""

from __future__ import annotations

import click
from pathlib import Path
from typing import Optional

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


@click.group()
def agent():
    """
    Agent 自动化命令组

    全自动的 Agent 团队驱动，从模糊需求到交付。

    \b
    使用场景:
      - 快速原型开发
      - 自动化开发任务
      - Agent 团队协作

    \b
    示例:
      aop agent run "做一个电商系统"
      aop agent run -i "做一个电商系统"  # 交互式追问
      aop agent status
    """
    pass


@agent.command("run")
@click.argument("description", required=False)
@click.option("--interactive", "-i", is_flag=True, help="交互式追问模式")
@click.option("--providers", "-P", default="claude", help="使用的Provider")
@click.option("--storage", "-s", default=".aop", help="存储路径")
@click.option("--resume", "-r", default=None, help="恢复指定冲刺ID")
def run_agent(description: str, interactive: bool, providers: str, storage: str, resume: str):
    """
    启动全自动 Agent 团队

    \b
    示例:
      aop agent run "做一个电商系统"
      aop agent run -i  # 交互模式，会追问
      aop agent run -r sprint-abc123  # 恢复冲刺

    \b
    流程:
      1. 需求澄清（交互式或自动）
      2. 假设生成
      3. 任务分解
      4. 并行执行
      5. 自动验证
      6. 学习提取
    """
    config = AgentDriverConfig(
        storage_path=Path(storage),
        auto_execute=True,
        parallel_execution=True,
        auto_validate=True,
        auto_learn=True,
    )

    driver = AgentDriver(config)

    if resume:
        # 恢复冲刺
        if HAS_RICH:
            console.print(f"[cyan]恢复冲刺: {resume}[/cyan]")
        else:
            click.echo(f"恢复冲刺: {resume}")
        result = driver.resume_sprint(resume)

    elif description:
        # 从描述启动
        if interactive:
            # 交互模式
            def clarifications_callback(question: str) -> str:
                return click.prompt(f"\n{question}", type=str)

            if HAS_RICH:
                console.print(Panel(f"[bold]任务:[/] {description}"))
                console.print("[cyan]开始澄清需求...[/cyan]")

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
            # 自动模式
            if HAS_RICH:
                console.print(Panel(f"[bold]任务:[/] {description}"))
                console.print("[cyan]自动模式启动...[/cyan]")

            def progress_callback(stage: str, message: str):
                if HAS_RICH:
                    console.print(f"  [{stage}] {message}")
                else:
                    click.echo(f"  [{stage}] {message}")

            config.progress_callback = progress_callback
            result = driver.run_from_vague_description(description)

    else:
        if HAS_RICH:
            console.print("[red]请提供任务描述，或使用 --resume 恢复冲刺[/red]")
        else:
            click.echo("错误: 请提供任务描述，或使用 --resume 恢复冲刺")
        raise SystemExit(1)

    # 显示结果
    if HAS_RICH:
        console.print("\n" + "=" * 50)
        console.print(Panel(
            f"[bold green]冲刺完成[/bold green]\n\n"
            f"ID: {result.sprint_id}\n"
            f"状态: {'成功' if result.success else '失败'}\n"
            f"假设数: {len(result.hypotheses)}\n"
            f"学习数: {len(result.learnings)}",
            title="执行结果",
        ))

        if result.next_steps:
            console.print("\n[bold]下一步建议:[/bold]")
            for step in result.next_steps:
                console.print(f"  • {step}")
    else:
        click.echo("\n" + "=" * 50)
        click.echo(f"冲刺完成")
        click.echo(f"ID: {result.sprint_id}")
        click.echo(f"状态: {'成功' if result.success else '失败'}")
        click.echo(f"假设数: {len(result.hypotheses)}")
        click.echo(f"学习数: {len(result.learnings)}")


@agent.command("status")
@click.option("--sprint-id", "-s", default=None, help="冲刺ID")
def agent_status(sprint_id: str):
    """
    查看当前冲刺状态

    \b
    示例:
      aop agent status
      aop agent status -s sprint-abc123
    """
    driver = AgentDriver()

    if sprint_id:
        driver.context = driver._load_context(sprint_id)

    if not driver.context:
        if HAS_RICH:
            console.print("[yellow]没有活跃的冲刺[/yellow]")
            console.print("使用 [cyan]aop agent run \"任务描述\"[/cyan] 启动新冲刺")
        else:
            click.echo("没有活跃的冲刺")
            click.echo("使用 'aop agent run \"任务描述\"' 启动新冲刺")
        return

    # 显示状态
    if HAS_RICH:
        table = Table(title=f"冲刺状态: {driver.context.sprint_id}")
        table.add_column("属性", style="cyan")
        table.add_column("值", style="white")

        table.add_row("状态", driver.context.state.value)
        table.add_row("原始输入", driver.context.original_input[:50] + "...")
        table.add_row("假设数", str(len(driver.context.hypotheses)))
        table.add_row("结果数", str(len(driver.context.execution_results)))
        table.add_row("学习数", str(len(driver.context.learnings)))

        console.print(table)
    else:
        click.echo(f"冲刺状态: {driver.context.sprint_id}")
        click.echo(f"  状态: {driver.context.state.value}")
        click.echo(f"  原始输入: {driver.context.original_input[:50]}...")
        click.echo(f"  假设数: {len(driver.context.hypotheses)}")


@agent.command("next")
def agent_next():
    """
    获取 AI 建议的下一步操作

    分析当前状态，给出智能建议
    """
    driver = AgentDriver()
    next_steps = driver.get_next_steps()

    if HAS_RICH:
        console.print("[bold]建议的下一步:[/bold]")
        for i, step in enumerate(next_steps, 1):
            console.print(f"  {i}. {step}")
    else:
        click.echo("建议的下一步:")
        for i, step in enumerate(next_steps, 1):
            click.echo(f"  {i}. {step}")


@agent.command("list")
def agent_list():
    """
    列出所有冲刺
    """
    import json
    from pathlib import Path

    storage_path = Path(".aop/sprints")
    if not storage_path.exists():
        if HAS_RICH:
            console.print("[yellow]没有找到冲刺记录[/yellow]")
        else:
            click.echo("没有找到冲刺记录")
        return

    sprints = list(storage_path.glob("sprint-*.json"))

    if not sprints:
        if HAS_RICH:
            console.print("[yellow]没有找到冲刺记录[/yellow]")
        else:
            click.echo("没有找到冲刺记录")
        return

    if HAS_RICH:
        table = Table(title="冲刺列表")
        table.add_column("Sprint ID", style="cyan")
        table.add_column("状态", style="white")
        table.add_column("创建时间", style="dim")

        for sprint_file in sorted(sprints, reverse=True):
            with open(sprint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            table.add_row(
                data.get("sprint_id", sprint_file.stem),
                data.get("state", "unknown"),
                data.get("created_at", "unknown")[:19]
            )

        console.print(table)
    else:
        click.echo("冲刺列表:")
        for sprint_file in sorted(sprints, reverse=True):
            with open(sprint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            click.echo(f"  {data.get('sprint_id')}: {data.get('state')}")
