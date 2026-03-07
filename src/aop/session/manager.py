# -*- coding: utf-8 -*-
"""
Claude Code Session Manager - 会话管理器

功能：
1. 捕获 Claude Code 会话 ID（从输出中解析）
2. 存储会话 ID 到项目配置
3. 启动时自动恢复会话上下文
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

AOP_DIR = Path.home() / ".aop"
PROJECTS_DIR = AOP_DIR / "projects"


@dataclass
class SessionInfo:
    """会话信息"""
    session_id: str
    provider: str
    project_id: str
    workspace: str
    created_at: str
    last_used: str
    message_count: int = 0
    status: str = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionInfo":
        return cls(**data)


class SessionManager:
    """会话管理器"""
    
    CLAUDE_SESSION_PATTERN = re.compile(
        r'claude\s+--resume\s+([a-f0-9-]{36})',
        re.IGNORECASE
    )
    
    OPENCODE_SESSION_PATTERN = re.compile(
        r'opencode\s+--resume\s+([a-f0-9-]+)',
        re.IGNORECASE
    )
    
    def __init__(self, projects_dir: Path = None):
        self.projects_dir = projects_dir or PROJECTS_DIR
        self.projects_dir.mkdir(parents=True, exist_ok=True)
    
    def get_project_sessions_path(self, project_id: str) -> Path:
        return self.projects_dir / project_id / "sessions.json"
    
    def load_sessions(self, project_id: str) -> Dict[str, SessionInfo]:
        sessions_file = self.get_project_sessions_path(project_id)
        
        if not sessions_file.exists():
            return {}
        
        try:
            with open(sessions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                sid: SessionInfo.from_dict(info)
                for sid, info in data.items()
            }
        except Exception as e:
            logger.error(f"Failed to load sessions for {project_id}: {e}")
            return {}
    
    def save_sessions(self, project_id: str, sessions: Dict[str, SessionInfo]):
        sessions_file = self.get_project_sessions_path(project_id)
        sessions_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(sessions_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {sid: info.to_dict() for sid, info in sessions.items()},
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        except Exception as e:
            logger.error(f"Failed to save sessions for {project_id}: {e}")
    
    def capture_session(
        self,
        output: str,
        project_id: str,
        workspace: str,
        provider: str = "claude"
    ) -> Optional[str]:
        """从输出中捕获会话 ID"""
        if provider == "claude":
            pattern = self.CLAUDE_SESSION_PATTERN
        elif provider == "opencode":
            pattern = self.OPENCODE_SESSION_PATTERN
        else:
            logger.warning(f"Unknown provider: {provider}")
            return None
        
        match = pattern.search(output)
        if not match:
            logger.debug(f"No session ID found in output")
            return None
        
        session_id = match.group(1)
        logger.info(f"Captured session ID: {session_id}")
        
        sessions = self.load_sessions(project_id)
        now = datetime.now().isoformat()
        
        if session_id in sessions:
            sessions[session_id].last_used = now
            sessions[session_id].message_count += 1
        else:
            sessions[session_id] = SessionInfo(
                session_id=session_id,
                provider=provider,
                project_id=project_id,
                workspace=workspace,
                created_at=now,
                last_used=now,
                message_count=1,
                status="active"
            )
        
        self.save_sessions(project_id, sessions)
        return session_id
    
    def get_latest_session(
        self,
        project_id: str,
        provider: str = "claude"
    ) -> Optional[SessionInfo]:
        """获取项目最新的活跃会话"""
        sessions = self.load_sessions(project_id)
        
        active_sessions = [
            s for s in sessions.values()
            if s.provider == provider and s.status == "active"
        ]
        
        if not active_sessions:
            return None
        
        active_sessions.sort(key=lambda s: s.last_used, reverse=True)
        return active_sessions[0]
    
    def get_resume_command(
        self,
        project_id: str,
        provider: str = "claude",
        base_command: str = None
    ) -> str:
        """生成带 --resume 的命令"""
        session = self.get_latest_session(project_id, provider)
        
        if provider == "claude":
            base = base_command or "claude"
        elif provider == "opencode":
            base = base_command or "opencode"
        else:
            return base or provider
        
        if session:
            return f"{base} --resume {session.session_id}"
        else:
            return base


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def capture_from_output(output: str, project_id: str, workspace: str, provider: str = "claude") -> Optional[str]:
    return get_session_manager().capture_session(output, project_id, workspace, provider)


def get_resume_command(project_id: str, provider: str = "claude") -> str:
    return get_session_manager().get_resume_command(project_id, provider)
