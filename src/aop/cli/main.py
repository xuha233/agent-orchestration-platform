"""AOP CLI."""

from __future__ import annotations

from aop import __version__

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

# Valid provider types for --provider option
VALID_PROVIDER_TYPES = ["opencode", "claude-code", "openclaw", "auto"]


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
    """Parse provider-specific timeouts from CLI argument."""
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
            raise ValueError(f"invalid timeout value for provider ''{provider_name}'': {timeout_text.strip()}") from None
        if timeout <= 0:
            raise ValueError(f"timeout must be > 0 for provider ''{provider_name}''")
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
            raise ValueError(f"permissions for provider ''{provider_name}'' must be an object")
        normalized: Dict[str, str] = {}
        for key, value in permissions.items():
            key_name = str(key).strip()
            if not key_name:
                raise ValueError(f"provider ''{provider_name}'' contains empty permission key")
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
    parsed_provider_timeouts = dict(config.policy.provider_timeouts)
    parsed_provider_timeouts.update(_parse_provider_timeouts(provider_timeouts))
    
    parsed_allow_paths = _parse_paths(allow_paths) if allow_paths else list(config.policy.allow_paths)
    
    parsed_provider_permissions = _merge_provider_permissions(
        config.policy.provider_permissions,
        _parse_provider_permissions_json(provider_permissions_json),
    )
    
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


def _get_best_provider() -> str:
    """Get the best available provider (orchestrator type)."""
    try:
        from ..orchestrator import get_best_orchestrator
        return get_best_orchestrator()
    except Exception:
        return "api"


def _resolve_provider(provider: str) -> str:
    """Resolve provider type from CLI argument."""
    if provider == "auto":
        return _get_best_provider()
    return provider


def _create_opencode_config(project_name: str, force: bool = False):
    """创建 OpenCode 配置文件"""
    # opencode.json
    opencode_json = Path("opencode.json")
    if not opencode_json.exists() or force:
        config_content = """{
  "$schema": "https://opencode.ai/config.json",
  "model": "myprovider/qianfan-code-latest",
  "agent": {
    "aop-coach": {
      "description": "AOP 敏捷教练 - 多 Agent 编排、假设驱动开发",
      "mode": "primary",
      "prompt": "{file:./AGENTS.md}",
      "temperature": 0.3
    }
  }
}"""
        opencode_json.write_text(config_content, encoding="utf-8")
        console.print(f"[green]Created {opencode_json}[/green]")
    
    # AGENTS.md
    agents_md = Path("AGENTS.md")
    if not agents_md.exists() or force:
        agents_content = """# AOP 敏捷教练

你是 AOP 敏捷教练，负责协调多 Agent 团队完成复杂开发任务。

## 核心命令
- `aop run <任务>` - 运行任务
- `aop review` - 代码审查
- `aop status` - 查看状态
- `aop init` - 初始化项目
- `aop hypothesis` - 假设管理

## 工作模式
1. **探索** - 分析需求、评估复杂度
2. **构建** - 分解任务、调度子 Agent
3. **验证** - 代码审查、测试验证
4. **学习** - 记录经验、更新记忆

## 子 Agent 类型
- `general` - 通用任务
- `explore` - 探索/研究
- `coder` - 编码
- `reviewer` - 审查

## 调度方式
使用 task 工具启动 sub-agent，完成后自动销毁。

简洁直接，假设驱动，并行执行，持续学习。
"""
        agents_md.write_text(agents_content, encoding="utf-8")
        console.print(f"[green]Created {agents_md}[/green]")
    
    # .opencode/agents/aop-coach.md
    opencode_agents_dir = Path(".opencode/agents")
    opencode_agents_dir.mkdir(parents=True, exist_ok=True)
    aop_coach_md = opencode_agents_dir / "aop-coach.md"
    if not aop_coach_md.exists() or force:
        coach_content = """---
description: AOP 敏捷教练 - 多 Agent 编排、假设驱动开发
mode: primary
temperature: 0.3
---

你是 AOP 敏捷教练，负责协调多 Agent 团队完成复杂开发任务。

## 核心命令
- aop run <任务> - 运行任务
- aop review - 代码审查
- aop status - 查看状态
- aop hypothesis - 假设管理

## 子 Agent 类型
- general - 通用任务
- explore - 探索/研究
- coder - 编码
- reviewer - 审查

简洁直接，假设驱动，并行执行，持续学习。
"""
        aop_coach_md.write_text(coach_content, encoding="utf-8")
        console.print(f"[green]Created {aop_coach_md}[/green]")


def _create_claude_config(project_name: str, force: bool = False):
    """创建 Claude Code 配置文件"""
    claude_dir = Path(".claude")
    claude_dir.mkdir(exist_ok=True)
    
    claude_md = claude_dir / "CLAUDE.md"
    if not claude_md.exists() or force:
        claude_content = """# AOP 敏捷教练

你是 AOP 敏捷教练，负责协调多 Agent 团队完成复杂开发任务。

## 核心命令
- `aop run <任务>` - 运行任务
- `aop review` - 代码审查
- `aop status` - 查看状态
- `aop init` - 初始化项目
- `aop hypothesis` - 假设管理

## 工作模式
1. **探索** - 分析需求、评估复杂度
2. **构建** - 分解任务、调度子 Agent
3. **验证** - 代码审查、测试验证
4. **学习** - 记录经验、更新记忆

## 子 Agent 调度
使用 Claude Code 的 Team 功能：
- TeamCreate 创建团队
- Task 分配任务
- TaskOutput 获取结果

简洁直接，假设驱动，并行执行，持续学习。

## ⛔ 核心约束

**主会话只能由用户关闭。**

禁止操作（除非用户明确说"关闭"、"结束"、"退出"）：
- ❌ Shutdown / TeamDelete / SendMessage(shutdown_request)
"""
        claude_md.write_text(claude_content, encoding="utf-8")
        console.print(f"[green]Created {claude_md}[/green]")


