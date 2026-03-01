<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-orange" alt="Providers: 5 built-in" />
</p>

<h1 align="center">AOP - Agent Orchestration Platform</h1>

<p align="center">
  <strong>统一的多 Agent 编排平台</strong><br>
  <em>工作流 + 执行，一套搞定</em>
</p>

<p align="center">
  <a href="#-核心功能">核心功能</a> • 
  <a href="#-快速开始">快速开始</a> • 
  <a href="#-命令概览">命令概览</a> • 
  <a href="#-使用场景">使用场景</a>
</p>

---

## 🎯 一句话介绍

AOP 融合了 **MCO 的执行引擎** 和 **AAIF 的工作流方法论**，让你的 AI Agent 团队高效协作。

---

## ✨ 核心功能

### 🤖 多 Agent 编排

```
┌─────────────────────────────────────────┐
│         Orchestrator (主 Agent)          │
│  • 创建假设                              │
│  • 分配任务                              │
│  • 监控执行                              │
│  • 验证结果                              │
│  • 捕获学习                              │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│Agent 1│ │Agent 2│ │Agent 3│ │Agent N│
│ UI    │ │Backend│ │Test   │ │ ...   │
└───────┘ └───────┘ └───────┘ └───────┘
```

**并行执行**: 多 Agent 同时工作，wall-clock 时间 ≈ 最慢 Agent

### 🕐 动态超时管理

**问题**: 固定超时导致子 Agent 任务失败  
**解决**: 子 Agent 自主申请和调整超时时间

```python
from aop.timeout_manager import SubagentTimeoutManager, TaskComplexity

manager = SubagentTimeoutManager("orchestrator-001")

# 子 Agent 申请初始超时
result = manager.request_timeout(
    agent_id="agent-ui-001",
    task_id="h-014",
    requested_timeout=900,  # 15 分钟
    reason="需要检查多个 UI 文件",
    complexity=TaskComplexity.MODERATE
)
# → 批准 900s

# 执行中申请延长
result = manager.request_extension(
    agent_id="agent-ui-001",
    task_id="h-014",
    additional_timeout=600,
    reason="发现需要探索项目结构",
    current_progress=0.7
)
# → 批准延长 600s
```

| 复杂度 | 默认超时 | 典型任务 |
|-------|---------|---------|
| SIMPLE | 5分钟 | 单文件修改 |
| MODERATE | 10分钟 | 多文件、UI组件 |
| COMPLEX | 30分钟 | 跨模块重构 |
| EXPLORATORY | 20分钟 | 代码审查 |

### 📊 假设驱动开发 (HDD)

**工作流**: 假设 → 验证 → 学习 → 迭代

```bash
# 创建假设
aop hypothesis create "添加缓存可减少 50% 响应时间" -p quick_win

# 查看假设列表
aop hypothesis list

# 更新状态
aop hypothesis update H-001 --state validated
```

### 🔍 多 Provider 代码审查

```bash
# 使用多个 AI Provider 并行审查
aop review -p "Review for bugs and security issues" -P claude,codex
```

```
Running review with 2 providers...
████████████████████████████████████████ 100%

Results:
  Duration: 45.2s
  Findings: 12 (3 high, 5 medium, 4 low)

Top findings:
  1. [HIGH] SQL injection in src/db/query.py:42
  2. [HIGH] Race condition in src/async/handler.py:108
```

### 🔌 5 个内置 Provider

| Provider | 类型 | 安装方式 |
|----------|------|----------|
| Claude | Anthropic | `npm install -g @anthropic-ai/claude-code` |
| Codex | OpenAI | `npm install -g @openai/codex` |
| Gemini | Google | `pip install google-generativeai` |
| Qwen | 阿里云 | `pip install dashscope` |
| OpenCode | 开源 | `npm install -g opencode` |

---

## 📦 安装

### 一键安装（推荐）

```bash
# macOS / Linux
git clone https://github.com/xuha233/agent-orchestration-platform.git aop
cd aop
chmod +x install.sh && ./install.sh
```

