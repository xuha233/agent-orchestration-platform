"""
Claude Code 命令配置模块

支持通过环境变量或配置文件自定义 Claude Code 命令前缀。

环境变量：
- AOP_CLAUDE_BINARY: Claude Code 二进制名称（默认: ccr）
- AOP_CLAUDE_SUBCMD: Claude Code 子命令（默认: code）
- AOP_CLAUDE_CMD: 完整命令（如 "claude" 或 "ccr code"，优先级最高）

配置文件 (~/.aop/config.yaml):
```yaml
claude:
  binary: ccr
  subcmd: code
  # 或直接指定完整命令
  command: "claude"
```

示例：
- 原生 Claude Code: AOP_CLAUDE_CMD="claude"
- CCR: AOP_CLAUDE_CMD="ccr code" 或 AOP_CLAUDE_BINARY="ccr" AOP_CLAUDE_SUBCMD="code"
"""

import os
from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class ClaudeCommandConfig:
    """Claude Code 命令配置"""
    binary: str
    subcmd: str

    @property
    def full_command(self) -> str:
        """返回完整命令字符串"""
        if self.subcmd:
            return f"{self.binary} {self.subcmd}"
        return self.binary

    def to_cmd_args(self) -> list:
        """转换为命令行参数列表"""
        if self.subcmd:
            return [self.binary, self.subcmd]
        return [self.binary]


# 默认配置：使用 CCR
DEFAULT_CONFIG = ClaudeCommandConfig(binary="ccr", subcmd="code")


def load_config_from_file() -> Optional[ClaudeCommandConfig]:
    """从配置文件加载配置"""
    config_path = Path.home() / ".aop" / "config.yaml"

    if not config_path.exists():
        return None

    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config or "claude" not in config:
            return None

        claude_config = config["claude"]

        # 优先使用完整命令
        if "command" in claude_config:
            parts = claude_config["command"].split(maxsplit=1)
            if len(parts) == 1:
                return ClaudeCommandConfig(binary=parts[0], subcmd="")
            return ClaudeCommandConfig(binary=parts[0], subcmd=parts[1])

        # 否则使用 binary + subcmd
        binary = claude_config.get("binary", DEFAULT_CONFIG.binary)
        subcmd = claude_config.get("subcmd", DEFAULT_CONFIG.subcmd)
        return ClaudeCommandConfig(binary=binary, subcmd=subcmd)

    except Exception:
        return None


def get_claude_command_config() -> ClaudeCommandConfig:
    """
    获取 Claude Code 命令配置

    优先级：
    1. 环境变量 AOP_CLAUDE_CMD（完整命令）
    2. 环境变量 AOP_CLAUDE_BINARY + AOP_CLAUDE_SUBCMD
    3. 配置文件 ~/.aop/config.yaml
    4. 默认值（ccr code）
    """
    # 1. 检查完整命令环境变量
    full_cmd = os.environ.get("AOP_CLAUDE_CMD")
    if full_cmd:
        parts = full_cmd.strip().split(maxsplit=1)
        if len(parts) == 1:
            return ClaudeCommandConfig(binary=parts[0], subcmd="")
        return ClaudeCommandConfig(binary=parts[0], subcmd=parts[1])

    # 2. 检查分离的环境变量
    binary = os.environ.get("AOP_CLAUDE_BINARY")
    subcmd = os.environ.get("AOP_CLAUDE_SUBCMD")
    if binary:
        return ClaudeCommandConfig(
            binary=binary,
            subcmd=subcmd if subcmd else DEFAULT_CONFIG.subcmd
        )

    # 3. 检查配置文件
    file_config = load_config_from_file()
    if file_config:
        return file_config

    # 4. 返回默认配置
    return DEFAULT_CONFIG


def get_claude_binary() -> str:
    """获取 Claude Code 二进制名称"""
    return get_claude_command_config().binary


def get_claude_subcmd() -> str:
    """获取 Claude Code 子命令"""
    return get_claude_command_config().subcmd


def get_claude_cmd_prefix() -> list:
    """
    获取 Claude Code 命令前缀

    返回值示例：
    - CCR: ["ccr", "code"]
    - 原生 Claude: ["claude"]
    """
    return get_claude_command_config().to_cmd_args()


# 便捷函数
def get_claude_full_cmd() -> str:
    """获取完整命令字符串（用于显示）"""
    return get_claude_command_config().full_command
