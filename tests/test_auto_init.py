"""
测试 AOP 环境自动初始化功能

测试 loader.py 中的自动初始化逻辑。
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from aop.memory.loader import (
    is_aop_initialized,
    initialize_aop_environment,
    build_agent_system_prompt,
    UNINITIALIZED_PROMPT,
)


class TestAopInitializationDetection:
    """测试 AOP 环境检测"""
    
    def test_is_aop_initialized_returns_false_for_no_aop_dir(self):
        """测试没有 .aop/ 目录时返回 False"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            assert is_aop_initialized(workspace) is False
    
    def test_is_aop_initialized_returns_true_for_existing_aop_dir(self):
        """测试有 .aop/ 目录时返回 True"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir()
            assert is_aop_initialized(workspace) is True
    
    def test_is_aop_initialized_returns_false_for_none_workspace(self):
        """测试 workspace_path 为 None 时返回 False"""
        assert is_aop_initialized(None) is False


class TestAopEnvironmentInitialization:
    """测试 AOP 环境初始化"""
    
    def test_initialize_creates_aop_directory(self):
        """测试初始化创建 .aop/ 目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            created_files = initialize_aop_environment(workspace)
            
            assert (workspace / ".aop").exists()
            assert len(created_files) > 0
    
    def test_initialize_creates_hypotheses_json(self):
        """测试创建 hypotheses.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            created_files = initialize_aop_environment(workspace)
            
            hypotheses_file = workspace / ".aop" / "hypotheses.json"
            assert hypotheses_file.exists()
            assert any("hypotheses.json" in f for f in created_files)
            
            # 验证文件内容
            import json
            with open(hypotheses_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert "_meta" in data
            assert "data" in data
    
    def test_initialize_creates_learning_json(self):
        """测试创建 learning.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            created_files = initialize_aop_environment(workspace)
            
            learning_file = workspace / ".aop" / "learning.json"
            assert learning_file.exists()
            assert any("learning.json" in f for f in created_files)
            
            # 验证文件内容
            import json
            with open(learning_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert "_meta" in data
            assert "learnings" in data
    
    def test_initialize_creates_memory_config_yaml(self):
        """测试创建 memory_config.yaml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            created_files = initialize_aop_environment(workspace)
            
            config_file = workspace / ".aop" / "memory_config.yaml"
            assert config_file.exists()
            assert any("memory_config.yaml" in f for f in created_files)
            
            # 验证文件内容
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            assert "version" in config
            assert "enable_mem0" in config
    
    def test_initialize_creates_state_md(self):
        """测试创建 STATE.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            created_files = initialize_aop_environment(workspace)
            
            state_file = workspace / ".aop" / "STATE.md"
            assert state_file.exists()
            assert any("STATE.md" in f for f in created_files)
            
            # 验证文件内容
            content = state_file.read_text(encoding='utf-8')
            assert "# STATE.md" in content
            assert "初始化 AOP 环境" in content
    
    def test_initialize_with_custom_project_name(self):
        """测试自定义项目名称"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            initialize_aop_environment(workspace, project_name="MyProject")
            
            state_file = workspace / ".aop" / "STATE.md"
            content = state_file.read_text(encoding='utf-8')
            assert "MyProject" in content
    
    def test_initialize_with_soul_md(self):
        """测试创建 SOUL.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            created_files = initialize_aop_environment(workspace, create_soul=True)
            
            soul_file = workspace / ".aop" / "SOUL.md"
            assert soul_file.exists()
            assert any("SOUL.md" in f for f in created_files)
    
    def test_initialize_does_not_overwrite_existing_files(self):
        """测试不覆盖已存在的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            aop_dir = workspace / ".aop"
            aop_dir.mkdir()
            
            # 创建已有的 hypotheses.json
            existing_file = aop_dir / "hypotheses.json"
            existing_file.write_text("existing content", encoding='utf-8')
            
            # 初始化
            created_files = initialize_aop_environment(workspace)
            
            # 验证文件未被覆盖
            assert existing_file.read_text(encoding='utf-8') == "existing content"
            # 只创建新文件
            assert not any("hypotheses.json" in f for f in created_files)
    
    def test_initialize_idempotent(self):
        """测试多次初始化是幂等的"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # 第一次初始化
            created_files_1 = initialize_aop_environment(workspace)
            
            # 第二次初始化
            created_files_2 = initialize_aop_environment(workspace)
            
            # 第二次不应该创建新文件
            assert len(created_files_2) == 0


class TestBuildAgentSystemPrompt:
    """测试 build_agent_system_prompt 函数"""
    
    def test_returns_uninitialized_prompt_for_new_project(self):
        """测试新项目返回未初始化提示词"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            prompt = build_agent_system_prompt(workspace_path=workspace)
            
            assert UNINITIALIZED_PROMPT in prompt
            assert "禁止关闭会话" in prompt
    
    def test_returns_normal_prompt_for_initialized_project(self):
        """测试已初始化项目返回正常提示词"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            initialize_aop_environment(workspace)
            
            prompt = build_agent_system_prompt(workspace_path=workspace)
            
            # 不应包含未初始化提示词
            assert UNINITIALIZED_PROMPT not in prompt
            assert "禁止关闭会话" in prompt
    
    def test_auto_init_initializes_environment(self):
        """测试 auto_init 参数自动初始化环境"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # 使用 auto_init=True
            prompt = build_agent_system_prompt(
                workspace_path=workspace,
                auto_init=True
            )
            
            # 应该自动初始化
            assert (workspace / ".aop").exists()
            # 不应包含未初始化提示词
            assert UNINITIALIZED_PROMPT not in prompt
    
    def test_includes_task_hint(self):
        """测试包含任务提示"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            initialize_aop_environment(workspace)
            
            prompt = build_agent_system_prompt(
                workspace_path=workspace,
                task_hint="Test task"
            )
            
            assert "Test task" in prompt
    
    def test_no_workspace_returns_prohibition_only(self):
        """测试无 workspace 时只返回禁止事项"""
        prompt = build_agent_system_prompt(workspace_path=None)
        
        assert "禁止关闭会话" in prompt
        # 不应包含未初始化提示词（因为没有 workspace）
        assert UNINITIALIZED_PROMPT not in prompt


class TestIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流：检测 -> 初始化 -> 加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # 1. 初始检测：未初始化
            assert is_aop_initialized(workspace) is False
            
            # 2. 获取系统提示词：返回未初始化提示
            prompt = build_agent_system_prompt(workspace_path=workspace)
            assert UNINITIALIZED_PROMPT in prompt
            
            # 3. 初始化环境
            created_files = initialize_aop_environment(workspace, project_name="TestProject")
            assert len(created_files) == 4  # 4 个必需文件
            
            # 4. 再次检测：已初始化
            assert is_aop_initialized(workspace) is True
            
            # 5. 获取系统提示词：正常加载
            prompt = build_agent_system_prompt(workspace_path=workspace)
            assert UNINITIALIZED_PROMPT not in prompt
    
    def test_auto_init_workflow(self):
        """测试自动初始化工作流"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # 使用 auto_init 自动初始化
            prompt = build_agent_system_prompt(
                workspace_path=workspace,
                auto_init=True
            )
            
            # 验证环境已初始化
            assert is_aop_initialized(workspace) is True
            assert (workspace / ".aop" / "hypotheses.json").exists()
            assert (workspace / ".aop" / "learning.json").exists()
            assert (workspace / ".aop" / "STATE.md").exists()
            
            # 验证提示词正常
            assert UNINITIALIZED_PROMPT not in prompt