def _show_next_steps():
    """Show next steps after init."""
    steps = """
[bold cyan]Next Steps:[/bold cyan]

  1. Edit [green].aop.yaml[/green] to configure your providers and settings
  2. Add your hypotheses to [green]hypotheses.md[/green]
  3. Run [blue]aop doctor[/blue] to check provider availability
  4. Run [blue]aop review -p "your prompt"[/blue] to start a review

[dim]Documentation: https://github.com/openclaw/aop[/dim]
"""
    console.print(steps)


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="aop")
@click.option("--port", "-p", default=8501, help="Dashboard port (default: 8501)")
@click.option("--host", "-h", default="localhost", help="Dashboard host (default: localhost)")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground and show logs in current terminal")
@click.pass_context
def cli(ctx, port: int, host: str, no_browser: bool, foreground: bool):
    """Agent Orchestration Platform."""
    if ctx.invoked_subcommand is None:
        _start_dashboard(port=port, host=host, open_browser=not no_browser, foreground=foreground)


def _start_dashboard(port: int, host: str, open_browser: bool, foreground: bool = False):
    """Start the AOP Dashboard."""
    try:
        from ..dashboard import run_dashboard



        
        console.print(Panel.fit(
            f"[bold cyan]AOP Dashboard[/bold cyan]\n\n"
            f"Starting at: [link]http://{host}:{port}[/link]\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            title="AOP - Agent Orchestration Platform",
            border_style="blue",
        ))
        
        run_dashboard(port=port, host=host, foreground=foreground, open_browser=open_browser)
        
    except ImportError:
        console.print("[bold red]Error: streamlit is not installed[/bold red]")
        console.print("\nInstall with:")
        console.print("  [cyan]pip install streamlit[/cyan]")
        sys.exit(EXIT_ERROR)
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped[/dim]")
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        console.print(f"[bold red]Error starting dashboard: {e}[/bold red]")
        sys.exit(EXIT_ERROR)


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--fix", "show_fix", is_flag=True, help="Show fix suggestions for issues")
@click.option("--all", "show_all", is_flag=True, help="Show all providers including orchestrators")
def doctor(json_output: bool, show_fix: bool, show_all: bool):
    """Check provider availability and configuration."""
    engine = ExecutionEngine()
    results = engine.detect_providers()
    
    provider_info = {}
    from ..core.adapter import get_adapter_registry
    registry = get_adapter_registry()
    
    for pid, presence in results.items():
        adapter = registry.get(pid)
        info = {
            "detected": presence.detected,
            "version": None,
            "auth_status": None,
            "fix_suggestion": None,
            "type": "adapter"
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
    
    orchestrator_info = {}
    try:
        from ..orchestrator import discover_orchestrators, get_best_orchestrator, ORCHESTRATOR_REGISTRY
        discovered = discover_orchestrators()
        
        for orch_type in ORCHESTRATOR_REGISTRY.keys():
            if orch_type == "api":
                orchestrator_info[orch_type] = {
                    "detected": True,
                    "version": "-",
                    "auth_status": "config required",
                    "fix_suggestion": "Configure LLMClient for API mode",
                    "type": "orchestrator"
                }
                continue
            
            presence = discovered.get(orch_type)
            if presence:
                orchestrator_info[orch_type] = {
                    "detected": presence.detected and presence.auth_ok,
                    "version": presence.version,
                    "auth_status": "OK" if presence.auth_ok else "Failed",
                    "fix_suggestion": None if presence.auth_ok else f"Run '{orch_type} auth' or check configuration",
                    "type": "orchestrator"
                }
            else:
                orchestrator_info[orch_type] = {
                    "detected": False,
                    "version": None,
                    "auth_status": None,
                    "fix_suggestion": f"Install {orch_type}",
                    "type": "orchestrator"
                }
    except Exception:
        pass
    
    recommended_provider = None
    all_providers = {**provider_info, **orchestrator_info}
    available_providers = [p for p, info in all_providers.items() if info["detected"]]
    
    priority_order = ["claude-code", "opencode", "openclaw", "claude", "codex"]
    for p in priority_order:
        if p in available_providers:
            recommended_provider = p
            break
    
    if json_output:
        output = {
            "providers": provider_info,
            "orchestrators": orchestrator_info,
            "all_available": all(p["detected"] for p in provider_info.values()),
            "available_count": sum(1 for p in provider_info.values() if p["detected"]),
            "total_count": len(provider_info),
            "recommended_provider": recommended_provider,
            "available_providers": available_providers
        }
        console.print_json(data=output)
        return
    
    table = Table(title="Provider Status (Adapters)")
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
    
    orch_table = Table(title="Provider Status (Orchestrators/Agents)")
    orch_table.add_column("Provider")
    orch_table.add_column("Status")
    orch_table.add_column("Version")
    orch_table.add_column("Auth")
    
    for orch_type, info in orchestrator_info.items():
        status = "[green]Available[/green]" if info["detected"] else "[red]Not found[/red]"
        version = info["version"] or "-"
        auth = info["auth_status"] or "-"
        orch_table.add_row(orch_type, status, version, auth)
    
    console.print(orch_table)
    
    # acpx 检测
    acpx_installed = False
    acpx_version = None
    try:
        import subprocess
        result = subprocess.run(["acpx", "--version"], capture_output=True, text=True, timeout=5, shell=True)
        if result.returncode == 0:
            acpx_installed = True
            acpx_version = result.stdout.strip().split()[-1] if result.stdout.strip() else None
    except Exception:
        pass
    
    acpx_table = Table(title="ACP Runtime")
    acpx_table.add_column("Component")
    acpx_table.add_column("Status")
    acpx_table.add_column("Version")
    if acpx_installed:
        acpx_table.add_row("acpx", "[green]Installed[/green]", acpx_version or "-")
    else:
        acpx_table.add_row("acpx", "[yellow]Not installed[/yellow]", "-")
    console.print(acpx_table)
    
    if not acpx_installed:
        console.print("\n[yellow]💡 acpx 未安装，ACP 调度功能不可用[/yellow]")
        console.print("   安装: [cyan]npm install -g acpx[/cyan]")
    
    if recommended_provider:
        console.print(f"\n[bold cyan]Recommended provider:[/] [green]{recommended_provider}[/green]")
    else:
        console.print(f"\n[yellow]No recommended provider available[/yellow]")
        console.print("Install one of: claude-code, opencode, openclaw")
    
    if show_fix:
        issues = [(pid, info) for pid, info in all_providers.items() if not info["detected"]]
        if issues:
            console.print("\n[bold yellow]Fix Suggestions:[/bold yellow]")
            for pid, info in issues:
                if info["fix_suggestion"]:
                    console.print(f"  * {pid}: {info['fix_suggestion']}")
    
    available_count = sum(1 for p in provider_info.values() if p["detected"])
    if available_count == 0:
        sys.exit(EXIT_PROVIDER_UNAVAILABLE)
    elif available_count < len(provider_info):
        sys.exit(EXIT_ERROR)


# Common review/run options
def _add_common_execution_options(f):
    """Add common execution options to a command."""
    f = click.option("--prompt", "-p", required=True, help="The prompt/question for multi-agent review")(f)
    f = click.option("--providers", "-P", default=None, help="Comma-separated provider list")(f)
    f = click.option("--repo", "-r", default=".", help="Repository root path")(f)
    f = click.option("--target-paths", default=".", help="Comma-separated task scope paths")(f)
    f = click.option("--task-id", default="", help="Optional stable task id")(f)
    f = click.option("--timeout", "-t", default=600, help="Timeout in seconds for each provider")(f)
    f = click.option("--stall-timeout", type=int, default=DEFAULT_POLICY.stall_timeout_seconds, help="Idle timeout")(f)
    f = click.option("--review-hard-timeout", type=int, default=DEFAULT_POLICY.review_hard_timeout_seconds, help="Hard deadline")(f)
    f = click.option("--poll-interval", type=float, default=DEFAULT_POLICY.poll_interval_seconds, help="Polling interval")(f)
    f = click.option("--max-provider-parallelism", type=int, default=DEFAULT_POLICY.max_provider_parallelism, help="Max parallel providers")(f)
    f = click.option("--provider-timeouts", default="", help="Provider-specific timeouts")(f)
    f = click.option("--format", "-f", "output_format", default="report", type=click.Choice(["report", "json", "summary", "sarif", "markdown-pr"]), help="Output format")(f)
    f = click.option("--result-mode", type=click.Choice(["stdout", "artifact", "both"]), default="stdout", help="Result mode")(f)
    f = click.option("--artifact-base", default="reports/review", help="Artifact base directory")(f)
    f = click.option("--include-token-usage", is_flag=True, help="Extract token usage")(f)
    f = click.option("--save-artifacts", is_flag=True, help="Force artifact writes")(f)
    f = click.option("--json", "json_output", is_flag=True, help="JSON output")(f)
    f = click.option("--synthesize", is_flag=True, help="Run synthesis pass")(f)
    f = click.option("--synth-provider", default="", help="Synthesis provider")(f)
    f = click.option("--allow-paths", default=".", help="Allowed paths")(f)
    f = click.option("--enforcement-mode", type=click.Choice(["strict", "best_effort"]), default=DEFAULT_POLICY.enforcement_mode, help="Enforcement mode")(f)
    f = click.option("--provider-permissions-json", default="", help="Provider permissions JSON")(f)
    f = click.option("--strict-contract", is_flag=True, help="Enforce strict findings contract")(f)
    f = click.option("--session", "-s", default="", help="Session ID to resume (provider-specific format)")(f)
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
    session: str,
):
    """Run multi-agent code review."""
    config = load_config()
    provider_list = _parse_providers(providers or ",".join(config.providers))
    
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
    
    synth_provider_name = synth_provider.strip() if synth_provider else ""
    do_synthesize = bool(synthesize or synth_provider_name)
    if synth_provider_name and synth_provider_name not in provider_list:
        console.print("[red]Error: --synth-provider must be one of selected providers[/red]")
        sys.exit(EXIT_ERROR)
    
    console.print(Panel(f"[bold]Running review with:[/] {', '.join(provider_list)}"))
    
    engine = ReviewEngine(providers=provider_list, default_timeout=timeout)
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
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
    
    effective_result_mode = result_mode
    if save_artifacts and effective_result_mode == "stdout":
        effective_result_mode = "both"
    
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
    
    if output_format == "json" or json_output:
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
    else:
        console.print(format_report(result))
    
    if result.decision == "FAIL":
        sys.exit(EXIT_ERROR)
    if result.decision == "INCONCLUSIVE":
        sys.exit(EXIT_INCONCLUSIVE)
    sys.exit(EXIT_SUCCESS)


