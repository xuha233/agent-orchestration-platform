"""
代码库自动分析器
"""

from __future__ import annotations

import ast
import json
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
            "fastapi": ["fastapi", "uvicorn"],
            "django": ["django", "djangorestframework"],
            "flask": ["flask"],
            "react": ["react", "react-dom"],
            "vue": ["vue"],
            "angular": ["@angular/core"],
            "nextjs": ["next"],
            "express": ["express"],
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
        req_file = root / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text(encoding="utf-8", errors="ignore").lower()
            for fw, indicators in self.framework_indicators.items():
                if any(ind in content for ind in indicators):
                    return fw
        return None
    
    def find_entry_points(self, path: Path | str) -> List[str]:
        """查找入口文件"""
        root = Path(path)
        entries = []
        for name in ["main.py", "app.py", "run.py", "__main__.py"]:
            if (root / name).exists():
                entries.append(name)
        return entries
    
    def detect_patterns(self, path: Path | str) -> List[str]:
        """检测架构模式"""
        root = Path(path)
        patterns = []
        if (root / "models").exists() and (root / "views").exists():
            patterns.append("MVC")
        if sum(1 for l in ["api", "service", "repository"] if (root / l).exists()) >= 2:
            patterns.append("Layered")
        return patterns
    
    def _extract_dependencies(self, root: Path) -> List[str]:
        deps = []
        req_file = root / "requirements.txt"
        if req_file.exists():
            for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    deps.append(line.split("==")[0].split(">=")[0])
        return deps[:20]
    
    def _analyze_structure(self, root: Path) -> Dict[str, Any]:
        return {d.name: {"type": "directory"} for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")}
    
    def _should_ignore(self, path: Path) -> bool:
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
        return any(part in ignore_dirs for part in path.parts)
