"""
Knowledge CLI - 知识库相关命令
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..knowledge.patterns import StartupPatternLibrary, StartupPattern
from ..knowledge.anti_patterns import AntiPatternLibrary, AntiPatternWarning
from ..knowledge.learning_store import LearningStore

console = Console()


@click.group()
def knowledge():
    """创业知识库管理。"""
    pass


@knowledge.command("search")
@click.argument("query")
@click.option("--tags", "-t", help="标签过滤，逗号分隔")
@click.option("--json", "json_output", is_flag=True, help="JSON 输出")
def search_patterns(query: str, tags: Optional[str], json_output: bool):
    """搜索创业模式。
    
    示例：
        aop knowledge search "需求验证"
        aop knowledge search "mvp" --tags validation,low-cost
    """
    library = StartupPatternLibrary()
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    patterns = library.search_patterns(query, tag_list)
    
    if not patterns:
        console.print(f"[yellow]未找到匹配的模式：{query}[/yellow]")
        return
    
    if json_output:
        output = {
            "query": query,
            "count": len(patterns),
            "patterns": [p.to_dict() for p in patterns]
        }
        console.print_json(data=output)
        return
    
    console.print(f"\n[bold]找到 {len(patterns)} 个模式：[/bold]\n")
    
    for i, pattern in enumerate(patterns, 1):
        console.print(f"[cyan]{i}. {pattern.name}[/cyan]")
        console.print(f"   {pattern.description}")
        console.print(f"   [dim]适用场景: {', '.join(pattern.when_to_use[:3])}[/dim]")
        if pattern.examples:
            console.print(f"   [dim]案例: {', '.join(pattern.examples[:2])}[/dim]")
        console.print()


@knowledge.command("suggest")
@click.option("--stage", "-s", help="项目阶段 (idea/validation/growth/scale)")
@click.option("--type", "-t", "project_type", help="项目类型 (b2b/b2c/marketplace)")
@click.option("--low-budget", is_flag=True, help="预算有限")
@click.option("--json", "json_output", is_flag=True, help="JSON 输出")
def suggest_patterns(stage: Optional[str], project_type: Optional[str], low_budget: bool, json_output: bool):
    """根据项目情况建议模式。
    
    示例：
        aop knowledge suggest --stage idea --low-budget
        aop knowledge suggest --type b2b --stage validation
    """
    library = StartupPatternLibrary()
    
    context = {}
    if stage:
        context["stage"] = stage
    if project_type:
        context["project_type"] = project_type
    if low_budget:
        context["constraints"] = {"low_budget": True}
    
    patterns = library.suggest_patterns(context)
    
    if not patterns:
        console.print("[yellow]根据当前条件未找到推荐模式[/yellow]")
        return
    
    if json_output:
        output = {
            "context": context,
            "count": len(patterns),
            "patterns": [p.to_dict() for p in patterns]
        }
        console.print_json(data=output)
        return
    
    console.print(f"\n[bold]推荐 {len(patterns)} 个模式：[/bold]\n")
    
    for i, pattern in enumerate(patterns, 1):
        success_rate = f"{pattern.success_rate*100:.0f}%" if pattern.success_rate else "N/A"
        console.print(f"[cyan]{i}. {pattern.name}[/cyan] (成功率: {success_rate})")
        console.print(f"   {pattern.description}")
        console.print(f"   [dim]难度: {pattern.difficulty} | 时间: {pattern.time_to_value}[/dim]")
        console.print()


@knowledge.command("antipatterns")
@click.option("--decisions", "-d", multiple=True, help="已做决策")
@click.option("--behaviors", "-b", multiple=True, help="当前行为")
@click.option("--json", "json_output", is_flag=True, help="JSON 输出")
def check_antipatterns(decisions: tuple, behaviors: tuple, json_output: bool):
    """检查项目中是否存在反模式。
    
    示例：
        aop knowledge antipatterns --decisions "先做完整架构" --behaviors "还没和用户聊过"
    """
    library = AntiPatternLibrary()
    
    context = {
        "decisions": list(decisions),
        "behaviors": list(behaviors),
    }
    
    warnings = library.check_for_antipatterns(context)
    
    if not warnings:
        console.print("[green]未检测到明显反模式[/green]")
        return
    
    if json_output:
        output = {
            "warnings": [
                {
                    "antipattern": w.anti_pattern.to_dict(),
                    "matched_symptoms": w.matched_symptoms,
                    "risk_level": w.risk_level,
                    "recommendation": w.recommendation,
                }
                for w in warnings
            ]
        }
        console.print_json(data=output)
        return
    
    severity_colors = {
        "critical": "red",
        "high": "yellow",
        "medium": "blue",
        "low": "dim",
    }
    
    console.print(f"\n[bold]检测到 {len(warnings)} 个潜在反模式：[/bold]\n")
    
    for warning in warnings:
        color = severity_colors.get(warning.risk_level, "white")
        
        console.print(f"[{color}]⚠ {warning.anti_pattern.name}[/{color}]")
        console.print(f"   风险等级: [{color}]{warning.risk_level.upper()}[/{color}]")
        console.print(f"   {warning.anti_pattern.description}")
        
        if warning.matched_symptoms:
            console.print(f"   [dim]匹配症状: {', '.join(warning.matched_symptoms[:3])}[/dim]")
        
        console.print(f"   [green]建议: {warning.recommendation}[/green]")
        console.print()


@knowledge.command("list")
@click.option("--type", "-t", "entry_type", type=click.Choice(["patterns", "antipatterns", "all"]), default="all", help="显示类型")
@click.option("--json", "json_output", is_flag=True, help="JSON 输出")
def list_knowledge(entry_type: str, json_output: bool):
    """列出所有知识库条目。"""
    if entry_type in ("patterns", "all"):
        pattern_lib = StartupPatternLibrary()
        patterns = pattern_lib.list_all()
        
        if json_output:
            console.print_json(data={
                "type": "patterns",
                "count": len(patterns),
                "entries": [p.to_dict() for p in patterns]
            })
        else:
            console.print(f"\n[bold cyan]创业模式 ({len(patterns)} 个)[/bold cyan]\n")
            
            table = Table()
            table.add_column("ID", style="cyan")
            table.add_column("名称", style="white")
            table.add_column("难度", style="yellow")
            table.add_column("标签", style="dim")
            
            for p in patterns:
                table.add_row(
                    p.id,
                    p.name,
                    p.difficulty,
                    ", ".join(p.tags[:3])
                )
            
            console.print(table)
    
    if entry_type in ("antipatterns", "all"):
        antipattern_lib = AntiPatternLibrary()
        antipatterns = antipattern_lib.list_all()
        
        if json_output:
            console.print_json(data={
                "type": "antipatterns",
                "count": len(antipatterns),
                "entries": [a.to_dict() for a in antipatterns]
            })
        else:
            console.print(f"\n[bold red]反模式 ({len(antipatterns)} 个)[/bold red]\n")
            
            table = Table()
            table.add_column("ID", style="cyan")
            table.add_column("名称", style="white")
            table.add_column("严重性", style="red")
            table.add_column("标签", style="dim")
            
            for a in antipatterns:
                table.add_row(
                    a.id,
                    a.name,
                    a.severity,
                    ", ".join(a.tags[:3])
                )
            
            console.print(table)


# 假设优先级命令
@click.group(name="prioritize")
def hypothesis_prioritize():
    """假设优先级排序。"""
    pass


@hypothesis_prioritize.command("run")
@click.argument("hypotheses_file", type=click.Path(exists=True), required=False)
@click.option("--json", "json_output", is_flag=True, help="JSON 输出")
def run_prioritize(hypotheses_file: Optional[str], json_output: bool):
    """对假设进行优先级排序。
    
    示例：
        aop hypothesis prioritize
        aop hypothesis prioritize hypotheses.json
    """
    from ..hypothesis.prioritizer import HypothesisPrioritizer
    import json
    
    prioritizer = HypothesisPrioritizer()
    
    # 加载假设
    if hypotheses_file:
        with open(hypotheses_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        hypotheses = data.get("hypotheses", [])
    else:
        # 从默认位置加载
        default_path = Path.cwd() / ".aop" / "hypotheses.json"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            hypotheses = data.get("hypotheses", [])
        else:
            console.print("[yellow]未找到假设文件，使用示例数据[/yellow]")
            hypotheses = [
                {"hypothesis_id": "H-001", "statement": "用户愿意为高级功能付费", "type": "business"},
                {"hypothesis_id": "H-002", "statement": "新用户能在5分钟内完成首次操作", "type": "usability"},
                {"hypothesis_id": "H-003", "statement": "系统支持10万并发用户", "type": "technical"},
            ]
    
    # 排序
    scores = prioritizer.prioritize(hypotheses)
    
    if json_output:
        output = {
            "hypotheses": [s.to_dict() for s in scores],
            "explanation": prioritizer.get_ranking_explanation(scores)
        }
        console.print_json(data=output)
        return
    
    # 显示结果
    console.print("\n[bold cyan]假设优先级排序结果[/bold cyan]\n")
    
    table = Table()
    table.add_column("排名", style="cyan")
    table.add_column("ID", style="white")
    table.add_column("陈述", style="white", max_width=40)
    table.add_column("影响", style="green")
    table.add_column("成本", style="yellow")
    table.add_column("不确定性", style="blue")
    table.add_column("优先级", style="magenta")
    
    for score in scores:
        table.add_row(
            str(score.rank),
            score.hypothesis_id,
            score.statement[:40] + "..." if len(score.statement) > 40 else score.statement,
            f"{score.impact_score:.1f}",
            f"{score.cost_score:.1f}",
            f"{score.uncertainty_score:.1f}",
            f"{score.priority_score:.2f}",
        )
    
    console.print(table)
    
    # 显示详细解释
    console.print("\n[bold]排序理由：[/bold]")
    for score in scores[:3]:
        console.print(f"\n[cyan]#{score.rank} {score.hypothesis_id}[/cyan]")
        console.print(f"  {score.reasoning}")


# 验证路径规划命令
@click.group(name="path")
def validation_path():
    """验证路径规划。"""
    pass


@validation_path.command("plan")
@click.argument("hypotheses_file", type=click.Path(exists=True), required=False)
@click.option("--max-days", type=int, default=30, help="最大天数限制")
@click.option("--json", "json_output", is_flag=True, help="JSON 输出")
def plan_validation(hypotheses_file: Optional[str], max_days: int, json_output: bool):
    """规划最小验证路径。
    
    示例：
        aop hypothesis path
        aop hypothesis path hypotheses.json --max-days 14
    """
    from ..validation.path_planner import ValidationPathPlanner
    from ..hypothesis.prioritizer import HypothesisPrioritizer
    import json
    
    planner = ValidationPathPlanner()
    prioritizer = HypothesisPrioritizer()
    
    # 加载假设
    if hypotheses_file:
        with open(hypotheses_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        hypotheses = data.get("hypotheses", [])
    else:
        default_path = Path.cwd() / ".aop" / "hypotheses.json"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            hypotheses = data.get("hypotheses", [])
        else:
            console.print("[yellow]未找到假设文件，使用示例数据[/yellow]")
            hypotheses = [
                {"hypothesis_id": "H-001", "statement": "用户愿意为高级功能付费", "type": "business"},
                {"hypothesis_id": "H-002", "statement": "新用户能在5分钟内完成首次操作", "type": "usability"},
                {"hypothesis_id": "H-003", "statement": "系统支持10万并发用户", "type": "technical"},
            ]
    
    # 先排序
    scores = prioritizer.prioritize(hypotheses)
    
    # 用排序后的假设规划路径
    sorted_hypotheses = [s.raw_hypothesis for s in scores]
    
    constraints = {"max_days": max_days}
    path = planner.plan(sorted_hypotheses, constraints)
    
    if json_output:
        console.print_json(data=path.to_dict())
        return
    
    # 显示结果
    console.print(path.get_summary())
    
    # 显示关键路径
    if path.critical_path:
        console.print("\n[bold yellow]关键路径步骤：[/bold yellow]")
        for step_id in path.critical_path:
            step = next((s for s in path.steps if s.step_id == step_id), None)
            if step:
                console.print(f"  • {step.description}")


# 学习记录命令
@click.group(name="learn")
def learning_cmd():
    """学习记录管理。"""
    pass


@learning_cmd.command("add")
@click.argument("name")
@click.argument("description")
@click.option("--category", "-c", default="technical", help="学习类别")
@click.option("--phase", "-p", default="", help="阶段")
@click.option("--impact", "-i", type=click.Choice(["low", "medium", "high"]), default="medium", help="影响程度")
def add_learning_entry(name: str, description: str, category: str, phase: str, impact: str):
    """添加学习记录。
    
    示例：
        aop learn add "用户反馈" "用户更喜欢简洁界面" --category user --impact high
    """
    store = LearningStore(storage_path=Path.cwd() / ".aop" / "learning")
    
    entry = store.add_learning(
        name=name,
        description=description,
        category=category,
        phase=phase,
        impact=impact,
    )
    
    console.print(f"[green]已添加学习记录：{entry.id}[/green]")
    console.print(f"  名称: {name}")
    console.print(f"  类别: {category}")
    console.print(f"  影响: {impact}")


@learning_cmd.command("summary")
def show_learning_summary():
    """显示学习摘要。"""
    store = LearningStore(storage_path=Path.cwd() / ".aop" / "learning")
    
    summary = store.get_summary()
    console.print(summary)


@learning_cmd.command("export")
@click.option("--output", "-o", default="learnings.md", help="输出文件")
def export_learnings(output: str):
    """导出学习记录为 Markdown。"""
    store = LearningStore(storage_path=Path.cwd() / ".aop" / "learning")
    
    markdown = store.export_to_markdown()
    
    output_path = Path(output)
    output_path.write_text(markdown, encoding="utf-8")
    
    console.print(f"[green]已导出到: {output_path}[/green]")
