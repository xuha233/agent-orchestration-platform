"""AOP Command Listener - 命令监听器

监听 ~/.aop/commands/ 目录，自动执行命令文件。
支持外部程序（如 OpenClaw、Claude Code）触发 AOP 操作。
"""

import json
import time
import threading
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 默认路径
AOP_DIR = Path.home() / ".aop"
COMMANDS_DIR = AOP_DIR / "commands"
RESULTS_DIR = AOP_DIR / "results"


@dataclass
class AOPCommand:
    """AOP 命令"""
    id: str
    command: str  # review, hypothesis, run, etc.
    args: Dict[str, Any]
    timestamp: str
    source: str = "external"  # openclaw, claude_code, external
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "AOPCommand":
        return cls(
            id=data.get("id", ""),
            command=data.get("command", ""),
            args=data.get("args", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            source=data.get("source", "external"),
        )


@dataclass
class CommandResult:
    """命令执行结果"""
    command_id: str
    success: bool
    output: str
    error: Optional[str] = None
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "timestamp": self.timestamp or datetime.now().isoformat(),
        }


class CommandListener:
    """命令监听器"""
    
    def __init__(
        self,
        commands_dir: Path = None,
        results_dir: Path = None,
        poll_interval: float = 1.0,
    ):
        self.commands_dir = commands_dir or COMMANDS_DIR
        self.results_dir = results_dir or RESULTS_DIR
        self.poll_interval = poll_interval
        
        # 确保目录存在
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._handlers: Dict[str, Callable] = {}
        
        # 注册默认处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认命令处理器"""
        self.register_handler("review", self._handle_review)
        self.register_handler("hypothesis", self._handle_hypothesis)
        self.register_handler("run", self._handle_run)
        self.register_handler("dashboard", self._handle_dashboard)
        self.register_handler("status", self._handle_status)
    
    def register_handler(self, command: str, handler: Callable):
        """注册命令处理器"""
        self._handlers[command] = handler
    
    def start(self):
        """启动监听"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info(f"Command listener started, watching {self.commands_dir}")
    
    def stop(self):
        """停止监听"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Command listener stopped")
    
    def _listen_loop(self):
        """监听循环"""
        processed_files = set()
        
        while self._running:
            try:
                # 扫描命令文件
                for cmd_file in self.commands_dir.glob("*.json"):
                    if cmd_file.name in processed_files:
                        continue
                    
                    # 处理命令
                    self._process_command_file(cmd_file)
                    processed_files.add(cmd_file.name)
                    
                    # 删除已处理的命令文件
                    try:
                        cmd_file.unlink()
                    except Exception:
                        pass
                
                # 清理旧的已处理文件记录（保留最近 100 个）
                if len(processed_files) > 100:
                    processed_files = set(list(processed_files)[-100:])
                
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
            
            time.sleep(self.poll_interval)
    
    def _process_command_file(self, cmd_file: Path):
        """处理命令文件"""
        try:
            with open(cmd_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            cmd = AOPCommand.from_json(data)
            logger.info(f"Processing command: {cmd.command} (id: {cmd.id})")
            
            # 获取处理器
            handler = self._handlers.get(cmd.command)
            if handler:
                result = handler(cmd)
            else:
                result = CommandResult(
                    command_id=cmd.id,
                    success=False,
                    output="",
                    error=f"Unknown command: {cmd.command}",
                )
            
            # 写入结果
            self._write_result(result)
            
        except Exception as e:
            logger.error(f"Error processing command file: {e}")
    
    def _write_result(self, result: CommandResult):
        """写入结果文件"""
        result_file = self.results_dir / f"{result.command_id}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    # ============ 默认处理器 ============
    
    def _handle_review(self, cmd: AOPCommand) -> CommandResult:
        """处理 review 命令"""
        from ..cli.main import cli
        import subprocess
        import sys
        
        args = cmd.args
        prompt = args.get("prompt", "")
        provider = args.get("provider", "claude")
        
        # 构建 CLI 命令
        cli_args = ["aop", "review", "-p", prompt, "-P", provider]
        
        try:
            result = subprocess.run(
                cli_args,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return CommandResult(
                command_id=cmd.id,
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return CommandResult(
                command_id=cmd.id,
                success=False,
                output="",
                error=str(e),
            )
    
    def _handle_hypothesis(self, cmd: AOPCommand) -> CommandResult:
        """处理 hypothesis 命令"""
        args = cmd.args
        action = args.get("action", "list")
        statement = args.get("statement", "")
        
        try:
            from ..workflow.hypothesis import HypothesisManager
            
            manager = HypothesisManager()
            
            if action == "create" and statement:
                h = manager.create(
                    statement=statement,
                    validation_method=args.get("validation_method", ""),
                    priority=args.get("priority", "medium"),
                )
                return CommandResult(
                    command_id=cmd.id,
                    success=True,
                    output=f"Created hypothesis: {h.hypothesis_id}",
                )
            else:
                hypotheses = manager.list_all()
                output = "\n".join([
                    f"- {h.statement} ({h.state})"
                    for h in hypotheses[:10]
                ])
                return CommandResult(
                    command_id=cmd.id,
                    success=True,
                    output=output or "No hypotheses found.",
                )
        except Exception as e:
            return CommandResult(
                command_id=cmd.id,
                success=False,
                output="",
                error=str(e),
            )
    
    def _handle_run(self, cmd: AOPCommand) -> CommandResult:
        """处理 run 命令"""
        # TODO: 实现 aop run 逻辑
        return CommandResult(
            command_id=cmd.id,
            success=False,
            output="",
            error="aop run is not yet implemented",
        )
    
    def _handle_dashboard(self, cmd: AOPCommand) -> CommandResult:
        """处理 dashboard 命令"""
        action = cmd.args.get("action", "status")
        
        if action == "open":
            import webbrowser
            webbrowser.open("http://localhost:8501")
            return CommandResult(
                command_id=cmd.id,
                success=True,
                output="Dashboard opened in browser",
            )
        else:
            return CommandResult(
                command_id=cmd.id,
                success=True,
                output="Dashboard is running at http://localhost:8501",
            )
    
    def _handle_status(self, cmd: AOPCommand) -> CommandResult:
        """处理 status 命令"""
        from ..core.adapter import get_adapter_registry
        
        registry = get_adapter_registry()
        providers = ["claude", "codex", "gemini", "qwen", "opencode"]
        
        status_lines = []
        for pid in providers:
            adapter = registry.get(pid)
            if adapter:
                presence = adapter.detect()
                status = "✅" if presence.detected and presence.auth_ok else "❌"
                status_lines.append(f"{pid}: {status}")
            else:
                status_lines.append(f"{pid}: ❌")
        
        return CommandResult(
            command_id=cmd.id,
            success=True,
            output="\n".join(status_lines),
        )


# 全局监听器实例
_listener: Optional[CommandListener] = None


def get_listener() -> CommandListener:
    """获取全局监听器实例"""
    global _listener
    if _listener is None:
        _listener = CommandListener()
    return _listener


def start_listener():
    """启动全局监听器"""
    listener = get_listener()
    listener.start()


def stop_listener():
    """停止全局监听器"""
    global _listener
    if _listener:
        _listener.stop()


def submit_command(command: str, args: Dict[str, Any] = None, source: str = "external") -> str:
    """提交命令到监听器
    
    Args:
        command: 命令名称（review, hypothesis, etc.）
        args: 命令参数
        source: 命令来源（openclaw, claude_code, external）
    
    Returns:
        命令 ID
    """
    import uuid
    
    cmd_id = str(uuid.uuid4())[:8]
    
    cmd_data = {
        "id": cmd_id,
        "command": command,
        "args": args or {},
        "timestamp": datetime.now().isoformat(),
        "source": source,
    }
    
    # 写入命令文件
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    cmd_file = COMMANDS_DIR / f"{cmd_id}.json"
    
    with open(cmd_file, "w", encoding="utf-8") as f:
        json.dump(cmd_data, f, ensure_ascii=False, indent=2)
    
    return cmd_id
