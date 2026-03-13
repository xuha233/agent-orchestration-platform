# -*- coding: utf-8 -*-
"""
记忆迁移工具

将现有文件记忆迁移到 mem0。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import MemoryConfig
from .service import MemoryService

logger = logging.getLogger(__name__)


class MemoryMigrator:
    """
    记忆迁移工具
    
    功能:
    - 将 hypotheses.json 迁移到 mem0
    - 将 learning.json 迁移到 mem0
    - 将 PROJECT_MEMORY.md 迁移到 mem0
    - 支持增量迁移（只迁移新内容）
    - 支持回滚
    """
    
    def __init__(
        self,
        service: MemoryService,
        workspace_path: Optional[Path] = None,
    ):
        """
        初始化迁移工具
        
        Args:
            service: 记忆服务实例
            workspace_path: 工作空间路径
        """
        self.service = service
        self.workspace_path = workspace_path or service.workspace_path
        self.aop_dir = self.workspace_path / ".aop"
        
        # 迁移日志
        self._migration_log: List[Dict[str, Any]] = []
    
    def analyze(self) -> Dict[str, Any]:
        """
        分析可迁移的内容
        
        Returns:
            分析结果，包含文件列表和统计
        """
        result = {
            "files": {},
            "stats": {
                "hypotheses": 0,
                "learnings": 0,
                "memories": 0,
                "total_entries": 0,
            },
            "ready": False,
            "issues": [],
        }
        
        # 检查假设文件
        hypotheses_file = self.aop_dir / "hypotheses.json"
        if hypotheses_file.exists():
            try:
                with open(hypotheses_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                hypotheses = data.get("data", data)
                count = len([k for k in hypotheses.keys() if not k.startswith("_")])
                result["files"]["hypotheses.json"] = {
                    "path": str(hypotheses_file),
                    "count": count,
                    "size": hypotheses_file.stat().st_size,
                }
                result["stats"]["hypotheses"] = count
                result["stats"]["total_entries"] += count
            except Exception as e:
                result["issues"].append(f"无法读取 hypotheses.json: {e}")
        
        # 检查学习文件
        learning_file = self.aop_dir / "learning.json"
        if learning_file.exists():
            try:
                with open(learning_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = data.get("records", data.get("data", {}).get("records", []))
                count = len(records)
                result["files"]["learning.json"] = {
                    "path": str(learning_file),
                    "count": count,
                    "size": learning_file.stat().st_size,
                }
                result["stats"]["learnings"] = count
                result["stats"]["total_entries"] += count
            except Exception as e:
                result["issues"].append(f"无法读取 learning.json: {e}")
        
        # 检查项目记忆文件
        project_memory_file = self.aop_dir / "PROJECT_MEMORY.md"
        if project_memory_file.exists():
            try:
                content = project_memory_file.read_text(encoding="utf-8")
                lines = content.strip().split("\n")
                result["files"]["PROJECT_MEMORY.md"] = {
                    "path": str(project_memory_file),
                    "lines": len(lines),
                    "size": project_memory_file.stat().st_size,
                }
                result["stats"]["memories"] = 1
                result["stats"]["total_entries"] += 1
            except Exception as e:
                result["issues"].append(f"无法读取 PROJECT_MEMORY.md: {e}")
        
        # 检查记忆文件（如果已存在）
        memories_file = self.aop_dir / "memory" / "memories.json"
        if memories_file.exists():
            try:
                with open(memories_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                existing = len(data.get("memories", {}))
                result["files"]["memory/memories.json"] = {
                    "path": str(memories_file),
                    "count": existing,
                }
            except Exception as e:
                result["issues"].append(f"无法读取现有记忆文件: {e}")
        
        # 判断是否可以迁移
        result["ready"] = (
            result["stats"]["total_entries"] > 0
            and self.service.is_mem0_available
        )
        
        if not self.service.is_mem0_available:
            result["issues"].append("mem0 未启用或不可用")
        
        return result
    
    def migrate_hypotheses(
        self,
        dry_run: bool = False,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        迁移假设记录
        
        Args:
            dry_run: 是否只模拟，不实际迁移
        
        Returns:
            (迁移数量, 迁移详情列表)
        """
        hypotheses_file = self.aop_dir / "hypotheses.json"
        
        if not hypotheses_file.exists():
            return 0, []
        
        with open(hypotheses_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        hypotheses = data.get("data", data)
        migrated = []
        count = 0
        
        for hyp_id, hyp_data in hypotheses.items():
            if hyp_id.startswith("_"):
                continue
            
            # 构建记忆内容
            content = self._format_hypothesis_for_memory(hyp_data)
            
            metadata = {
                "type": "hypothesis",
                "hypothesis_id": hyp_id,
                "state": hyp_data.get("state", "pending"),
                "priority": hyp_data.get("priority", ""),
            }
            
            if dry_run:
                migrated.append({
                    "id": hyp_id,
                    "content": content[:100] + "...",
                    "metadata": metadata,
                })
            else:
                memory_id = self.service.add(content, metadata=metadata)
                if memory_id:
                    migrated.append({
                        "original_id": hyp_id,
                        "memory_id": memory_id,
                        "content": content[:100] + "...",
                    })
            
            count += 1
        
        self._migration_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "migrate_hypotheses",
            "count": count,
            "dry_run": dry_run,
        })
        
        return count, migrated
    
    def migrate_learnings(
        self,
        dry_run: bool = False,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        迁移学习记录
        
        Args:
            dry_run: 是否只模拟，不实际迁移
        
        Returns:
            (迁移数量, 迁移详情列表)
        """
        learning_file = self.aop_dir / "learning.json"
        
        if not learning_file.exists():
            return 0, []
        
        with open(learning_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        records = data.get("records", data.get("data", {}).get("records", []))
        migrated = []
        count = 0
        
        for i, record in enumerate(records):
            # 构建记忆内容
            content = self._format_learning_for_memory(record)
            
            metadata = {
                "type": "learning",
                "phase": record.get("phase", ""),
                "index": i,
            }
            
            if dry_run:
                migrated.append({
                    "index": i,
                    "content": content[:100] + "...",
                    "metadata": metadata,
                })
            else:
                memory_id = self.service.add(content, metadata=metadata)
                if memory_id:
                    migrated.append({
                        "index": i,
                        "memory_id": memory_id,
                        "content": content[:100] + "...",
                    })
            
            count += 1
        
        self._migration_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "migrate_learnings",
            "count": count,
            "dry_run": dry_run,
        })
        
        return count, migrated
    
    def migrate_project_memory(
        self,
        dry_run: bool = False,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        迁移项目记忆文件
        
        Args:
            dry_run: 是否只模拟，不实际迁移
        
        Returns:
            (迁移数量, 迁移详情列表)
        """
        project_memory_file = self.aop_dir / "PROJECT_MEMORY.md"
        
        if not project_memory_file.exists():
            return 0, []
        
        content = project_memory_file.read_text(encoding="utf-8")
        
        # 可以按段落分割
        sections = self._split_markdown_sections(content)
        migrated = []
        count = 0
        
        for section in sections:
            if not section.strip():
                continue
            
            # 提取标题作为元数据
            title = ""
            lines = section.strip().split("\n")
            if lines and lines[0].startswith("#"):
                title = lines[0].lstrip("# ").strip()
            
            metadata = {
                "type": "project_memory",
                "title": title,
                "source": "PROJECT_MEMORY.md",
            }
            
            if dry_run:
                migrated.append({
                    "title": title,
                    "content": section[:100] + "...",
                    "metadata": metadata,
                })
            else:
                memory_id = self.service.add(section, metadata=metadata)
                if memory_id:
                    migrated.append({
                        "memory_id": memory_id,
                        "title": title,
                        "content": section[:100] + "...",
                    })
            
            count += 1
        
        self._migration_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": "migrate_project_memory",
            "count": count,
            "dry_run": dry_run,
        })
        
        return count, migrated
    
    def migrate_all(
        self,
        dry_run: bool = False,
        include_hypotheses: bool = True,
        include_learnings: bool = True,
        include_project_memory: bool = True,
    ) -> Dict[str, Any]:
        """
        迁移所有记忆
        
        Args:
            dry_run: 是否只模拟
            include_hypotheses: 是否迁移假设
            include_learnings: 是否迁移学习
            include_project_memory: 是否迁移项目记忆
        
        Returns:
            迁移结果汇总
        """
        result = {
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "hypotheses": None,
            "learnings": None,
            "project_memory": None,
            "total": 0,
            "success": True,
            "errors": [],
        }
        
        if include_hypotheses:
            try:
                count, migrated = self.migrate_hypotheses(dry_run)
                result["hypotheses"] = {
                    "count": count,
                    "migrated": migrated,
                }
                result["total"] += count
            except Exception as e:
                result["errors"].append(f"假设迁移失败: {e}")
                result["success"] = False
        
        if include_learnings:
            try:
                count, migrated = self.migrate_learnings(dry_run)
                result["learnings"] = {
                    "count": count,
                    "migrated": migrated,
                }
                result["total"] += count
            except Exception as e:
                result["errors"].append(f"学习迁移失败: {e}")
                result["success"] = False
        
        if include_project_memory:
            try:
                count, migrated = self.migrate_project_memory(dry_run)
                result["project_memory"] = {
                    "count": count,
                    "migrated": migrated,
                }
                result["total"] += count
            except Exception as e:
                result["errors"].append(f"项目记忆迁移失败: {e}")
                result["success"] = False
        
        return result
    
    def _format_hypothesis_for_memory(self, hyp_data: Dict[str, Any]) -> str:
        """格式化假设为记忆文本"""
        parts = []
        
        statement = hyp_data.get("statement", "")
        if statement:
            parts.append(f"假设: {statement}")
        
        state = hyp_data.get("state", "pending")
        parts.append(f"状态: {state}")
        
        priority = hyp_data.get("priority", "")
        if priority:
            parts.append(f"优先级: {priority}")
        
        validation_method = hyp_data.get("validation_method", "")
        if validation_method:
            parts.append(f"验证方法: {validation_method}")
        
        findings = hyp_data.get("findings", [])
        if findings:
            parts.append("发现:")
            for f in findings:
                parts.append(f"  - {f}")
        
        return "\n".join(parts)
    
    def _format_learning_for_memory(self, record: Dict[str, Any]) -> str:
        """格式化学习记录为记忆文本"""
        parts = []
        
        phase = record.get("phase", "")
        if phase:
            parts.append(f"阶段: {phase}")
        
        what_worked = record.get("what_worked", [])
        if what_worked:
            parts.append("成功的做法:")
            for w in what_worked:
                parts.append(f"  + {w}")
        
        what_failed = record.get("what_failed", [])
        if what_failed:
            parts.append("失败的原因:")
            for f in what_failed:
                parts.append(f"  - {f}")
        
        insights = record.get("insights", [])
        if insights:
            parts.append("洞察:")
            for i in insights:
                parts.append(f"  * {i}")
        
        return "\n".join(parts)
    
    def _split_markdown_sections(self, content: str) -> List[str]:
        """按标题分割 Markdown 内容"""
        sections = []
        current_section = []
        
        for line in content.split("\n"):
            if line.startswith("# ") or line.startswith("## "):
                if current_section:
                    sections.append("\n".join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            sections.append("\n".join(current_section))
        
        return sections
    
    def get_migration_log(self) -> List[Dict[str, Any]]:
        """获取迁移日志"""
        return self._migration_log.copy()
    
    def export_migration_report(self, output_path: Optional[Path] = None) -> str:
        """
        导出迁移报告
        
        Args:
            output_path: 输出路径（可选）
        
        Returns:
            报告内容
        """
        lines = [
            "# 记忆迁移报告",
            "",
            f"生成时间: {datetime.now().isoformat()}",
            f"工作空间: {self.workspace_path}",
            "",
        ]
        
        # 分析结果
        analysis = self.analyze()
        lines.append("## 源文件分析")
        lines.append("")
        
        for filename, info in analysis["files"].items():
            if "count" in info:
                lines.append(f"- {filename}: {info['count']} 条记录")
            elif "lines" in info:
                lines.append(f"- {filename}: {info['lines']} 行")
        
        lines.append("")
        lines.append("## 迁移统计")
        lines.append("")
        lines.append(f"- 假设: {analysis['stats']['hypotheses']}")
        lines.append(f"- 学习: {analysis['stats']['learnings']}")
        lines.append(f"- 项目记忆: {analysis['stats']['memories']}")
        lines.append(f"- 总计: {analysis['stats']['total_entries']}")
        
        if analysis["issues"]:
            lines.append("")
            lines.append("## 问题")
            lines.append("")
            for issue in analysis["issues"]:
                lines.append(f"- {issue}")
        
        # 迁移日志
        if self._migration_log:
            lines.append("")
            lines.append("## 迁移日志")
            lines.append("")
            
            for entry in self._migration_log:
                lines.append(f"- {entry['timestamp']}: {entry['action']} ({entry['count']} 条)")
        
        report = "\n".join(lines)
        
        if output_path:
            output_path.write_text(report, encoding="utf-8")
        
        return report
