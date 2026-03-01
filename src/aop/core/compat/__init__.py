# -*- coding: utf-8 -*-
"""
AOP 跨平台兼容性模块

功能：
1. 自动检测操作系统
2. 提供平台特定的配置
3. 处理路径分隔符差异
4. 提供平台特定的命令建议
"""

import platform
import os
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class Platform(Enum):
    """操作系统类型"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


@dataclass
class PlatformConfig:
    """平台特定配置"""
    platform: Platform
    path_sep: str
    shell: str
    install_script: str
    env_var_prefix: str  # 环境变量前缀 ($ 或 %)
    env_var_suffix: str  # 环境变量后缀 (空 或 %)
    line_ending: str
    home_var: str  # HOME 或 USERPROFILE


class PlatformDetector:
    """平台检测器"""
    
    _instance: Optional['PlatformDetector'] = None
    _platform: Optional[Platform] = None
    _config: Optional[PlatformConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._detect()
        return cls._instance
    
    def _detect(self):
        """检测操作系统"""
        system = platform.system()
        
        if system == "Windows":
            self._platform = Platform.WINDOWS
            self._config = PlatformConfig(
                platform=Platform.WINDOWS,
                path_sep="\\",
                shell="powershell",
                install_script="install.ps1",
                env_var_prefix="$env:",
                env_var_suffix="",
                line_ending="\r\n",
                home_var="USERPROFILE"
            )
        elif system == "Darwin":
            self._platform = Platform.MACOS
            self._config = PlatformConfig(
                platform=Platform.MACOS,
                path_sep="/",
                shell="bash",
                install_script="install.sh",
                env_var_prefix="$",
                env_var_suffix="",
                line_ending="\n",
                home_var="HOME"
            )
        elif system == "Linux":
            self._platform = Platform.LINUX
            self._config = PlatformConfig(
                platform=Platform.LINUX,
                path_sep="/",
                shell="bash",
                install_script="install.sh",
                env_var_prefix="$",
                env_var_suffix="",
                line_ending="\n",
                home_var="HOME"
            )
        else:
            self._platform = Platform.UNKNOWN
            self._config = PlatformConfig(
                platform=Platform.UNKNOWN,
                path_sep="/",
                shell="bash",
                install_script="install.sh",
                env_var_prefix="$",
                env_var_suffix="",
                line_ending="\n",
                home_var="HOME"
            )
    
    @property
    def current_platform(self) -> Platform:
        """获取当前平台"""
        return self._platform
    
    @property
    def config(self) -> PlatformConfig:
        """获取平台配置"""
        return self._config
    
    def is_windows(self) -> bool:
        """是否是 Windows"""
        return self._platform == Platform.WINDOWS
    
    def is_macos(self) -> bool:
        """是否是 macOS"""
        return self._platform == Platform.MACOS
    
    def is_linux(self) -> bool:
        """是否是 Linux"""
        return self._platform == Platform.LINUX
    
    def get_home_directory(self) -> str:
        """获取用户主目录"""
        if self.is_windows():
            return os.environ.get("USERPROFILE", os.path.expanduser("~"))
        return os.environ.get("HOME", os.path.expanduser("~"))
    
    def normalize_path(self, path: str) -> str:
        """标准化路径"""
        if self.is_windows():
            return path.replace("/", "\\")
        return path.replace("\\", "/")
    
    def get_env_command(self, var_name: str, value: str) -> str:
        """获取设置环境变量的命令"""
        if self.is_windows():
            return f'$env:{var_name} = "{value}"'
        return f'export {var_name}="{value}"'
    
    def get_provider_install_commands(self) -> Dict[str, List[str]]:
        """获取 Provider 安装命令"""
        commands = {
            "claude": [
                "npm install -g @anthropic-ai/claude-code",
                "claude auth login"
            ],
            "codex": [
                "npm install -g @openai/codex",
                self.get_env_command("OPENAI_API_KEY", "your-key")
            ],
            "gemini": [
                "pip install google-generativeai",
                self.get_env_command("GOOGLE_API_KEY", "your-key")
            ],
            "qwen": [
                "pip install dashscope",
                self.get_env_command("DASHSCOPE_API_KEY", "your-key")
            ],
            "opencode": [
                "npm install -g opencode",
                "opencode auth login"
            ]
        }
        return commands
    
    def get_platform_info(self) -> Dict[str, str]:
        """获取平台信息"""
        return {
            "platform": self._platform.value,
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "shell": self._config.shell,
            "install_script": self._config.install_script
        }


def get_platform_detector() -> PlatformDetector:
    """获取平台检测器实例"""
    return PlatformDetector()


# 便捷函数
def is_windows() -> bool:
    return get_platform_detector().is_windows()

def is_macos() -> bool:
    return get_platform_detector().is_macos()

def is_linux() -> bool:
    return get_platform_detector().is_linux()

def normalize_path(path: str) -> str:
    return get_platform_detector().normalize_path(path)


# 使用示例
if __name__ == "__main__":
    detector = get_platform_detector()
    
    print(f"Platform: {detector.current_platform.value}")
    print(f"Shell: {detector.config.shell}")
    print(f"Install script: {detector.config.install_script}")
    print(f"Home directory: {detector.get_home_directory()}")
    print(f"Path separator: {detector.config.path_sep}")
    
    print("\nPlatform info:")
    for key, value in detector.get_platform_info().items():
        print(f"  {key}: {value}")
    
    print("\nProvider install commands:")
    for provider, commands in detector.get_provider_install_commands().items():
        print(f"  {provider}:")
        for cmd in commands:
            print(f"    {cmd}")
