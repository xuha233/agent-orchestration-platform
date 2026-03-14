"""AOP Command Listener - 命令监听器

监听 ~/.aop/commands/ 目录，自动执行命令文件。
支持外部程序（如 OpenClaw、Claude Code）触发 AOP 操作。
"""

import json
import time
import threading
import shutil
import subprocess
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
    command: str
    args: Dict[str, Any]
    timestamp: str
    source: str = "external"
    
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
        
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._handlers: Dict[str, Callable] = {}
        
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        self.register_handler("review", self._handle_review)
        self.register_handler("hypothesis", self._handle_hypothesis)
        self.register_handler("run", self._handle_run)
        self.register_handler("dashboard", self._handle_dashboard)
        self.register_handler("status", self._handle_status)
    
    def register_handler(self, command: str, handler: Callable):
        self._handlers[command] = handler
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info(f"Command listener started, watching {self.commands_dir}")
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Command listener stopped")
    
    def _listen_loop(self):
        processed_files = set()
        
        while self._running:
            try:
                for cmd_file in list(self.commands_dir.glob("*.json")):
                    if cmd_file.name in processed_files:
                        continue
                    
                    self._process_command_file(cmd_file)
                    processed_files.add(cmd_file.name)
                    
                    try:
                        cmd_file.unlink()
                    except Exception:
                        pass
                
                if len(processed_files) > 100:
                    processed_files = set(list(processed_files)[-100:])
                
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
            
            time.sleep(self.poll_interval)
    
    def _process_command_file(self, cmd_file: Path):
        try:
            with open(cmd_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            cmd = AOPCommand.from_json(data)
            logger.info(f"Processing command: {cmd.command} (id: {cmd.id})")
            
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
            
            self._write_result(result)
            
        except Exception as e:
            logger.error(f"Error processing command file: {e}")
    
    def _write_result(self, result: CommandResult):
        result_file = self.results_dir / f"{result.command_id}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    # ============ 默认处理器 ============
    
    def _handle_review(self, cmd: AOPCommand) -> CommandResult:
        args = cmd.args
        prompt = args.get("prompt", "")
        provider = args.get("provider", "claude")
        
        cli_args = ["aop", "review", "-p", prompt, "-P", provider]
        
        try:
            result = subprocess.run(
                cli_args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
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
        args = cmd.args
        action = args.get("action", "list")
        statement = args.get("statement", "")
        
        try:
            from aop.workflow.hypothesis import HypothesisManager
            
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
        return CommandResult(
            command_id=cmd.id,
            success=False,
            output="",
            error="aop run is not yet implemented",
        )
    
    def _handle_dashboard(self, cmd: AOPCommand) -> CommandResult:
        action = cmd.args.get("action", "status")
        
        if action == "open":
            import webbrowser
            webbrowser.open(f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
            return CommandResult(
                command_id=cmd.id,
                success=True,
                output="Dashboard opened in browser",
            )
        else:
            return CommandResult(
                command_id=cmd.id,
                success=True,
                output=f"Dashboard is running at http://{DASHBOARD_HOST}:{DASHBOARD_PORT}",
            )
    
    def _handle_status(self, cmd: AOPCommand) -> CommandResult:
        """检查 Provider 状态（简化版，避免 detect() 卡住）"""
        import shutil
        
        providers = {
            "claude": "claude",
            "codex": "codex",
            "gemini": None,  # Python package
            "qwen": None,    # Python package
            "opencode": "opencode",
        }
        
        status_lines = []
        for pid, binary in providers.items():
            if binary:
                available = shutil.which(binary) is not None
                status_lines.append(f"{pid}: {'✅' if available else '❌'}")
            else:
                status_lines.append(f"{pid}: ⚠️ (check manually)")
        
        return CommandResult(
            command_id=cmd.id,
            success=True,
            output="\n".join(status_lines),
        )


# 全局实例
_listener: Optional[CommandListener] = None


def get_listener() -> CommandListener:
    global _listener
    if _listener is None:
        _listener = CommandListener()
    return _listener


def start_listener():
    listener = get_listener()
    listener.start()


def stop_listener():
    global _listener
    if _listener:
        _listener.stop()


def submit_command(command: str, args: Dict[str, Any] = None, source: str = "external") -> str:
    """提交命令到监听器"""
    import uuid
    
    cmd_id = str(uuid.uuid4())[:8]
    
    cmd_data = {
        "id": cmd_id,
        "command": command,
        "args": args or {},
        "timestamp": datetime.now().isoformat(),
        "source": source,
    }
    
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    cmd_file = COMMANDS_DIR / f"{cmd_id}.json"
    
    with open(cmd_file, "w", encoding="utf-8") as f:
        json.dump(cmd_data, f, ensure_ascii=False, indent=2)
    
    return cmd_id