@cli.command("run")
@_add_common_execution_options
@click.option(
    "--provider",
    type=click.Choice(VALID_PROVIDER_TYPES),
    default="auto",
    help="Orchestrator/agent provider to use (opencode, claude-code, openclaw, auto). Default: auto"
)
@click.option(
    "--parallel",
    is_flag=True,
    help="Enable multi-agent parallel execution (use with --agents)"
)
@click.option(
    "--agents",
    default="",
    help="Comma-separated agent list for parallel execution (e.g., reviewer,tester,implementer)"
)
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
    provider: str,
    parallel: bool,
    agents: str,
    session: str,
):
    """Run general multi-provider task execution.
    
    Provider Selection:
      --provider opencode      Use OpenCode as orchestrator
      --provider claude-code   Use Claude Code as orchestrator
      --provider openclaw      Use OpenClaw as orchestrator
      --provider auto          Auto-select best available (default)
    
    Parallel Execution:
      --parallel --agents reviewer,tester   Run multiple agents in parallel
    """
    actual_provider = _resolve_provider(provider)
    agent_list = [a.strip() for a in agents.split(",") if a.strip()] if agents else []
    
    if parallel and not agent_list:
        console.print("[yellow]Warning: --parallel requires --agents. Using default agents.[/yellow]")
        agent_list = ["reviewer", "implementer"]
    
    config = load_config()
    provider_list = _parse_providers(providers or ",".join(config.providers))
    
    policy = _resolve_policy(
        config=config,
        stall_timeout=stall_timeout,
        review_hard_timeout=review_hard_timeout,
        poll_interval=poll_interval,
        provider_timeouts=provider_timeouts,
        allow_paths=allow_paths,
        enforcement_mode=enforcement_mode,
        strict_contract=False,
        max_provider_parallelism=max_provider_parallelism,
        provider_permissions_json=provider_permissions_json,
    )
    
    synth_provider_name = synth_provider.strip() if synth_provider else ""
    do_synthesize = bool(synthesize or synth_provider_name)
    if synth_provider_name and synth_provider_name not in provider_list:
        console.print("[red]Error: --synth-provider must be one of selected providers[/red]")
        sys.exit(EXIT_ERROR)
    
    if output_format in ("sarif", "markdown-pr"):
        console.print(f"[red]Error: --format {output_format} is supported only for review command[/red]")
        sys.exit(EXIT_ERROR)
    
    if parallel:
        console.print(Panel(
            f"[bold]Running parallel task with:[/]\n"
            f"  Provider: {actual_provider}\n"
            f"  Agents: {', '.join(agent_list)}\n"
            f"  Adapters: {', '.join(provider_list)}"
        ))
    else:
        console.print(Panel(
            f"[bold]Running task with:[/]\n"
            f"  Provider: {actual_provider}\n"
            f"  Adapters: {', '.join(provider_list)}"
        ))
    
    if provider != "auto" or parallel:
        try:
            from ..orchestrator import create_orchestrator
            from ..primary import get_registry
            
            registry = get_registry()
            agent = registry.get(actual_provider)
            
            if agent and not agent.is_available():
                console.print(f"[yellow]Warning: Provider '{actual_provider}' is not available. Falling back to auto.[/yellow]")
                actual_provider = _get_best_provider()
            
            if parallel:
                result = _run_parallel_execution(
                    prompt=prompt,
                    provider=actual_provider,
                    agents=agent_list,
                    repo_root=repo,
                    target_paths=_parse_paths(target_paths),
                    timeout=timeout,
                )
            else:
                orchestrator = create_orchestrator(actual_provider)
                result = _run_with_orchestrator(
                    orchestrator=orchestrator,
                    prompt=prompt,
                    repo_root=repo,
                    target_paths=_parse_paths(target_paths),
                    timeout=timeout,
                    session_id=session,
                )
                
        except ImportError as e:
            console.print(f"[yellow]Orchestrator module not available: {e}. Using adapter mode.[/yellow]")
            result = _run_with_adapters(
                prompt=prompt,
                provider_list=provider_list,
                repo_root=repo,
                target_paths=_parse_paths(target_paths),
                task_id=task_id,
                timeout=timeout,
                include_token_usage=include_token_usage,
                synthesize=do_synthesize,
                synthesis_provider=synth_provider_name,
            )
    else:
        engine = ExecutionEngine(providers=provider_list, default_timeout=timeout)
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
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
    
    effective_result_mode = result_mode
    if save_artifacts and effective_result_mode == "stdout":
        effective_result_mode = "both"
    
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
            "errors": result.errors,
            "provider_used": actual_provider,
        }
        if parallel:
            output["parallel"] = True
            output["agents"] = agent_list
        if result.token_usage_summary is not None:
            output["token_usage_summary"] = result.token_usage_summary
        if result.synthesis is not None:
            output["synthesis"] = result.synthesis
        console.print_json(data=output)
    elif output_format == "summary":
        console.print(f"\n[bold]Task:[/] {result.task_id}")
        console.print(f"[bold]Provider:[/] {actual_provider}")
        console.print(f"[bold]Duration:[/] {result.duration_seconds:.2f}s")
        console.print(f"[bold]Status:[/] {'[green]Success[/green]' if result.success else '[red]Failed[/red]'}")
    else:
        console.print(f"\n[bold]Task:[/] {result.task_id}")
        console.print(f"[bold]Provider:[/] {actual_provider}")
        if parallel:
            console.print(f"[bold]Agents:[/] {', '.join(agent_list)}")
        console.print(f"[bold]Duration:[/] {result.duration_seconds:.2f}s")
        console.print(f"[bold]Status:[/] {'[green]Success[/green]' if result.success else '[red]Failed[/red]'}")
        
        if result.provider_results:
            console.print("\n[bold]Provider Results:[/bold]")
            for provider_name, details in sorted(result.provider_results.items()):
                if hasattr(details, 'success'):
                    success = details.success
                else:
                    success = details.get("success", False)
                status = "[green]Success[/green]" if success else "[red]Failed[/red]"
                console.print(f"  {provider_name}: {status}")
    
    if result.errors:
        console.print("\n[yellow]Warnings:[/yellow]")
        for err in result.errors:
            console.print(f"  * {err}")
    
    sys.exit(EXIT_SUCCESS if result.success else EXIT_ERROR)


