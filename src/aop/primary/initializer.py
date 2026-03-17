"""AOP 项目初始化器 - 安全地为项目添加 AOP 配置"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from rich.console import Console
from ..config.models import DEFAULT_OPENCODE_MODEL

console = Console()


@dataclass
class ProjectAnalysis:
    """项目分析结果"""
    project_type: str  # python, node, rust, go, etc.
    package_manager: Optional[str]  # pip, poetry, npm, yarn, etc.
    has_tests: bool
    test_command: Optional[str]
    dependencies: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


@dataclass
class InitResult:
    """初始化结果"""
    success: bool
    created_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ProjectInitializer:
    """项目初始化器"""
    
    PROJECT_TYPE_RULES = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "node": ["package.json"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
        "java": ["pom.xml", "build.gradle"],
    }
    
    TEST_COMMANDS = {
        "python": "pytest",
        "node": "npm test",
        "rust": "cargo test",
        "go": "go test ./...",
    }
    
    AOP_COACH_PROMPT = """# AOP MVP Generator

你是 AOP MVP 生成器。

你的任务是帮助用户把一个想法快速推进到可验证的 MVP，而不是一开始就把系统做得很重。

## 启动时必须执行

1. 检查 `.aop` 目录是否存在
2. 如果存在，优先读取：
   - `.aop/PROJECT_MEMORY.md`
   - `.aop/STATE.md`
   - `.aop/hypotheses.json`
   - `.aop/learning.json`
3. 用简短状态面板告诉用户：
   - 当前项目
   - 当前阶段
   - 假设数量
   - 下一步建议

## 核心命令

- `aop run "想法或任务"` - 主入口
- `aop doctor` - 检查环境
- `aop dashboard` - 打开工作台
- `aop hypothesis ...` - 管理假设
- `aop learning ...` - 管理学习记录

## 工作方式

1. 先澄清用户真正想验证什么
2. 把需求转成假设
3. 选择最小可验证推进方式
4. 需要时再使用多 Agent 协同
5. 结束后把关键决策写回项目记忆

## 约束

- 不要跳过状态检查
- 不要忽略项目记忆
- 不要为了展示能力而过度设计

简洁直接，假设驱动，面向验证。
"""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        
    def analyze(self) -> ProjectAnalysis:
        """分析项目结构"""
        result = ProjectAnalysis(
            project_type="unknown",
            package_manager=None,
            has_tests=False,
            test_command=None,
        )
        
        for ptype, markers in self.PROJECT_TYPE_RULES.items():
            for marker in markers:
                if (self.project_path / marker).exists():
                    result.project_type = ptype
                    result.config_files.append(marker)
                    break
            if result.project_type != "unknown":
                break
        
        if result.project_type == "python":
            if (self.project_path / "pyproject.toml").exists():
                result.package_manager = "poetry"
            else:
                result.package_manager = "pip"
        elif result.project_type == "node":
            if (self.project_path / "yarn.lock").exists():
                result.package_manager = "yarn"
            else:
                result.package_manager = "npm"
        
        test_dirs = ["tests", "test", "__tests__"]
        for tdir in test_dirs:
            if (self.project_path / tdir).exists():
                result.has_tests = True
                break
        
        if result.has_tests:
            result.test_command = self.TEST_COMMANDS.get(result.project_type)
        
        return result
    
    def initialize(self, project_name: Optional[str] = None, force: bool = False) -> InitResult:
        """初始化项目 AOP 配置"""
        result = InitResult(success=True)
        analysis = self.analyze()
        project_name = project_name or self.project_path.name
        
        # .aop 目录
        aop_dir = self.project_path / ".aop"
        aop_dir.mkdir(exist_ok=True)
        result.created_files.append(str(aop_dir))
        
        # PROJECT_MEMORY.md
        memory_file = aop_dir / "PROJECT_MEMORY.md"
        if not memory_file.exists() or force:
            memory_content = f"""# PROJECT_MEMORY.md - 项目记忆

## 基本信息
- **名称**: {project_name}
- **路径**: {self.project_path}
- **类型**: {analysis.project_type}

## 当前状态
- **阶段**: 初始化
- **当前目标**: 明确第一个要验证的想法
- **活跃假设**: 0
- **学习记录**: 0

