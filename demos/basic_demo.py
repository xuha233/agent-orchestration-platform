#!/usr/bin/env python3
"""AOP Basic Demo"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table

from aop.core.types import ComplexityAssessment, HypothesisState
from aop.core.engine import ExecutionEngine
from aop.workflow.hypothesis import HypothesisManager
from aop.workflow.learning import LearningLog
from aop.workflow.team import TeamOrchestrator

console = Console()

def demo_project_assessment():
    """演示项目评估"""
    console.print("\n[bold cyan]=== 1. 项目复杂度评估 ===[/bold cyan]\n")
    
    orchestrator = TeamOrchestrator()
    assessment = orchestrator.assess_project(
        problem_clarity="low",
        data_availability="low", 
        tech_novelty="high",
        business_risk="medium",
    )
    config = orchestrator.get_team_config()
    
    console.print(f"[bold green]项目类型: {config.project_type.value}[/bold green]")
    console.print(f"[bold]推荐团队:[/bold] {', '.join(config.agents)}")
    console.print(f"[bold]迭代周期:[/bold] {config.iteration_length}")
    return orchestrator

def demo_hypothesis():
    """演示假设管理"""
    console.print("\n[bold cyan]=== 2. 假设驱动开发 ===[/bold cyan]\n")
    
    manager = HypothesisManager()
    h1 = manager.create(
        statement="如果我们添加缓存层，那么 API 响应时间将减少 50%",
        validation_method="A/B 测试",
        priority="quick_win",
    )
    console.print(f"[green]创建假设: {h1.hypothesis_id}[/green]")
    console.print(f"  陈述: {h1.statement}")
    return manager

def demo_learning():
    """演示学习捕获"""
    console.print("\n[bold cyan]=== 3. 学习捕获 ===[/bold cyan]\n")
    
    log = LearningLog()
    log.capture(
        phase="探索阶段",
        what_worked=["快速原型验证了核心假设"],
        what_failed=["初期假设过于乐观"],
        insights=["需要更早进行数据评估"],
    )
    console.print(f"[green]捕获了 {len(log.learnings)} 条学习记录[/green]")
    return log

def demo_providers():
    """演示 Agent 检测"""
    console.print("\n[bold cyan]=== 4. Agent 检测 ===[/bold cyan]\n")
    
    engine = ExecutionEngine(providers=["claude", "codex"])
    results = engine.detect_providers()
    
    table = Table(title="Agent 状态")
    table.add_column("Agent")
    table.add_column("状态")
    for pid, p in results.items():
        status = "可用" if p.detected else "不可用"
        table.add_row(pid, status)
    console.print(table)

def main():
    console.print("\n[bold magenta]Agent Orchestration Platform (AOP) Demo[/bold magenta]")
    demo_project_assessment()
    demo_hypothesis()
    demo_learning()
    demo_providers()
    console.print("\n[bold green]Demo 完成![/bold green]")

if __name__ == "__main__":
    main()