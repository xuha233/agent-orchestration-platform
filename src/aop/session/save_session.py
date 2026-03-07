# -*- coding: utf-8 -*-
"""会话 ID 保存脚本"""

import sys
import json
from pathlib import Path
from datetime import datetime

def save_session(session_id: str, project_id: str, workspace: str, provider: str = "claude"):
    aop_dir = Path.home() / ".aop" / "projects" / project_id
    aop_dir.mkdir(parents=True, exist_ok=True)

    sessions_file = aop_dir / "sessions.json"
    sessions = {}

    if sessions_file.exists():
        try:
            with open(sessions_file, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
        except Exception:
            pass

    now = datetime.now().isoformat()

    if session_id in sessions:
        sessions[session_id]["last_used"] = now
        sessions[session_id]["message_count"] += 1
    else:
        sessions[session_id] = {
            "session_id": session_id,
            "provider": provider,
            "project_id": project_id,
            "workspace": workspace,
            "created_at": now,
            "last_used": now,
            "message_count": 1,
            "status": "active"
        }

    with open(sessions_file, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)

    print(f"Session saved: {session_id[:8]}...")

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        save_session(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "claude")
    else:
        print("Usage: python save_session.py SESSION_ID PROJECT_ID WORKSPACE [PROVIDER]")
