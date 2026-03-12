"""
STATE.md 管理器

提供跨会话状态持久化和管理功能。
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .templates import (
    STATE_TEMPLATE,
    format_timestamp,
    format_hypotheses_table,
    format_decisions,
    format_blockers,
    format_learnings,
)


@dataclass
class StateData:
    """状态数据结构"""
    session_id: str = ""
    current_task: str = "无"
    last_action: str = "无"
    next_step: str = "待确定"
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    blockers: List[Dict[str, Any]] = field(default_factory=list)
    learnings: List[Dict[str, Any]] = field(default_factory=list)
    context: str = "无"
    updated_at: datetime = field(default_factory=datetime.now)


class StateManager:
    """
    STATE.md 跨会话记忆管理器
    
    功能:
    - 加载/保存状态到 STATE.md 文件
    - 更新任务状态
    - 添加决策记录
    - 更新假设状态
    - 管理阻塞项
    - 添加学习笔记
    - 生成上下文摘要
    - 与现有 hypotheses.json 兼容
    
    使用示例:
        manager = StateManager(project_path=Path("."))
        
        # 更新任务
        manager.update_task(
            task="实现用户认证",
            action="完成了登录 API",
            next_step="添加密码重置功能"
        )
        
        # 记录决策
        manager.add_decision(
            decision="使用 JWT 进行认证",
            reason="无状态，易扩展"
        )
        
        # 添加阻塞项
        manager.add_blocker("等待 Stripe API Key")
        
        # 解决阻塞项
        manager.resolve_blocker("等待 Stripe API Key")
        
        # 记录学习
        manager.add_learning(
            learning="用户更喜欢简洁的登录流程",
            category="用户体验",
            source="用户访谈"
        )
        
        # 获取上下文摘要（注入 Agent prompt）
        summary = manager.get_context_summary()
    """
    
    def __init__(self, project_path: Path, session_id: Optional[str] = None):
        """
        初始化状态管理器
        
        Args:
            project_path: 项目根目录路径
            session_id: 会话ID，如果不提供则自动生成
        """
        self.project_path = Path(project_path)
        self.aop_dir = self.project_path / ".aop"
        self.state_file = self.aop_dir / "STATE.md"
        self.hypotheses_file = self.aop_dir / "hypotheses.json"
        
        self.session_id = session_id or self._generate_session_id()
        self._cache: Optional[StateData] = None
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"session-{uuid.uuid4().hex[:8]}"
    
    def _ensure_aop_dir(self):
        """确保 .aop 目录存在"""
        self.aop_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> StateData:
        """
        加载状态
        
        Returns:
            StateData: 当前状态数据
        """
        if self._cache is not None:
            return self._cache
        
        if not self.state_file.exists():
            # 尝试从 hypotheses.json 加载
            data = self._load_from_hypotheses_json()
            self._cache = data
            return data
        
        # 解析 STATE.md
        data = self._parse_state_md()
        self._cache = data
        return data
    
    def _load_from_hypotheses_json(self) -> StateData:
        """从现有的 hypotheses.json 加载假设数据"""
        data = StateData(session_id=self.session_id)
        
        if self.hypotheses_file.exists():
            try:
                with open(self.hypotheses_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                
                hypotheses_data = raw.get("data", {})
                for h_id, h_info in hypotheses_data.items():
                    data.hypotheses.append({
                        "hypothesis_id": h_id,
                        "statement": h_info.get("statement", ""),
                        "state": h_info.get("state", "pending"),
                        "validation_method": h_info.get("validation_method", ""),
                        "result": "",
                        "priority": h_info.get("priority", "medium"),
                    })
            except Exception as e:
                print(f"[StateManager] Failed to load hypotheses.json: {e}")
        
        return data
    
    def _parse_state_md(self) -> StateData:
        """解析 STATE.md 文件"""
        data = StateData(session_id=self.session_id)
        
        try:
            content = self.state_file.read_text(encoding="utf-8")
            
            # 解析元数据
            session_match = re.search(r"> 会话: (.+)" , content)
            if session_match:
                data.session_id = session_match.group(1).strip()
            
            # 解析当前状态
            task_match = re.search(r"\*\*正在工作\*\*: (.+)" , content)
            if task_match:
                data.current_task = task_match.group(1).strip()
            
            action_match = re.search(r"\*\*最后行动\*\*: (.+)" , content)
            if action_match:
                data.last_action = action_match.group(1).strip()
            
            step_match = re.search(r"\*\*下一步\*\*: (.+)" , content)
            if step_match:
                data.next_step = step_match.group(1).strip()
            
            # 解析假设表格
            data.hypotheses = self._parse_hypotheses_table(content)
            
            # 解析决策记录
            data.decisions = self._parse_decisions(content)
            
            # 解析阻塞项
            data.blockers = self._parse_blockers(content)
            
            # 解析学习笔记
            data.learnings = self._parse_learnings(content)
            
            # 解析上下文
            context_match = re.search(r"## 上下文\n\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
            if context_match:
                data.context = context_match.group(1).strip()
        
        except Exception as e:
            print(f"[StateManager] Failed to parse STATE.md: {e}")
        
        return data
    
    def _parse_hypotheses_table(self, content: str) -> List[Dict[str, Any]]:
        """解析假设表格"""
        hypotheses = []
        
        # 找到表格部分
        table_match = re.search(
            r"\| ID \| 假设 \| 状态 \| 验证方法 \| 结果 \|\n\|[-| ]+\|\n(.+?)(?=\n## |\Z)",
            content,
            re.DOTALL
        )
        
        if table_match:
            table_content = table_match.group(1)
            for line in table_content.strip().split("\n"):
                if line.startswith("|") and not line.startswith("| -"):
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 5:
                        hypotheses.append({
                            "hypothesis_id": parts[0],
                            "statement": parts[1],
                            "state": parts[2],
                            "validation_method": parts[3],
                            "result": parts[4],
                        })
        
        return hypotheses
    
    def _parse_decisions(self, content: str) -> List[Dict[str, Any]]:
        """解析决策记录"""
        decisions = []
        
        # 找到决策部分
        decision_match = re.search(
            r"## 决策记录\n\n(.+?)(?=\n## |\Z)",
            content,
            re.DOTALL
        )
        
        if decision_match:
            decision_content = decision_match.group(1)
            # 解析每个决策
            pattern = r"- \*\*\[([^\]]+)\]\*\* (.+)\n  - 原因: (.+)"
            for match in re.finditer(pattern, decision_content):
                decisions.append({
                    "date": match.group(1),
                    "decision": match.group(2).strip(),
                    "reason": match.group(3).strip(),
                })
        
        return decisions
    
    def _parse_blockers(self, content: str) -> List[Dict[str, Any]]:
        """解析阻塞项"""
        blockers = []
        
        blocker_match = re.search(
            r"## 阻塞项\n\n(.+?)(?=\n## |\Z)",
            content,
            re.DOTALL
        )
        
        if blocker_match:
            blocker_content = blocker_match.group(1)
            # 解析每个阻塞项
            pattern = r"- \[([ x])\] (.+)\n  - 添加时间: (.+?)(?:\n  - 解决时间: (.+?))?(?=\n- |\Z)"
            for match in re.finditer(pattern, blocker_content, re.DOTALL):
                blockers.append({
                    "resolved": match.group(1) == "x",
                    "blocker": match.group(2).strip(),
                    "added_at": match.group(3).strip(),
                    "resolved_at": match.group(4).strip() if match.group(4) else "",
                })
        
        return blockers
    
    def _parse_learnings(self, content: str) -> List[Dict[str, Any]]:
        """解析学习笔记"""
        learnings = []
        
        learning_match = re.search(
            r"## 学习笔记\n\n(.+?)(?=\n## |\Z)",
            content,
            re.DOTALL
        )
        
        if learning_match:
            learning_content = learning_match.group(1)
            # 解析每个学习笔记
            pattern = r"- \*\*\[([^\]]+)\]\*\* (.+)\n  - 内容: (.+)\n  - 来源: (.+)"
            for match in re.finditer(pattern, learning_content):
                learnings.append({
                    "date": match.group(1),
                    "category": match.group(2).strip(),
                    "content": match.group(3).strip(),
                    "source": match.group(4).strip(),
                })
        
        return learnings
    
    def save(self, state: Optional[StateData] = None):
        """
        保存状态
        
        Args:
            state: 要保存的状态数据，如果不提供则使用缓存
        """
        if state is None:
            state = self._cache or StateData(session_id=self.session_id)
        
        self._cache = state
        self._ensure_aop_dir()
        
        content = STATE_TEMPLATE.format(
            timestamp=format_timestamp(state.updated_at),
            session_id=state.session_id,
            current_task=state.current_task,
            last_action=state.last_action,
            next_step=state.next_step,
            hypotheses_table=format_hypotheses_table(state.hypotheses),
            decisions=format_decisions(state.decisions),
            blockers=format_blockers(state.blockers),
            learnings=format_learnings(state.learnings),
            context=state.context,
        )
        
        self.state_file.write_text(content, encoding="utf-8")
    
    def update_task(self, task: str, action: str, next_step: str):
        """
        更新当前任务
        
        Args:
            task: 当前正在工作的任务
            action: 最后执行的行动
            next_step: 下一步计划
        """
        state = self.load()
        state.current_task = task
        state.last_action = action
        state.next_step = next_step
        state.updated_at = datetime.now()
        self.save(state)
    
    def add_decision(self, decision: str, reason: str):
        """
        添加决策记录
        
        Args:
            decision: 决策内容
            reason: 决策原因
        """
        state = self.load()
        state.decisions.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "decision": decision,
            "reason": reason,
        })
        state.updated_at = datetime.now()
        self.save(state)
    
    def update_hypothesis(
        self,
        hypothesis_id: str,
        status: str,
        result: Optional[str] = None
    ):
        """
        更新假设状态
        
        Args:
            hypothesis_id: 假设ID
            status: 新状态 (pending, validating, validated, rejected)
            result: 验证结果（可选）
        """
        state = self.load()
        
        for h in state.hypotheses:
            if h.get("hypothesis_id") == hypothesis_id:
                h["state"] = status
                if result:
                    h["result"] = result
                break
        else:
            # 如果假设不存在，添加新假设
            state.hypotheses.append({
                "hypothesis_id": hypothesis_id,
                "statement": "",
                "state": status,
                "validation_method": "",
                "result": result or "",
            })
        
        state.updated_at = datetime.now()
        self.save(state)
    
    def add_hypothesis(
        self,
        statement: str,
        validation_method: str = "",
        priority: str = "medium"
    ) -> str:
        """
        添加新假设
        
        Args:
            statement: 假设陈述
            validation_method: 验证方法
            priority: 优先级
            
        Returns:
            str: 假设ID
        """
        state = self.load()
        
        hypothesis_id = f"H-{uuid.uuid4().hex[:8].upper()}"
        
        state.hypotheses.append({
            "hypothesis_id": hypothesis_id,
            "statement": statement,
            "state": "pending",
            "validation_method": validation_method,
            "result": "",
            "priority": priority,
        })
        
        state.updated_at = datetime.now()
        self.save(state)
        
        return hypothesis_id
    
    def add_blocker(self, blocker: str):
        """
        添加阻塞项
        
        Args:
            blocker: 阻塞项描述
        """
        state = self.load()
        
        # 检查是否已存在相同的阻塞项
        for b in state.blockers:
            if b.get("blocker") == blocker and not b.get("resolved", False):
                return  # 已存在未解决的相同阻塞项
        
        state.blockers.append({
            "resolved": False,
            "blocker": blocker,
            "added_at": format_timestamp(),
            "resolved_at": "",
        })
        
        state.updated_at = datetime.now()
        self.save(state)
    
    def resolve_blocker(self, blocker: str):
        """
        解决阻塞项
        
        Args:
            blocker: 阻塞项描述（需要完全匹配）
        """
        state = self.load()
        
        for b in state.blockers:
            if b.get("blocker") == blocker and not b.get("resolved", False):
                b["resolved"] = True
                b["resolved_at"] = format_timestamp()
                break
        
        state.updated_at = datetime.now()
        self.save(state)
    
    def add_learning(
        self,
        learning: str,
        category: str = "通用",
        source: str = "执行过程"
    ):
        """
        添加学习笔记
        
        Args:
            learning: 学习内容
            category: 分类（技术、产品、流程等）
            source: 来源
        """
        state = self.load()
        
        state.learnings.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "category": category,
            "content": learning,
            "source": source,
        })
        
        state.updated_at = datetime.now()
        self.save(state)
    
    def update_context(self, context: str):
        """
        更新上下文
        
        Args:
            context: 上下文内容
        """
        state = self.load()
        state.context = context
        state.updated_at = datetime.now()
        self.save(state)
    
    def get_context_summary(self, max_length: int = 1000) -> str:
        """
        获取上下文摘要（用于注入 Agent prompt）
        
        Args:
            max_length: 最大长度限制
            
        Returns:
            str: 上下文摘要
        """
        state = self.load()
        
        lines = []
        
        # 当前状态
        lines.append(f"**当前状态**:")
        lines.append(f"- 正在工作: {state.current_task}")
        lines.append(f"- 最后行动: {state.last_action}")
        lines.append(f"- 下一步: {state.next_step}")
        lines.append("")
        
        # 活跃假设
        active_hypotheses = [
            h for h in state.hypotheses
            if h.get("state") in ["pending", "validating"]
        ]
        if active_hypotheses:
            lines.append(f"**活跃假设** ({len(active_hypotheses)}):")
            for h in active_hypotheses[:5]:  # 最多显示5个
                lines.append(f"- [{h.get('hypothesis_id')}] {h.get('statement', '')[:60]}")
            lines.append("")
        
        # 未解决的阻塞项
        active_blockers = [
            b for b in state.blockers if not b.get("resolved", False)
        ]
        if active_blockers:
            lines.append(f"**阻塞项** ({len(active_blockers)}):")
            for b in active_blockers:
                lines.append(f"- {b.get('blocker')}")
            lines.append("")
        
        # 最近决策
        recent_decisions = state.decisions[-3:] if state.decisions else []
        if recent_decisions:
            lines.append(f"**最近决策**:")
            for d in recent_decisions:
                lines.append(f"- [{d.get('date')}] {d.get('decision')}")
            lines.append("")
        
        # 最近学习
        recent_learnings = state.learnings[-3:] if state.learnings else []
        if recent_learnings:
            lines.append(f"**最近学习**:")
            for l in recent_learnings:
                lines.append(f"- {l.get('content', '')[:60]}")
            lines.append("")
        
        summary = "\n".join(lines)
        
        # 截断到最大长度
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    def get_active_blockers(self) -> List[Dict[str, Any]]:
        """获取所有未解决的阻塞项"""
        state = self.load()
        return [b for b in state.blockers if not b.get("resolved", False)]
    
    def get_active_hypotheses(self) -> List[Dict[str, Any]]:
        """获取所有活跃假设（pending 或 validating）"""
        state = self.load()
        return [
            h for h in state.hypotheses
            if h.get("state") in ["pending", "validating"]
        ]
    
    def sync_with_hypotheses_json(self):
        """
        与 hypotheses.json 同步
        
        将 hypotheses.json 中的假设合并到 STATE.md
        """
        if not self.hypotheses_file.exists():
            return
        
        try:
            with open(self.hypotheses_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            
            hypotheses_data = raw.get("data", {})
            state = self.load()
            
            # 建立现有假设的索引
            existing_ids = {h.get("hypothesis_id") for h in state.hypotheses}
            
            # 添加新假设
            for h_id, h_info in hypotheses_data.items():
                if h_id not in existing_ids:
                    state.hypotheses.append({
                        "hypothesis_id": h_id,
                        "statement": h_info.get("statement", ""),
                        "state": h_info.get("state", "pending"),
                        "validation_method": h_info.get("validation_method", ""),
                        "result": "",
                        "priority": h_info.get("priority", "medium"),
                    })
            
            self.save(state)
            
        except Exception as e:
            print(f"[StateManager] Failed to sync with hypotheses.json: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        state = self.load()
        return {
            "session_id": state.session_id,
            "current_task": state.current_task,
            "last_action": state.last_action,
            "next_step": state.next_step,
            "hypotheses": state.hypotheses,
            "decisions": state.decisions,
            "blockers": state.blockers,
            "learnings": state.learnings,
            "context": state.context,
            "updated_at": format_timestamp(state.updated_at),
        }
