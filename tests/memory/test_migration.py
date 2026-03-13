# -*- coding: utf-8 -*-
"""Tests for memory migration."""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile
import json

from aop.memory.config import MemoryConfig
from aop.memory.service import MemoryService
from aop.memory.migration import MemoryMigrator


class TestMemoryMigrator:
    """Test MemoryMigrator class."""
    
    def test_analyze_empty_workspace(self):
        """Test analyzing an empty workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=Path(tmpdir))
            migrator = MemoryMigrator(service, workspace_path=Path(tmpdir))
            
            analysis = migrator.analyze()
            
            assert analysis["stats"]["total_entries"] == 0
            assert len(analysis["files"]) == 0
            assert analysis["ready"] is False
    
    def test_analyze_with_hypotheses(self):
        """Test analyzing workspace with hypotheses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir(parents=True)
            
            # Create hypotheses file
            hypotheses = {
                "H-001": {
                    "statement": "Test hypothesis",
                    "state": "pending",
                },
                "H-002": {
                    "statement": "Another hypothesis",
                    "state": "validated",
                }
            }
            
            with open(aop_dir / "hypotheses.json", "w", encoding="utf-8") as f:
                json.dump({"data": hypotheses}, f)
            
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=workspace)
            migrator = MemoryMigrator(service, workspace_path=workspace)
            
            analysis = migrator.analyze()
            
            assert analysis["stats"]["hypotheses"] == 2
            assert "hypotheses.json" in analysis["files"]
    
    def test_analyze_with_learnings(self):
        """Test analyzing workspace with learnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir(parents=True)
            
            # Create learning file
            learnings = {
                "records": [
                    {"phase": "build", "what_worked": ["TDD"]},
                    {"phase": "test", "what_worked": ["Integration tests"]},
                ]
            }
            
            with open(aop_dir / "learning.json", "w", encoding="utf-8") as f:
                json.dump(learnings, f)
            
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=workspace)
            migrator = MemoryMigrator(service, workspace_path=workspace)
            
            analysis = migrator.analyze()
            
            assert analysis["stats"]["learnings"] == 2
            assert "learning.json" in analysis["files"]
    
    def test_migrate_hypotheses_dry_run(self):
        """Test migrating hypotheses in dry-run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir(parents=True)
            
            # Create hypotheses
            hypotheses = {
                "H-001": {
                    "statement": "Test hypothesis",
                    "state": "pending",
                    "priority": "high",
                }
            }
            
            with open(aop_dir / "hypotheses.json", "w", encoding="utf-8") as f:
                json.dump({"data": hypotheses}, f)
            
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=workspace)
            migrator = MemoryMigrator(service, workspace_path=workspace)
            
            # Dry run
            count, migrated = migrator.migrate_hypotheses(dry_run=True)
            
            assert count == 1
            assert len(migrated) == 1
            assert migrated[0]["id"] == "H-001"
            
            # Verify no actual migration
            memories = service.list_all(limit=100)
            assert len(memories) == 0
    
    def test_migrate_learnings_dry_run(self):
        """Test migrating learnings in dry-run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir(parents=True)
            
            # Create learning file
            learnings = {
                "records": [
                    {
                        "phase": "build",
                        "what_worked": ["TDD approach"],
                        "what_failed": ["Big design upfront"],
                        "insights": ["Iterate faster"],
                    }
                ]
            }
            
            with open(aop_dir / "learning.json", "w", encoding="utf-8") as f:
                json.dump(learnings, f)
            
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=workspace)
            migrator = MemoryMigrator(service, workspace_path=workspace)
            
            # Dry run
            count, migrated = migrator.migrate_learnings(dry_run=True)
            
            assert count == 1
            assert len(migrated) == 1
    
    def test_migrate_all_dry_run(self):
        """Test migrating all memories in dry-run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir(parents=True)
            
            # Create both files
            with open(aop_dir / "hypotheses.json", "w", encoding="utf-8") as f:
                json.dump({"data": {"H-001": {"statement": "Test", "state": "pending"}}}, f)
            
            with open(aop_dir / "learning.json", "w", encoding="utf-8") as f:
                json.dump({"records": [{"phase": "build"}]}, f)
            
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=workspace)
            migrator = MemoryMigrator(service, workspace_path=workspace)
            
            result = migrator.migrate_all(dry_run=True)
            
            assert result["dry_run"] is True
            assert result["hypotheses"]["count"] == 1
            assert result["learnings"]["count"] == 1
            assert result["total"] == 2
    
    def test_migrate_all_actual(self):
        """Test actual migration (not dry-run)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir(parents=True)
            
            # Create hypotheses
            with open(aop_dir / "hypotheses.json", "w", encoding="utf-8") as f:
                json.dump({
                    "data": {
                        "H-001": {
                            "statement": "Test hypothesis",
                            "state": "pending",
                        }
                    }
                }, f)
            
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=workspace)
            migrator = MemoryMigrator(service, workspace_path=workspace)
            
            # Actual migration
            result = migrator.migrate_all(dry_run=False)
            
            assert result["success"] is True
            assert result["hypotheses"]["count"] == 1
            
            # Verify memory was created
            memories = service.list_all(limit=100)
            assert len(memories) >= 1
    
    def test_export_migration_report(self):
        """Test exporting migration report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir(parents=True)
            
            # Create a hypotheses file
            with open(aop_dir / "hypotheses.json", "w", encoding="utf-8") as f:
                json.dump({"data": {"H-001": {"statement": "Test"}}}, f)
            
            config = MemoryConfig(enabled=False)
            service = MemoryService(config, workspace_path=workspace)
            migrator = MemoryMigrator(service, workspace_path=workspace)
            
            # Generate report
            report = migrator.export_migration_report()
            
            assert "# 记忆迁移报告" in report
            assert "hypotheses.json" in report
    
    def test_format_hypothesis_for_memory(self):
        """Test formatting hypothesis as memory text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = MemoryService(workspace_path=Path(tmpdir))
            migrator = MemoryMigrator(service)
            
            hyp_data = {
                "statement": "Test hypothesis",
                "state": "pending",
                "priority": "high",
                "validation_method": "A/B test",
                "findings": ["Finding 1", "Finding 2"],
            }
            
            content = migrator._format_hypothesis_for_memory(hyp_data)
            
            assert "假设: Test hypothesis" in content
            assert "状态: pending" in content
            assert "优先级: high" in content
            assert "验证方法: A/B test" in content
    
    def test_format_learning_for_memory(self):
        """Test formatting learning as memory text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = MemoryService(workspace_path=Path(tmpdir))
            migrator = MemoryMigrator(service)
            
            record = {
                "phase": "build",
                "what_worked": ["TDD", "Pair programming"],
                "what_failed": ["Big design upfront"],
                "insights": ["Iterate faster", "Communicate more"],
            }
            
            content = migrator._format_learning_for_memory(record)
            
            assert "阶段: build" in content
            assert "成功的做法:" in content
            assert "失败的原因:" in content
            assert "洞察:" in content
