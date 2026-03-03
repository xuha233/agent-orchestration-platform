"""
超时延长协议
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtensionProtocol:
    REQUEST_START = "[TIMEOUT_EXTENSION_REQUEST]"
    REQUEST_END = "[/TIMEOUT_EXTENSION_REQUEST]"
    RESPONSE_START = "[TIMEOUT_EXTENSION_RESPONSE]"
    RESPONSE_END = "[/TIMEOUT_EXTENSION_RESPONSE]"

    @staticmethod
    def format_extension_request(requested_seconds: int, reason: str, progress_summary: str) -> str:
        data = {"requested_seconds": requested_seconds, "reason": reason, "progress_summary": progress_summary}
        return f"{ExtensionProtocol.REQUEST_START}\n{json.dumps(data, ensure_ascii=False, indent=2)}\n{ExtensionProtocol.REQUEST_END}"

    @staticmethod
    def parse_extension_request(text: str) -> Optional[dict]:
        # 需要转义 [ 和 ]
        pattern = r"\[TIMEOUT_EXTENSION_REQUEST\]\s*(.*?)\s*\[/TIMEOUT_EXTENSION_REQUEST\]"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def format_extension_response(approved: bool, granted_seconds: int, message: str) -> str:
        data = {"approved": approved, "granted_seconds": granted_seconds, "message": message}
        return f"{ExtensionProtocol.RESPONSE_START}\n{json.dumps(data, ensure_ascii=False, indent=2)}\n{ExtensionProtocol.RESPONSE_END}"

    @staticmethod
    def parse_extension_response(text: str) -> Optional[dict]:
        pattern = r"\[TIMEOUT_EXTENSION_RESPONSE\]\s*(.*?)\s*\[/TIMEOUT_EXTENSION_RESPONSE\]"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def get_agent_instructions() -> str:
        return """## 超时延长机制

申请方式：输出以下格式：

[TIMEOUT_EXTENSION_REQUEST]
{"requested_seconds": 300, "reason": "需要更多时间", "progress_summary": "已完成 50%"}
[/TIMEOUT_EXTENSION_REQUEST]

参数说明：
- requested_seconds: 请求延长的秒数（建议 300-600）
- reason: 延长原因
- progress_summary: 当前进度摘要

注意事项：
- 每个任务最多延长 3 次
- 总延长时间不超过 30 分钟
- 在申请延长前，请先保存当前进度
"""