## 下一步建议
- 先运行 `aop doctor` 检查环境
- 然后用 `aop run "你的想法"` 启动第一轮 MVP 验证

## 关键决策

_暂无关键决策_
"""
            memory_file.write_text(memory_content, encoding="utf-8")
            result.created_files.append(str(memory_file))
        
        # hypotheses.json & learning.json
        for fname in ["hypotheses.json", "learning.json"]:
            fpath = aop_dir / fname
            if not fpath.exists() or force:
                data = {fname.split('.')[0]: []}
                fpath.write_text(json.dumps(data, indent=2), encoding="utf-8")
                result.created_files.append(str(fpath))
        
        # .aop.yaml
        aop_yaml = self.project_path / ".aop.yaml"
        if not aop_yaml.exists() or force:
            yaml_content = f"""project_type: backend
providers:
  - claude
  - opencode
timeout: 300
"""
            aop_yaml.write_text(yaml_content, encoding="utf-8")
            result.created_files.append(str(aop_yaml))
        
        # OpenCode 配置
        self._create_opencode_config(project_name, force, result)
        
        # Claude Code 配置
        self._create_claude_config(force, result)
        
        # 检查风险
        if not analysis.has_tests:
            result.warnings.append("项目没有测试目录，建议添加测试")
        
        return result
    
    def _create_opencode_config(self, project_name: str, force: bool, result: InitResult) -> None:
        """创建 OpenCode 配置"""
        opencode_json = self.project_path / "opencode.json"
        if not opencode_json.exists() or force:
            config = {
                "$schema": "https://opencode.ai/config.json",
                "agent": {
                    "aop-coach": {
                        "description": "AOP 敏捷教练 - 多 Agent 编排、假设驱动开发",
                        "mode": "primary",
                        "prompt": "{file:./AGENTS.md}",
                        "temperature": 0.3
                    }
                }
            }
            if DEFAULT_OPENCODE_MODEL:
                config["model"] = DEFAULT_OPENCODE_MODEL
            opencode_json.write_text(json.dumps(config, indent=2), encoding="utf-8")
            result.created_files.append(str(opencode_json))
        
        agents_md = self.project_path / "AGENTS.md"
        if not agents_md.exists() or force:
            agents_md.write_text(self.AOP_COACH_PROMPT, encoding="utf-8")
            result.created_files.append(str(agents_md))
        
        opencode_agents_dir = self.project_path / ".opencode" / "agents"
        opencode_agents_dir.mkdir(parents=True, exist_ok=True)
        aop_coach_md = opencode_agents_dir / "aop-coach.md"
        if not aop_coach_md.exists() or force:
            aop_coach_md.write_text(f"---\ndescription: AOP 敏捷教练\nmode: primary\ntemperature: 0.3\n---\n\n{self.AOP_COACH_PROMPT}", encoding="utf-8")
            result.created_files.append(str(aop_coach_md))
        
        # 创建启动脚本 (Windows)
        start_bat = self.project_path / "start-aop.bat"
        if not start_bat.exists() or force:
            bat_lines = [
                "@echo off",
                "echo Starting AOP Coach...",
                "opencode --agent aop-coach",
                ""
            ]
            start_bat.write_text("\n".join(bat_lines), encoding="utf-8")
            result.created_files.append(str(start_bat))
    
    def _create_claude_config(self, force: bool, result: InitResult) -> None:
        """创建 Claude Code 配置"""
        claude_dir = self.project_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        
        claude_md = claude_dir / "CLAUDE.md"
        if not claude_md.exists() or force:
            claude_md.write_text(self.AOP_COACH_PROMPT + "\n\n## 核心约束\n\n主会话只能由用户关闭。", encoding="utf-8")
            result.created_files.append(str(claude_md))
    
    def verify(self) -> bool:
        """验证初始化完整性"""
        required = [
            self.project_path / ".aop",
            self.project_path / ".aop.yaml",
            self.project_path / "opencode.json",
            self.project_path / "AGENTS.md",
            self.project_path / ".claude" / "CLAUDE.md",
        ]
        return all(f.exists() for f in required)
