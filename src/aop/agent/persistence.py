"""
冲刺持久化管理

支持中断后恢复冲刺，包括：
- JSON 格式存储
- 增量保存
- 损坏文件处理
- 冲刺列表查询
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from .types import (
    SprintContext,
    SprintState,
    ClarifiedRequirement,
    GeneratedHypothesis,
    ExtractedLearning,
)


class SprintPersistence:
    """
    冲刺持久化管理

    功能:
    - save: 保存冲刺上下文到 JSON 文件
    - load: 加载冲刺上下文
    - list_sprints: 列出所有冲刺（可按状态过滤）
    - get_latest: 获取最近的冲刺
    - delete: 删除冲刺
    - archive: 归档冲刺（移动到归档目录）
    """

    def __init__(self, storage_path: str = ".aop/sprints"):
        """
        初始化持久化管理器

        Args:
            storage_path: 存储目录路径
        """
        self.storage_path = Path(storage_path)
        self.archive_path = self.storage_path.parent / "sprints_archive"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """确保存储目录存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)

    def save(self, context: SprintContext, incremental: bool = True) -> None:
        """
        保存冲刺上下文

        Args:
            context: 冲刺上下文对象
            incremental: 是否增量保存（更新时间戳）
        """
        if incremental:
            context.updated_at = datetime.now()

        # 先写入临时文件，避免写入过程中崩溃导致数据损坏
        temp_path = self.storage_path / f".tmp_{context.sprint_id}.json"
        final_path = self.storage_path / f"{context.sprint_id}.json"

        try:
            data = self._serialize_context(context)

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            # 原子操作：重命名临时文件
            temp_path.replace(final_path)

        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"保存冲刺上下文失败: {e}") from e

    def _serialize_context(self, context: SprintContext) -> Dict[str, Any]:
        """
        序列化冲刺上下文为字典

        Args:
            context: 冲刺上下文对象

        Returns:
            可 JSON 序列化的字典
        """
        data = {
            "sprint_id": context.sprint_id,
            "original_input": context.original_input,
            "state": context.state.value,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
        }

        # 澄清后的需求
        if context.clarified_requirement:
            req = context.clarified_requirement
            data["clarified_requirement"] = {
                "summary": req.summary,
                "user_type": req.user_type,
                "core_features": req.core_features,
                "tech_constraints": req.tech_constraints,
                "success_criteria": req.success_criteria,
                "priority_order": req.priority_order,
                "risks": req.risks,
                "clarifications": [
                    {"question": qa.question, "answer": qa.answer, "confidence": qa.confidence}
                    for qa in req.clarifications
                ] if req.clarifications else [],
            }

        # 假设列表
        if context.hypotheses:
            data["hypotheses"] = []
            for h in context.hypotheses:
                if isinstance(h, GeneratedHypothesis):
                    data["hypotheses"].append({
                        "statement": h.statement,
                        "hypothesis_type": h.hypothesis_type.value if hasattr(h.hypothesis_type, 'value') else str(h.hypothesis_type),
                        "validation_method": h.validation_method,
                        "success_criteria": h.success_criteria,
                        "priority": h.priority,
                        "estimated_effort": h.estimated_effort,
                        "dependencies": h.dependencies,
                        "risk_level": h.risk_level,
                    })
                elif isinstance(h, dict):
                    data["hypotheses"].append(h)

        # 执行结果
        if context.execution_results:
            data["execution_results"] = context.execution_results

        # 学习提取
        if context.learnings:
            data["learnings"] = []
            for l in context.learnings:
                if isinstance(l, ExtractedLearning):
                    data["learnings"].append({
                        "phase": l.phase,
                        "what_worked": l.what_worked,
                        "what_failed": l.what_failed,
                        "insights": l.insights,
                        "patterns": l.patterns,
                        "confidence": l.confidence,
                    })
                elif isinstance(l, dict):
                    data["learnings"].append(l)

        return data

    def load(self, sprint_id: str) -> Optional[SprintContext]:
        """
        加载冲刺上下文

        Args:
            sprint_id: 冲刺ID

        Returns:
            冲刺上下文对象，如果不存在或损坏则返回 None
        """
        context_path = self.storage_path / f"{sprint_id}.json"

        if not context_path.exists():
            return None

        try:
            with open(context_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return self._deserialize_context(data)

        except json.JSONDecodeError as e:
            # JSON 文件损坏，尝试恢复
            return self._handle_corrupted_file(context_path, e)
        except Exception as e:
            # 其他错误，记录并返回 None
            print(f"加载冲刺上下文失败: {e}")
            return None

    def _deserialize_context(self, data: Dict[str, Any]) -> SprintContext:
        """
        反序列化字典为冲刺上下文

        Args:
            data: 字典数据

        Returns:
            冲刺上下文对象
        """
        context = SprintContext(
            sprint_id=data["sprint_id"],
            original_input=data["original_input"],
            state=SprintState(data.get("state", "initialized")),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )

        # 恢复澄清后的需求
        if "clarified_requirement" in data:
            req_data = data["clarified_requirement"]
            context.clarified_requirement = ClarifiedRequirement(
                summary=req_data.get("summary", ""),
                user_type=req_data.get("user_type", "unknown"),
                core_features=req_data.get("core_features", []),
                tech_constraints=req_data.get("tech_constraints", {}),
                success_criteria=req_data.get("success_criteria", []),
                priority_order=req_data.get("priority_order", []),
                risks=req_data.get("risks", []),
                clarifications=[
                    type('QAPair', (), {
                        "question": qa["question"],
                        "answer": qa["answer"],
                        "confidence": qa.get("confidence", 0.0)
                    })() for qa in req_data.get("clarifications", [])
                ],
            )

        # 恢复假设列表
        if "hypotheses" in data:
            context.hypotheses = data["hypotheses"]

        # 恢复执行结果
        if "execution_results" in data:
            context.execution_results = data["execution_results"]

        # 恢复学习提取
        if "learnings" in data:
            context.learnings = [
                ExtractedLearning(
                    phase=l.get("phase", ""),
                    what_worked=l.get("what_worked", []),
                    what_failed=l.get("what_failed", []),
                    insights=l.get("insights", []),
                    patterns=l.get("patterns", []),
                    confidence=l.get("confidence", 0.0),
                ) for l in data["learnings"]
            ]

        return context

    def _handle_corrupted_file(self, file_path: Path, error: Exception) -> Optional[SprintContext]:
        """
        处理损坏的存储文件

        策略:
        1. 尝试读取部分内容
        2. 备份损坏的文件
        3. 返回 None 或部分恢复的数据

        Args:
            file_path: 损坏的文件路径
            error: 错误信息

        Returns:
            部分恢复的上下文或 None
        """
        # 备份损坏的文件
        backup_path = self.storage_path / "corrupted" / f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.bak"
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(file_path, backup_path)
            print(f"损坏文件已备份到: {backup_path}")
        except Exception as e:
            print(f"备份损坏文件失败: {e}")

        # 尝试部分恢复
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 尝试找到有效的 JSON 片段
            # 简单策略：找到第一个完整的 JSON 对象
            start = content.find("{")
            if start >= 0:
                # 尝试逐步截断并解析
                for end in range(len(content), start, -1):
                    try:
                        data = json.loads(content[start:end])
                        if "sprint_id" in data:
                            print(f"部分恢复成功，从损坏文件中提取了冲刺 {data['sprint_id']}")
                            return self._deserialize_context(data)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        return None

    def list_sprints(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有冲刺

        Args:
            status: 可选的状态过滤

        Returns:
            冲刺信息列表
        """
        sprints = []

        for file_path in self.storage_path.glob("*.json"):
            if file_path.stem.startswith("."):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                sprint_state = data.get("state", "unknown")

                # 状态过滤
                if status and sprint_state != status:
                    continue

                sprints.append({
                    "sprint_id": data.get("sprint_id", file_path.stem),
                    "state": sprint_state,
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "original_input": data.get("original_input", "")[:100] + "..." if len(data.get("original_input", "")) > 100 else data.get("original_input", ""),
                    "file_path": str(file_path),
                })

            except (json.JSONDecodeError, Exception) as e:
                sprints.append({
                    "sprint_id": file_path.stem,
                    "state": "corrupted",
                    "error": str(e),
                    "file_path": str(file_path),
                })

        # 按更新时间排序（最新的在前）
        sprints.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return sprints

    def get_latest(self) -> Optional[SprintContext]:
        """
        获取最近的冲刺

        Returns:
            最新的冲刺上下文，如果没有则返回 None
        """
        sprints = self.list_sprints()

        if not sprints:
            return None

        # 排除损坏的冲刺
        valid_sprints = [s for s in sprints if s.get("state") != "corrupted"]

        if not valid_sprints:
            return None

        latest = valid_sprints[0]
        return self.load(latest["sprint_id"])

    def get_latest_active(self) -> Optional[SprintContext]:
        """
        获取最近的活跃冲刺（未完成的）

        Returns:
            最新的活跃冲刺上下文，如果没有则返回 None
        """
        active_states = ["initialized", "clarified", "hypotheses_generated", "tasks_decomposed", "executed", "validated"]

        for state in active_states:
            sprints = self.list_sprints(status=state)
            if sprints:
                return self.load(sprints[0]["sprint_id"])

        return None

    def delete(self, sprint_id: str) -> bool:
        """
        删除冲刺

        Args:
            sprint_id: 冲刺ID

        Returns:
            删除是否成功
        """
        context_path = self.storage_path / f"{sprint_id}.json"

        if not context_path.exists():
            return False

        try:
            context_path.unlink()
            return True
        except Exception as e:
            print(f"删除冲刺失败: {e}")
            return False

    def archive(self, sprint_id: str) -> bool:
        """
        归档冲刺（移动到归档目录）

        Args:
            sprint_id: 冲刺ID

        Returns:
            归档是否成功
        """
        source_path = self.storage_path / f"{sprint_id}.json"
        dest_path = self.archive_path / f"{sprint_id}.json"

        if not source_path.exists():
            return False

        try:
            shutil.move(str(source_path), str(dest_path))
            return True
        except Exception as e:
            print(f"归档冲刺失败: {e}")
            return False

    def cleanup_old_sprints(self, days: int = 30, keep_active: bool = True) -> int:
        """
        清理旧的冲刺

        Args:
            days: 保留天数
            keep_active: 是否保留活跃冲刺

        Returns:
            清理的冲刺数量
        """
        import time

        cutoff = time.time() - (days * 24 * 60 * 60)
        cleaned = 0

        active_states = ["initialized", "clarified", "hypotheses_generated", "tasks_decomposed", "executed", "validated"]

        for sprint in self.list_sprints():
            if sprint.get("state") == "corrupted":
                continue

            file_path = Path(sprint.get("file_path", ""))
            if not file_path.exists():
                continue

            # 检查文件修改时间
            if file_path.stat().st_mtime < cutoff:
                # 检查是否活跃
                if keep_active and sprint.get("state") in active_states:
                    continue

                # 归档而不是删除
                if self.archive(sprint["sprint_id"]):
                    cleaned += 1

        return cleaned

    def export_sprint(self, sprint_id: str, export_path: Path) -> bool:
        """
        导出冲刺到指定路径

        Args:
            sprint_id: 冲刺ID
            export_path: 导出路径

        Returns:
            导出是否成功
        """
        source_path = self.storage_path / f"{sprint_id}.json"

        if not source_path.exists():
            return False

        try:
            shutil.copy2(source_path, export_path)
            return True
        except Exception as e:
            print(f"导出冲刺失败: {e}")
            return False

    def import_sprint(self, import_path: Path, new_id: Optional[str] = None) -> Optional[str]:
        """
        从文件导入冲刺

        Args:
            import_path: 导入文件路径
            new_id: 新的冲刺ID（可选）

        Returns:
            导入的冲刺ID，失败返回 None
        """
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if new_id:
                data["sprint_id"] = new_id

            sprint_id = data["sprint_id"]
            dest_path = self.storage_path / f"{sprint_id}.json"

            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            return sprint_id

        except Exception as e:
            print(f"导入冲刺失败: {e}")
            return None