def _run_with_orchestrator(orchestrator, prompt: str, repo_root: str, target_paths: List[str], timeout: int, session_id: str = ""):
    """Run task using an orchestrator provider.
    
    Args:
        orchestrator: Orchestrator 实例
        prompt: 任务提示
        repo_root: 仓库根目录
        target_paths: 目标路径
        timeout: 超时时间
        session_id: 会话 ID，用于恢复之前的会话
    """
    from ..core.types import TaskResult
    import time
    
    start_time = time.time()
    
    try:
        # 传递 session_id 用于会话恢复
        response = orchestrator.execute(
            prompt=prompt,
            cwd=repo_root,
            timeout=timeout,
            session_id=session_id if session_id else None
        )
        
        duration = time.time() - start_time
        task_id = f"task-{int(start_time)}"
        
        return TaskResult(
            task_id=task_id,
            decision="PASS" if response.success else "FAIL",
            terminal_state="completed",
            success=response.success,
            duration_seconds=duration,
            provider_results={
                orchestrator.__class__.__name__: {
                    "success": response.success,
                    "output": response.content,
                }
            },
            errors=[response.error] if response.error else [],
            findings=[],
        )
    except Exception as e:
        duration = time.time() - start_time
        return TaskResult(
            task_id=f"task-{int(start_time)}",
            decision="FAIL",
            terminal_state="error",
            success=False,
            duration_seconds=duration,
            provider_results={},
            errors=[str(e)],
            findings=[],
        )


