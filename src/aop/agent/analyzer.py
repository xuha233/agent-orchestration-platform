"""
代码库自动分析器
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter


@dataclass
class CodebaseInfo:
    """代码库信息"""
    language: str = "unknown"
    framework: str | None = None
    structure: Dict[str, Any] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0


class CodebaseAnalyzer:
    """代码库自动分析器"""
    
    def __init__(self):
        self.language_extensions = {
            "python": [".py"],
            "javascript": [".js", ".jsx", ".mjs"],
            "typescript": [".ts", ".tsx"],
            "java": [".java"],
            "go": [".go"],
            "rust": [".rs"],
        }
        
        self.framework_indicators = {
            # Web 框架
            "fastapi": ["fastapi", "uvicorn"],
            "django": ["django", "djangorestframework"],
            "flask": ["flask"],
            "starlette": ["starlette"],
            
            # 前端框架
            "react": ["react", "react-dom"],
            "vue": ["vue"],
            "angular": ["@angular/core"],
            "nextjs": ["next"],
            "express": ["express"],
            
            # 桌面 UI 框架
            "pyqt5": ["PyQt5"],
            "pyqt6": ["PyQt6"],
            "pyside6": ["PySide6"],
            "qfluentwidgets": ["qfluentwidgets", "QFluentWidgets"],
            "tkinter": ["tkinter"],
            "pygobject": ["pygobject", "PyGObject"],
            "wxpython": ["wxpython", "wx"],
            "kivy": ["kivy"],
            
            # 数据应用框架
            "streamlit": ["streamlit"],
            "gradio": ["gradio"],
            "dash": ["dash"],
            "jupyter": ["jupyter", "ipython"],
            
            # CLI 框架
            "click": ["click"],
            "typer": ["typer"],
            "argparse": ["argparse"],
            
            # 任务调度
            "celery": ["celery"],
            "dramatiq": ["dramatiq"],
            "huey": ["huey"],
        }
    
    def analyze(self, path: str = ".") -> CodebaseInfo:
        """分析代码库"""
        root = Path(path)
        return CodebaseInfo(
            language=self.detect_language(root),
            framework=self.detect_framework(root),
            entry_points=self.find_entry_points(root),
            dependencies=self._extract_dependencies(root),
            patterns=self.detect_patterns(root),
            structure=self._analyze_structure(root),
            total_files=0,
            total_lines=0,
        )
    
    def detect_language(self, path: Path | str) -> str:
        """检测主语言"""
        root = Path(path)
        ext_counts = Counter()
        for file in root.rglob("*"):
            if file.is_file() and not self._should_ignore(file):
                ext = file.suffix.lower()
                for lang, exts in self.language_extensions.items():
                    if ext in exts:
                        ext_counts[lang] += 1
        return ext_counts.most_common(1)[0][0] if ext_counts else "unknown"
    
    def detect_framework(self, path: Path | str) -> str | None:
        """检测框架"""
        root = Path(path)
        deps_text = ""
        
        # 检查 requirements.txt
        req_file = root / "requirements.txt"
        if req_file.exists():
            deps_text += req_file.read_text(encoding="utf-8", errors="ignore").lower()
        
        # 检查 pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            deps_text += pyproject.read_text(encoding="utf-8", errors="ignore").lower()
        
        # 检查 setup.py
        setup_py = root / "setup.py"
        if setup_py.exists():
            deps_text += setup_py.read_text(encoding="utf-8", errors="ignore").lower()
        
        # 检查 package.json (JavaScript/TypeScript)
        package_json = root / "package.json"
        if package_json.exists():
            deps_text += package_json.read_text(encoding="utf-8", errors="ignore").lower()
        
        # 匹配框架
        for fw, indicators in self.framework_indicators.items():
            for ind in indicators:
                if ind.lower() in deps_text:
                    return fw
        
        return None
    
    def find_entry_points(self, path: Path | str) -> List[str]:
        """查找入口文件"""
        root = Path(path)
        entries = []
        
        # 检查根目录
        root_entries = ["main.py", "app.py", "run.py", "__main__.py", "server.py", "wsgi.py", "asgi.py"]
        for name in root_entries:
            if (root / name).exists():
                entries.append(name)
        
        # 检查 src/ 子目录
        src_dir = root / "src"
        if src_dir.exists():
            for name in root_entries:
                if (src_dir / name).exists():
                    entries.append(f"src/{name}")
        
        # 检查常见的应用目录结构
        for subdir in ["app", "server", "api"]:
            subdir_path = root / subdir
            if subdir_path.exists():
                for name in ["main.py", "app.py", "__init__.py"]:
                    if (subdir_path / name).exists():
                        entries.append(f"{subdir}/{name}")
        
        return entries
    
    def detect_patterns(self, path: Path | str) -> List[str]:
        """检测架构模式"""
        root = Path(path)
        patterns = []
        
        # MVC 模式
        if (root / "models").exists() and (root / "views").exists():
            patterns.append("MVC")
        
        # MVVM 模式
        if (root / "viewmodels").exists() or (
            (root / "models").exists() and 
            (root / "views").exists() and 
            any(f.suffix == ".qml" for f in root.rglob("*.qml"))
        ):
            patterns.append("MVVM")
        
        # 分层架构 - 检查常见分层目录
        layer_dirs = ["api", "service", "repository", "domain", "infrastructure"]
        ui_dirs = ["ui", "views", "presentation", "frontend"]
        core_dirs = ["core", "business", "logic", "backend"]
        
        # 标准 DDD 分层
        if sum(1 for d in layer_dirs if (root / d).exists()) >= 2:
            patterns.append("Layered")
        
        # UI/Core 分层（桌面应用常见）
        elif any((root / d).exists() for d in ui_dirs) and any((root / d).exists() for d in core_dirs):
            patterns.append("Layered")
        
        # src/ 子目录结构
        src_dir = root / "src"
        if src_dir.exists():
            if any((src_dir / d).exists() for d in ui_dirs) and any((src_dir / d).exists() for d in core_dirs):
                if "Layered" not in patterns:
                    patterns.append("Layered")
        
        # Clean Architecture
        clean_dirs = ["entities", "usecases", "interfaces", "adapters"]
        if sum(1 for d in clean_dirs if (root / d).exists()) >= 2:
            patterns.append("Clean Architecture")
        
        # 微服务架构
        if (root / "services").exists() or (root / "microservices").exists():
            patterns.append("Microservice")
        
        # 六边形架构
        if (root / "ports").exists() and (root / "adapters").exists():
            patterns.append("Hexagonal")
        
        # 插件架构
        if (root / "plugins").exists() or (root / "extensions").exists():
            patterns.append("Plugin")
        
        # 事件驱动
        if (root / "events").exists() or (root / "handlers").exists():
            patterns.append("Event-Driven")
        
        return patterns
    
    def _extract_dependencies(self, root: Path) -> List[str]:
        """提取依赖"""
        deps = []
        # requirements.txt
        req_file = root / "requirements.txt"
        if req_file.exists():
            for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    deps.append(line.split("==")[0].split(">=")[0])
        # pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if match:
                for line in match.group(1).splitlines():
                    line = line.strip().strip('"').strip("'")
                    if line and not line.startswith("#") and not line.startswith("["):
                        deps.append(line.split(">=")[0].split("<")[0].split("[")[0])
        return list(set(deps))[:20]
    
    def _analyze_structure(self, root: Path) -> Dict[str, Any]:
        return {d.name: {"type": "directory"} for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")}
    
    def _should_ignore(self, path: Path) -> bool:
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
        return any(part in ignore_dirs for part in path.parts)
