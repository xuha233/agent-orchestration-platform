# AOP Review Skill

## Description

AOP (Agent Orchestration Platform) 是一个多 Agent 代码审查工具，支持并行执行多个 AI provider 进行代码审查和分析。

## Usage

```bash
# 执行代码审查
aop review -p "审查提示" --providers claude,codex

# 检查环境配置
aop doctor

# 创建假设
aop hypothesis create "Adding cache improves performance"

# 捕获学习记录
aop learning capture -p exploration -w "Daily standups" -i "Short cycles work"
```

## Commands

### Core Commands

- `aop doctor` - 检查 provider 环境和配置
- `aop review` - 执行多 Agent 代码审查
- `aop run` - 执行通用多 provider 任务
- `aop init` - 初始化 AOP 项目

### Hypothesis Commands

- `aop hypothesis create <statement>` - 创建新假设
- `aop hypothesis list` - 列出所有假设
- `aop hypothesis update <id> <state>` - 更新假设状态

### Learning Commands

- `aop learning capture` - 捕获学习记录

### Project Commands

- `aop project assess` - 评估项目复杂度

## Parameters

### Review Command

- `--prompt, -p` - 审查提示（必需）
- `--providers, -P` - Provider 列表，逗号分隔（默认：claude,codex）
- `--repo, -r` - 仓库根目录（默认：当前目录）
- `--target-paths` - 目标路径，逗号分隔
- `--timeout, -t` - 每个 provider 的超时时间（默认：600秒）
- `--stall-timeout` - 无输出时取消 provider 的超时时间
- `--format, -f` - 输出格式：report, json, summary, sarif, markdown-pr
- `--synthesize` - 运行额外的综合分析
- `--strict-contract` - 强制严格 findings JSON 契约

### Hypothesis Command

- `--priority, -p` - 优先级：quick_win 或 deep_dive

### Learning Capture Command

- `--phase, -p` - 阶段名称
- `--worked, -w` - 有效的做法（可多次指定）
- `--failed, -f` - 失败的做法（可多次指定）
- `--insight, -i` - 关键洞察（可多次指定）

## Exit Codes

- `0` - 成功
- `1` - 失败
- `2` - 配置/输入错误
- `3` - Provider 不可用或结果不确定

## Examples

```bash
# 基本审查
aop review -p "Review the authentication module"

# 使用多个 provider
aop review -p "Check for security issues" -P claude,gemini,qwen

# JSON 输出
aop review -p "Analyze performance" -f json

# SARIF 格式（用于 GitHub Code Scanning）
aop review -p "Review for bugs" --format sarif

# 创建假设
aop hypothesis create "Refactoring reduces bugs" -p deep_dive

# 捕获学习
aop learning capture -p implementation -w "Daily code reviews" -i "CI/CD helps"
```

## Configuration

AOP 使用 `.aop.yaml` 配置文件。通过 `aop init` 初始化项目时会自动创建。

## Persistence

- 假设和学习记录可以持久化到 `.aop/data/` 目录
- 数据以 JSON 格式存储
- 支持导出为 Markdown 格式