```powershell
# Windows PowerShell
git clone https://github.com/xuha233/agent-orchestration-platform.git aop
cd aop
.\install.ps1
```

### 手动安装

```bash
git clone https://github.com/xuha233/agent-orchestration-platform.git
cd agent-orchestration-platform
pip install -e .
```

---

## 🚀 快速开始

### 1. 检查环境

```bash
aop doctor
```

### 2. 初始化项目

```bash
aop init my-project -P claude,codex
cd my-project
```

### 3. 代码审查

```bash
aop review -p "Review for bugs and security issues"
```

### 4. 假设驱动开发

```bash
aop hypothesis create "添加缓存可减少 50% 响应时间" -p quick_win
aop hypothesis list
```

---

## 📋 命令概览

| 命令 | 用途 | 示例 |
|------|------|------|
| `aop doctor` | 检查环境和 Provider 状态 | `aop doctor --json` |
| `aop init` | 初始化新项目 | `aop init my-project -P claude,codex` |
| `aop review` | 多 Agent 代码审查 | `aop review -p "Review for bugs"` |
| `aop run` | 执行多 Agent 任务 | `aop run -p "Analyze architecture"` |
| `aop hypothesis` | 假设管理 | `aop hypothesis create "..."` |
| `aop project` | 项目评估 | `aop project assess` |
| `aop learning` | 学习捕获 | `aop learning capture --phase build` |

---

## 🎯 使用场景

| 场景 | 命令 |
|------|------|
| 新项目初始化 | `aop init my-project && cd my-project` |
| 代码审查 | `aop review -p "Review for security issues" -P claude,codex` |
| 多 Agent 任务 | `aop run -p "Analyze architecture" -P claude,codex,gemini` |
| 假设验证 | `aop hypothesis create "..." && aop hypothesis list` |
| 团队配置 | `aop project assess --tech-novelty high` |
| 经验捕获 | `aop learning capture --phase build` |

---

## ⚙️ 配置文件

在项目根目录创建 `.aop.yaml`：

```yaml
# .aop.yaml
providers:
  - claude
  - codex

defaults:
  timeout: 600        # 超时时间（秒）
  format: report      # 输出格式
  max_tokens: null    # 无限制

# 子 Agent 配置
subagent:
  default_timeout: 600       # 默认 10 分钟
  complex_task_timeout: 1800 # 复杂任务 30 分钟
  max_parallel: 3            # 最大并行数

# 任务前验证
validation:
  check_existing_code: true  # 检查代码是否已存在
  check_duplicate_tasks: true
  estimate_timeout: true     # 估算超时时间
```

---

## 🏗 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    工作流层 (AAIF)                           │
│  项目评估 │ 假设管理 │ 团队配置 │ 学习捕获 │ 阶段协调        │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    执行层 (MCO)                              │
│  并行调度 │ 结果聚合 │ 去重 │ 标准化输出 │ 错误处理         │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────┬───────────┼───────────┬─────────┐
        ▼         ▼           ▼           ▼         ▼
    ┌───────┐ ┌───────┐ ┌───────┐ ┌────────┐ ┌──────┐
    │ Claude│ │ Codex │ │Gemini │ │OpenCode│ │ Qwen │
    └───────┘ └───────┘ └───────┘ └────────┘ └──────┘
```

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [最佳实践](docs/best-practices.md) | 基于 PurifyAI 项目经验的实践指南 |
| [配置示例](examples/.aop.yaml.example) | 完整配置文件示例 |
| [动态超时管理](src/aop/timeout_manager.py) | 子 Agent 超时管理实现 |

---

## 📚 相关项目

| 项目 | 说明 |
|------|------|
| [MCO](https://github.com/xuha233/mco) | 多 Agent 代码审查执行引擎 |
| [AAIF](https://github.com/xuha233/agent-team-template) | AI 敏捷孵化框架 |
| [PurifyAI](https://github.com/xuha233/purifyai) | 使用 AOP 开发的实际项目 |

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件