def _run_parallel_execution(prompt: str, provider: str, agents: List[str], repo_root: str, target_paths: List[str], timeout: int):
    """Run parallel execution with multiple agents."""
    from ..core.types import TaskResult
    import time
    import concurrent.futures
    
    start_time = time.time()
    task_id = f"parallel-{int(start_time)}"
    
    console.print(f"[dim]Starting parallel execution with {len(agents)} agents...[/dim]")
    
    results = {}
    errors = []
    
    try:
        from ..orchestrator import create_orchestrator
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as executor:
            futures = {}
            for agent_name in agents:
                orch = create_orchestrator(provider)
                future = executor.submit(
                    orch.execute,
                    prompt=f"[{agent_name}] {prompt}",
                    cwd=repo_root,
                    timeout=timeout,
                )
                futures[future] = agent_name
            
            for future in concurrent.futures.as_completed(futures):
                agent_name = futures[future]
                try:
                    response = future.result()
                    results[agent_name] = {
                        "success": response.success,
                        "output": response.content[:500] if response.content else None,
                    }
                except Exception as e:
                    results[agent_name] = {
                        "success": False,
                        "error": str(e),
                    }
                    errors.append(f"{agent_name}: {str(e)}")
                    
    except Exception as e:
        errors.append(f"Parallel execution error: {str(e)}")
    
    duration = time.time() - start_time
    overall_success = all(r.get("success", False) for r in results.values())
    
    return TaskResult(
        task_id=task_id,
        decision="PASS" if overall_success else "FAIL",
        terminal_state="completed",
        success=overall_success,
        duration_seconds=duration,
        provider_results=results,
        errors=errors,
        findings=[],
    )


def _run_with_adapters(prompt: str, provider_list: List[str], repo_root: str, target_paths: List[str], 
                        task_id: str, timeout: int, include_token_usage: bool, synthesize: bool, synthesis_provider: str):
    """Run task using adapter-based execution (fallback)."""
    engine = ExecutionEngine(providers=provider_list, default_timeout=timeout)
    
    return engine.run(
        prompt,
        repo_root=repo_root,
        target_paths=target_paths,
        task_id=task_id or None,
        include_token_usage=include_token_usage,
        synthesize=synthesize,
        synthesis_provider=synthesis_provider or None,
    )


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
    return format_sarif(result)


def _format_markdown_pr(result) -> str:
    """Format result as Markdown PR comment."""
    return format_markdown_pr(result)


@cli.command()
@click.option("--name", "-n", help="Project name")
@click.option("--providers", "-P", help="Comma-separated providers (default: claude,codex)")
@click.option("--project-type", "-t", type=click.Choice(["exploratory", "optimization", "transformation", "compliance_sensitive"]), default="transformation", help="Project type")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
def init(name: Optional[str], providers: Optional[str], project_type: str, force: bool):
    """Initialize a new AOP project with config file."""
    config_path = Path(".aop.yaml")
    
    if config_path.exists() and not force:
        console.print("[red]Error: .aop.yaml already exists. Use --force to overwrite.[/red]")
        sys.exit(EXIT_ERROR)
    
    if not name:
        name = click.prompt("Project name", default=Path.cwd().name)
    
    provider_list = None
    if not providers:
        providers_input = click.prompt("Providers (comma-separated)", default="claude,codex")
        provider_list = [p.strip() for p in providers_input.split(",")]
    else:
        provider_list = [p.strip() for p in providers.split(",")]
    
    config = AOPConfig(project_type=project_type, providers=provider_list)
    
    try:
        config.to_yaml(config_path)
        console.print(f"[green]Created {config_path}[/green]")
        
        runs_dir = Path("runs")
        runs_dir.mkdir(exist_ok=True)
        console.print(f"[green]Created {runs_dir}/ directory[/green]")
        
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

---

