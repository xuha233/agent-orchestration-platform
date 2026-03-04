"""AOP Workspace Management - 工作区管理系统"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import uuid

# 默认存储路径
AOP_DIR = Path.home() / ".aop"
WORKSPACES_DIR = AOP_DIR / "workspaces"
SESSIONS_DIR = AOP_DIR / "sessions"


@dataclass
class Workspace:
    """工作区配置"""
    id: str
    name: str
    project_path: str
    primary_agent: str = "claude_code"  # openclaw | claude_code | opencode
    session_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "project_path": self.project_path,
            "primary_agent": self.primary_agent,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workspace":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Unnamed"),
            project_path=data.get("project_path", ""),
            primary_agent=data.get("primary_agent", "claude_code"),
            session_id=data.get("session_id"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_active=data.get("last_active", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )


class WorkspaceManager:
    """工作区管理器"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or AOP_DIR
        self.workspaces_dir = self.base_dir / "workspaces"
        self.sessions_dir = self.base_dir / "sessions"
        
        # 确保目录存在
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        self._current_workspace: Optional[Workspace] = None
    
    def list_workspaces(self) -> List[Workspace]:
        """列出所有工作区"""
        workspaces = []
        for ws_file in self.workspaces_dir.glob("*.json"):
            try:
                with open(ws_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    workspaces.append(Workspace.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue
        
        # 按最后活跃时间排序
        workspaces.sort(key=lambda w: w.last_active, reverse=True)
        return workspaces
    
    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """获取指定工作区"""
        ws_file = self.workspaces_dir / f"{workspace_id}.json"
        if ws_file.exists():
            with open(ws_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Workspace.from_dict(data)
        return None
    
    def create_workspace(
        self,
        name: str,
        project_path: str,
        primary_agent: str = "claude_code",
    ) -> Workspace:
        """创建新工作区"""
        # 生成 ID（基于项目路径的简短 hash）
        import hashlib
        path_hash = hashlib.md5(project_path.encode()).hexdigest()[:8]
        workspace_id = f"ws_{path_hash}"
        
        workspace = Workspace(
            id=workspace_id,
            name=name,
            project_path=project_path,
            primary_agent=primary_agent,
        )
        
        self._save_workspace(workspace)
        return workspace
    
    def update_workspace(self, workspace: Workspace) -> None:
        """更新工作区"""
        workspace.last_active = datetime.now().isoformat()
        self._save_workspace(workspace)
    
    def delete_workspace(self, workspace_id: str) -> bool:
        """删除工作区"""
        ws_file = self.workspaces_dir / f"{workspace_id}.json"
        if ws_file.exists():
            ws_file.unlink()
            return True
        return False
    
    def set_current_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """设置当前工作区"""
        workspace = self.get_workspace(workspace_id)
        if workspace:
            self._current_workspace = workspace
            self.update_workspace(workspace)
        return workspace
    
    def get_current_workspace(self) -> Optional[Workspace]:
        """获取当前工作区"""
        return self._current_workspace
    
    def _save_workspace(self, workspace: Workspace) -> None:
        """保存工作区到文件"""
        ws_file = self.workspaces_dir / f"{workspace.id}.json"
        with open(ws_file, "w", encoding="utf-8") as f:
            json.dump(workspace.to_dict(), f, ensure_ascii=False, indent=2)
    
    # ============ 会话管理 ============
    
    def create_session(self, workspace_id: str) -> str:
        """为新会话生成 ID"""
        session_id = str(uuid.uuid4())
        
        # 更新工作区的 session_id
        workspace = self.get_workspace(workspace_id)
        if workspace:
            workspace.session_id = session_id
            self.update_workspace(workspace)
        
        return session_id
    
    def get_session_file(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self.sessions_dir / f"{session_id}.jsonl"
    
    def append_to_session(
        self,
        session_id: str,
        message_type: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ) -> None:
        """追加消息到会话文件"""
        session_file = self.get_session_file(session_id)
        
        entry = {
            "type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            entry["metadata"] = metadata
        
        with open(session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def load_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """加载会话历史"""
        session_file = self.get_session_file(session_id)
        if not session_file.exists():
            return []
        
        history = []
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        history.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        return history
