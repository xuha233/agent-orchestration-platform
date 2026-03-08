# Claude Code 命令配置

AOP 支持动态配置 Claude Code 命令前缀，方便用户选择原生 Claude Code 或 Claude Code Router。

## 配置方式

### 方式 1：环境变量（推荐）

```bash
# 使用原生 Claude Code
export AOP_CLAUDE_CMD="claude"

# 使用 Claude Code Router（默认）
export AOP_CLAUDE_CMD="ccr code"

# 或分开设置
export AOP_CLAUDE_BINARY="claude"
export AOP_CLAUDE_SUBCMD=""
```

### 方式 2：配置文件

创建 `~/.aop/config.yaml`：

```yaml
claude:
  # 方式 1：完整命令
  command: "claude"

  # 方式 2：分离配置
  # binary: ccr
  # subcmd: code
```

### 方式 3：默认值

如果未配置，默认使用 `ccr code`。

## 优先级

1. 环境变量 `AOP_CLAUDE_CMD`
2. 环境变量 `AOP_CLAUDE_BINARY` + `AOP_CLAUDE_SUBCMD`
3. 配置文件 `~/.aop/config.yaml`
4. 默认值 `ccr code`

## Agent 安装流程

安装 AOP 时，Agent 应询问：

```
请问您想使用哪种 Claude Code 模式？

1. 【原生 Claude Code】
   - 使用 Anthropic 官方 API
   - 需要运行: claude auth login
   - 命令: claude

2. 【Claude Code Router】（默认）
   - 支持第三方模型 API（DeepSeek、Gemini、OpenRouter 等）
   - 性价比更高
   - 命令: ccr code

请选择（1 或 2）：
```

### 如果选择【1】原生 Claude Code

```bash
# 设置环境变量（临时）
export AOP_CLAUDE_CMD="claude"

# 或写入配置文件（永久）
mkdir -p ~/.aop
echo 'claude:\n  command: "claude"' > ~/.aop/config.yaml

# 验证
claude --version
claude auth login
```

### 如果选择【2】Claude Code Router

默认配置，无需额外设置。继续 CCR 安装流程：
1. `npm install -g @musistudio/claude-code-router`
2. 询问配置信息
3. 创建 `~/.claude-code-router/config.json`
4. 验证 `ccr code`

## 验证配置

```python
from aop.config.claude_config import get_claude_full_cmd

print(get_claude_full_cmd())
# 输出: "claude" 或 "ccr code"
```

## 示例

### Windows (PowerShell)

```powershell
# 临时设置
$env:AOP_CLAUDE_CMD = "claude"

# 永久设置（添加到 $PROFILE）
echo '$env:AOP_CLAUDE_CMD = "claude"' >> $PROFILE
```

### Linux/macOS (Bash)

```bash
# 临时设置
export AOP_CLAUDE_CMD="claude"

# 永久设置
echo 'export AOP_CLAUDE_CMD="claude"' >> ~/.bashrc
```