Run `aop hypothesis create "your statement"` to add new hypotheses.
"""
            hypotheses_path.write_text(hypotheses_content, encoding="utf-8")
            console.print(f"[green]Created {hypotheses_path} template[/green]")
        
        # 创建 OpenCode 配置文件
        _create_opencode_config(name, force)
        
        # 创建 Claude Code 配置文件
        _create_claude_config(name, force)
        
        console.print(f"\n[bold green]Project '{name}' initialized![/bold green]")
        _show_next_steps()
        
        sys.exit(EXIT_SUCCESS)
        
    except Exception as e:
        console.print(f"[red]Failed to initialize project: {e}[/red]")
        sys.exit(EXIT_CONFIG_NOT_FOUND)


@cli.group()
def hypothesis():
    """Manage hypotheses."""
    pass


@hypothesis.command("create")
@click.argument("statement")
@click.option("--priority", "-p", type=click.Choice(["quick_win", "deep_dive"]), default="quick_win", help="Hypothesis priority")
def create_hypothesis(statement: str, priority: str):
    """Create a hypothesis."""
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
@click.option("--state", "-s", type=click.Choice(["pending", "validated", "refuted", "inconclusive"]), default=None, help="Filter by state")
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
@click.option("--state", "-s", type=click.Choice(["pending", "validated", "refuted", "inconclusive"]), required=True, help="New state")
def update_hypothesis(hypothesis_id, state):
    """Update hypothesis status."""
    from ..core.types import HypothesisState
    default_path = Path.cwd() / ".aop" / "hypotheses.json"
    manager = HypothesisManager(storage_path=default_path) if default_path.exists() else HypothesisManager()
    
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



@hypothesis.command("prioritize")
@click.argument("hypotheses_file", type=click.Path(exists=True), required=False)
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def prioritize_hypotheses(hypotheses_file: Optional[str], json_output: bool):
    """Prioritize hypotheses by impact, cost, and uncertainty.
    
    Example:
        aop hypothesis prioritize
        aop hypothesis prioritize hypotheses.json
    """
    from ..hypothesis.prioritizer import HypothesisPrioritizer
    
    prioritizer = HypothesisPrioritizer()
    
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
            console.print("[yellow]No hypotheses file found, using sample data[/yellow]")
            hypotheses = [
                {"hypothesis_id": "H-001", "statement": "Users will pay for premium features", "type": "business"},
                {"hypothesis_id": "H-002", "statement": "New users can complete first action in 5 minutes", "type": "usability"},
                {"hypothesis_id": "H-003", "statement": "System supports 100K concurrent users", "type": "technical"},
            ]
    
    scores = prioritizer.prioritize(hypotheses)
    
    if json_output:
        output = {
            "hypotheses": [s.to_dict() for s in scores],
            "explanation": prioritizer.get_ranking_explanation(scores)
        }
        console.print_json(data=output)
        return
    
    console.print("\n[bold cyan]Hypothesis Priority Ranking[/bold cyan]\n")
    
    table = Table()
    table.add_column("Rank", style="cyan")
    table.add_column("ID", style="white")
    table.add_column("Statement", style="white", max_width=40)
    table.add_column("Impact", style="green")
    table.add_column("Cost", style="yellow")
    table.add_column("Uncertainty", style="blue")
    table.add_column("Priority", style="magenta")
    
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
    
    console.print("\n[bold]Reasoning:[/bold]")
    for score in scores[:3]:
        console.print(f"\n[cyan]#{score.rank} {score.hypothesis_id}[/cyan]")
        console.print(f"  {score.reasoning}")


@hypothesis.command("path")
@click.argument("hypotheses_file", type=click.Path(exists=True), required=False)
@click.option("--max-days", type=int, default=30, help="Maximum days constraint")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def plan_validation_path(hypotheses_file: Optional[str], max_days: int, json_output: bool):
    """Plan minimal validation path for hypotheses.
    
    Example:
        aop hypothesis path
        aop hypothesis path hypotheses.json --max-days 14
    """
    from ..validation.path_planner import ValidationPathPlanner
    from ..hypothesis.prioritizer import HypothesisPrioritizer
    
    planner = ValidationPathPlanner()
    prioritizer = HypothesisPrioritizer()
    
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
            console.print("[yellow]No hypotheses file found, using sample data[/yellow]")
            hypotheses = [
                {"hypothesis_id": "H-001", "statement": "Users will pay for premium features", "type": "business"},
                {"hypothesis_id": "H-002", "statement": "New users can complete first action in 5 minutes", "type": "usability"},
                {"hypothesis_id": "H-003", "statement": "System supports 100K concurrent users", "type": "technical"},
            ]
    
    scores = prioritizer.prioritize(hypotheses)
    sorted_hypotheses = [s.raw_hypothesis for s in scores]
    
    constraints = {"max_days": max_days}
    path = planner.plan(sorted_hypotheses, constraints)
    
    if json_output:
        console.print_json(data=path.to_dict())
        return
    
    console.print(path.get_summary())


@cli.group()
def knowledge():
    """Startup knowledge base (patterns and antipatterns)."""
    pass


@knowledge.command("search")
@click.argument("query")
@click.option("--tags", "-t", help="Tag filter (comma-separated)")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def search_patterns(query: str, tags: Optional[str], json_output: bool):
    """Search startup patterns.
    
    Example:
        aop knowledge search "demand validation"
        aop knowledge search "mvp" --tags validation,low-cost
    """
    from ..knowledge.patterns import StartupPatternLibrary
    
    library = StartupPatternLibrary()
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    patterns = library.search_patterns(query, tag_list)
    
    if not patterns:
        console.print(f"[yellow]No patterns found for: {query}[/yellow]")
        return
    
    if json_output:
        output = {
            "query": query,
            "count": len(patterns),
            "patterns": [p.to_dict() for p in patterns]
        }
        console.print_json(data=output)
        return
    
    console.print(f"\n[bold]Found {len(patterns)} patterns:[/bold]\n")
    
    for i, pattern in enumerate(patterns, 1):
        console.print(f"[cyan]{i}. {pattern.name}[/cyan]")
        console.print(f"   {pattern.description}")
        console.print(f"   [dim]When: {', '.join(pattern.when_to_use[:3])}[/dim]")
        if pattern.examples:
            console.print(f"   [dim]Examples: {', '.join(pattern.examples[:2])}[/dim]")
        console.print()


@knowledge.command("suggest")
@click.option("--stage", "-s", help="Project stage (idea/validation/growth/scale)")
@click.option("--type", "-t", "project_type", help="Project type (b2b/b2c/marketplace)")
@click.option("--low-budget", is_flag=True, help="Budget constrained")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def suggest_patterns(stage: Optional[str], project_type: Optional[str], low_budget: bool, json_output: bool):
    """Suggest patterns based on project context.
    
    Example:
        aop knowledge suggest --stage idea --low-budget
        aop knowledge suggest --type b2b --stage validation
    """
    from ..knowledge.patterns import StartupPatternLibrary
    
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
        console.print("[yellow]No patterns suggested for current conditions[/yellow]")
        return
    
    if json_output:
        output = {
            "context": context,
            "count": len(patterns),
            "patterns": [p.to_dict() for p in patterns]
        }
        console.print_json(data=output)
        return
    
    console.print(f"\n[bold]Suggested {len(patterns)} patterns:[/bold]\n")
    
    for i, pattern in enumerate(patterns, 1):
        success_rate = f"{pattern.success_rate*100:.0f}%" if pattern.success_rate else "N/A"
        console.print(f"[cyan]{i}. {pattern.name}[/cyan] (Success: {success_rate})")
        console.print(f"   {pattern.description}")
        console.print(f"   [dim]Difficulty: {pattern.difficulty} | Time: {pattern.time_to_value}[/dim]")
        console.print()


@knowledge.command("antipatterns")
@click.option("--decisions", "-d", multiple=True, help="Decisions made")
@click.option("--behaviors", "-b", multiple=True, help="Current behaviors")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def check_antipatterns(decisions: tuple, behaviors: tuple, json_output: bool):
    """Check for antipatterns in current project.
    
    Example:
        aop knowledge antipatterns --decisions "build full product first" --behaviors "haven't talked to users"
    """
    from ..knowledge.anti_patterns import AntiPatternLibrary
    
    library = AntiPatternLibrary()
    
    context = {
        "decisions": list(decisions),
        "behaviors": list(behaviors),
    }
    
    warnings = library.check_for_antipatterns(context)
    
    if not warnings:
        console.print("[green]No obvious antipatterns detected[/green]")
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
    
    console.print(f"\n[bold]Detected {len(warnings)} potential antipatterns:[/bold]\n")
    
    for warning in warnings:
        color = severity_colors.get(warning.risk_level, "white")
        
        console.print(f"[{color}]⚠ {warning.anti_pattern.name}[/{color}]")
        console.print(f"   Risk: [{color}]{warning.risk_level.upper()}[/{color}]")
        console.print(f"   {warning.anti_pattern.description}")
        
        if warning.matched_symptoms:
            console.print(f"   [dim]Matched: {', '.join(warning.matched_symptoms[:3])}[/dim]")
        
        console.print(f"   [green]Suggestion: {warning.recommendation}[/green]")
        console.print()


@knowledge.command("list")
@click.option("--type", "-t", "entry_type", type=click.Choice(["patterns", "antipatterns", "all"]), default="all", help="Entry type to list")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def list_knowledge(entry_type: str, json_output: bool):
    """List all knowledge base entries."""
    if entry_type in ("patterns", "all"):
        from ..knowledge.patterns import StartupPatternLibrary
        pattern_lib = StartupPatternLibrary()
        patterns = pattern_lib.list_all()
        
        if json_output:
            console.print_json(data={
                "type": "patterns",
                "count": len(patterns),
                "entries": [p.to_dict() for p in patterns]
            })
        else:
            console.print(f"\n[bold cyan]Startup Patterns ({len(patterns)})[/bold cyan]\n")
            
            table = Table()
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Difficulty", style="yellow")
            table.add_column("Tags", style="dim")
            
            for p in patterns:
                table.add_row(
                    p.id,
                    p.name,
                    p.difficulty,
                    ", ".join(p.tags[:3])
                )
            
            console.print(table)
    
    if entry_type in ("antipatterns", "all"):
        from ..knowledge.anti_patterns import AntiPatternLibrary
        antipattern_lib = AntiPatternLibrary()
        antipatterns = antipattern_lib.list_all()
        
        if json_output:
            console.print_json(data={
                "type": "antipatterns",
                "count": len(antipatterns),
                "entries": [a.to_dict() for a in antipatterns]
            })
        else:
            console.print(f"\n[bold red]Antipatterns ({len(antipatterns)})[/bold red]\n")
            
            table = Table()
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Severity", style="red")
            table.add_column("Tags", style="dim")
            
            for a in antipatterns:
                table.add_row(
                    a.id,
                    a.name,
                    a.severity,
                    ", ".join(a.tags[:3])
                )
            
            console.print(table)

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
    
    log.capture(phase=phase, what_worked=list(worked), what_failed=list(failed), insights=list(insight))
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
        table.add_row(l.phase, str(len(l.what_worked)), str(len(l.what_failed)), str(len(l.insights)))
    
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
    """Project management."""
    pass


@project.command("assess")
@click.option("--problem-clarity", "-p", default="medium", type=click.Choice(["low", "medium", "high"]), help="Problem clarity level")
@click.option("--data-availability", "-d", default="medium", type=click.Choice(["low", "medium", "high"]), help="Data availability level")
@click.option("--tech-novelty", "-t", default="medium", type=click.Choice(["low", "medium", "high"]), help="Technical novelty level")
@click.option("--business-risk", "-b", default="medium", type=click.Choice(["low", "medium", "high"]), help="Business risk level")
def assess(problem_clarity: str, data_availability: str, tech_novelty: str, business_risk: str):
    """Assess project complexity."""
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
@click.option("--port", "-p", default=8501, help="Port to run dashboard on")
@click.option("--host", "-h", default="localhost", help="Host to bind")
@click.option("--open-browser", "-o", is_flag=True, help="Open browser automatically")
def dashboard(port: int, host: str, open_browser: bool):
    """Start the AOP Dashboard web UI."""
    try:
        from ..dashboard import run_dashboard

        
        console.print(Panel.fit(
            f"[bold cyan]AOP Dashboard[/bold cyan]\n\n"
            f"Starting at: [link]http://{host}:{port}[/link]\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            title="Dashboard",
            border_style="blue",
        ))
        
        run_dashboard(port=port, host=host, open_browser=open_browser)
        
    except ImportError:
        console.print("[bold red]Error: streamlit is not installed[/bold red]")
        console.print("\nInstall with:")
        console.print("  [cyan]pip install streamlit[/cyan]")
        sys.exit(EXIT_ERROR)
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped[/dim]")
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        console.print(f"[bold red]Error starting dashboard: {e}[/bold red]")
        sys.exit(EXIT_ERROR)




@cli.group()
def state():
    """Manage STATE.md cross-session memory."""
    pass


@state.command("show")
def show_state():
    """Show current state."""
    from ..state import StateManager
    
    manager = StateManager(project_path=Path.cwd())
    state_data = manager.load()
    
    state_text = (
        f"[bold cyan]STATE.md[/bold cyan]\n\n"
        f"[bold]Session:[/bold] {state_data.session_id}\n"
        f"[bold]Updated:[/bold] {state_data.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"[bold]Current Task:[/bold] {state_data.current_task}\n"
        f"[bold]Last Action:[/bold] {state_data.last_action}\n"
        f"[bold]Next Step:[/bold] {state_data.next_step}"
    )
    
    console.print(Panel.fit(
        state_text,
        title="Current State",
        border_style="blue",
    ))
    
    # Active blockers
    active_blockers = manager.get_active_blockers()
    if active_blockers:
        console.print(f"\n[bold red]Blockers ({len(active_blockers)}):[/bold red]")
        for b in active_blockers:
            console.print(f"  - {b['blocker']}")
    
    # Active hypotheses
    active_hypotheses = manager.get_active_hypotheses()
    if active_hypotheses:
        console.print(f"\n[bold yellow]Active Hypotheses ({len(active_hypotheses)}):[/bold yellow]")
        for h in active_hypotheses[:5]:
            stmt = h['statement'][:50] + "..." if len(h['statement']) > 50 else h['statement']
            console.print(f"  - [{h['hypothesis_id']}] {stmt}")
    
    # Recent decisions
    if state_data.decisions:
        console.print(f"\n[bold green]Recent Decisions ({len(state_data.decisions)}):[/bold green]")
        for d in state_data.decisions[-3:]:
            console.print(f"  - [{d['date']}] {d['decision']}")


@state.command("task")
@click.argument("task")
@click.option("--action", "-a", default="", help="Last action")
@click.option("--next", "-n", default="TBD", help="Next step")
def update_task(task: str, action: str, next: str):
    """Update current task."""
    from ..state import StateManager
    
    manager = StateManager(project_path=Path.cwd())
    manager.update_task(task=task, action=action, next_step=next)
    
    console.print(f"[green]Updated task:[/green] {task}")
    console.print(f"  Last action: {action}")
    console.print(f"  Next step: {next}")


@state.command("decision")
@click.argument("decision")
@click.option("--reason", "-r", required=True, help="Reason for the decision")
def add_decision(decision: str, reason: str):
    """Record a decision."""
    from ..state import StateManager
    
    manager = StateManager(project_path=Path.cwd())
    manager.add_decision(decision=decision, reason=reason)
    
    console.print(f"[green]Recorded decision:[/green] {decision}")
    console.print(f"  Reason: {reason}")


@state.command("blocker")
@click.argument("blocker")
def add_blocker(blocker: str):
    """Add a blocker."""
    from ..state import StateManager
    
    manager = StateManager(project_path=Path.cwd())
    manager.add_blocker(blocker=blocker)
    
    console.print(f"[yellow]Added blocker:[/yellow] {blocker}")


@state.command("resolve")
@click.argument("blocker")
def resolve_blocker(blocker: str):
    """Resolve a blocker."""
    from ..state import StateManager
    
    manager = StateManager(project_path=Path.cwd())
    manager.resolve_blocker(blocker=blocker)
    
    console.print(f"[green]Resolved blocker:[/green] {blocker}")


@state.command("learning")
@click.argument("learning")
@click.option("--category", "-c", default="General", help="Learning category")
@click.option("--source", "-s", default="Execution", help="Learning source")
def add_learning(learning: str, category: str, source: str):
    """Record a learning."""
    from ..state import StateManager
    
    manager = StateManager(project_path=Path.cwd())
    manager.add_learning(learning=learning, category=category, source=source)
    
    console.print(f"[green]Recorded learning:[/green] {learning}")
    console.print(f"  Category: {category}")
    console.print(f"  Source: {source}")


@state.command("hypothesis")
@click.argument("statement")
@click.option("--validation", "-v", default="", help="Validation method")
@click.option("--priority", "-p", type=click.Choice(["high", "medium", "low"]), default="medium", help="Priority")
def add_state_hypothesis(statement: str, validation: str, priority: str):
    """Add a new hypothesis."""
    from ..state import StateManager
    
    manager = StateManager(project_path=Path.cwd())
    h_id = manager.add_hypothesis(
        statement=statement,
        validation_method=validation,
        priority=priority
    )
    
    console.print(f"[green]Added hypothesis:[/green] {h_id}")
    console.print(f"  Statement: {statement}")
    console.print(f"  Validation: {validation}")
    console.print(f"  Priority: {priority}")


@state.command("context")
def show_context():
    """Show context summary for Agent prompt injection."""
    from ..state import StateManager
    
    manager = StateManager(project_path=Path.cwd())
    summary = manager.get_context_summary()
    
    console.print(Panel(
        summary,
        title="Context Summary",
        border_style="cyan",
    ))


@state.command("sync")
def sync_state():
    """Sync STATE.md with hypotheses.json."""
    from ..state import StateManager
    
    manager = StateManager(project_path=Path.cwd())
    manager.sync_with_hypotheses_json()
    
    console.print("[green]Synced STATE.md with hypotheses.json[/green]")



# Register agent command group
try:
    from .agent import agent as agent_group
    cli.add_command(agent_group, name="agent")
except ImportError:
    pass

# Register orchestrator command group
try:
    from .orchestrator import orchestrator as orchestrator_group
    cli.add_command(orchestrator_group, name="orchestrator")
except ImportError:
    pass

# Register two-stage review command group
try:
    from .review import review as review_group
    cli.add_command(review_group, name="review")
except ImportError:
    pass
# 添加到 main.py 末尾，注册 memory 命令组
try:
    from .memory import memory as memory_group
    cli.add_command(memory_group, name="memory")
except ImportError:
    pass

