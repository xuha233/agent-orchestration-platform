<p align="center">
  <img src="https://img.shields.io/npm/v/agent-orchestration-platform" alt="npm version" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-green" alt="Providers: 5 built-in" />
</p>

<h1 align="center">AOP - Agent Orchestration Platform</h1>

<p align="center"><strong>统一的多 Agent 编排平台 — 工作流 + 执行，一套搞定</strong></p>

<p align="center"><a href="#快速开始">快速开始</a> | <a href="#命令概览">命令概览</a> | <a href="#provider-配置">Provider 配置</a></p>

---

## 一句话介绍

AOP 融合了 **MCO 的执行引擎** 和 **AAIF 的工作流方法论**：
- **并行执行** — 多 Agent 同时工作，wall-clock 时间 约等于 最慢 Agent
- **假设驱动** — 假设 验证 学习的迭代循环
- **即开即用** — 5 分钟上手，零配置可用

---

## 安装

```bash
# 从 GitHub 安装
git clone https://github.com/xuha233/agent-orchestration-platform.git
cd agent-orchestration-platform
pip install -e .
```

或使用一键安装脚本：
```bash
# macOS / Linux
./install.sh

# Windows PowerShell
.\install.ps1
```

---

## 快速开始

### 1. 检查环境

```bash
aop doctor
```

输出：
```
Provider Status:
  [OK] claude: available (v1.0.0)
  [OK] codex: available
  [--] gemini: not found
  [--] qwen: not found
```

### 2. 代码审查

```bash
aop review -p "Review for bugs" -P claude,codex
```

输出：
```
Running review with 2 providers...

Results:
  Duration: 45.2s
  Findings: 12 (3 high, 5 medium, 4 low)

Top findings:
  1. [HIGH] SQL injection in src/db/query.py:42
  2. [HIGH] Race condition in src/async/handler.py:108
  3. [MEDIUM] Missing input validation in src/api/user.py:23
```

### 3. 项目初始化

```bash
aop init my-project
```

创建：
```
my-project/
  .aop.yaml       # 配置文件
  runs/           # 运行记录
  hypotheses.md   # 假设模板
```

### 4. 假设驱动开发

```bash
# 创建假设
aop hypothesis create "添加缓存可减少 50% 响应时间" -p quick_win

# 查看假设列表
aop hypothesis list

# 更新假设状态
aop hypothesis update H-001 --state validated
```

### 5. 项目评估

```bash
aop project assess --problem-clarity low --tech-novelty high
```

输出：
```
Project Type: exploratory
Recommended Team: product_owner, data, ml
Strategy: fast-fail, learning-focused
```

---

## 命令概览

| 命令 | 用途 | 示例 |
|------|------|------|
| aop doctor | 检查环境 | aop doctor --json |
| aop init | 初始化项目 | aop init my-project |
| aop review | 代码审查 | aop review -p "Review for bugs" |
| aop run | 执行任务 | aop run -p "Summarize architecture" |
| aop hypothesis | 假设管理 | aop hypothesis create "..." |
| aop project | 项目评估 | aop project assess |
| aop learning | 学习捕获 | aop learning capture --phase explore |

---

## 使用场景

| 场景 | 命令 |
|------|------|
| 新项目初始化 | aop init my-project && cd my-project |
| 代码审查 | aop review -p "Review for security issues" -P claude,codex |
| 多 Agent 任务 | aop run -p "Analyze architecture" -P claude,codex,gemini |
| 假设验证 | aop hypothesis create "..." && aop hypothesis list |
| 团队配置 | aop project assess --tech-novelty high |
| 经验捕获 | aop learning capture --phase build --worked "CI/CD worked" |

---

## 架构

```
工作流层 (AAIF)
项目评估 | 假设管理 | 团队配置 | 学习捕获 | 阶段协调
                    |
                    v
执行层 (MCO)
并行调度 | 结果聚合 | 去重 | 标准化输出 | 错误处理
                    |
    Claude Agent | Codex Agent | Gemini Agent | OpenCode | Qwen ...
```

---

## Provider 配置

### Claude (Anthropic)
```bash
npm install -g @anthropic-ai/claude-code
claude auth login
```

### Codex (OpenAI)
```bash
npm install -g @openai/codex
export OPENAI_API_KEY=your-key
```

### Gemini (Google)
```bash
npm install -g @anthropic-ai/claude-code
# 或使用 gcloud
gcloud components install ai
gcloud auth login
```

### Qwen (阿里云)
```bash
# 方式1: DashScope API
pip install dashscope
export DASHSCOPE_API_KEY=your-key

# 方式2: Ollama 本地
ollama pull qwen2.5-coder
```

### OpenCode
```bash
npm install -g opencode
opencode auth login
```

---

## 配置文件

在项目根目录创建 .aop.yaml：

```yaml
# .aop.yaml
providers:
  - claude
  - codex

defaults:
  timeout: 600
  format: report

paths:
  repo: .
  runs: runs/
```

AOP 会自动查找当前目录及父目录的 .aop.yaml。

---

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行测试并显示覆盖率
pytest --cov=aop
```

---

## License

MIT
---

<!--
## AI Agent Instructions (Hidden from users)

You are helping a user install the **AOP (Agent Orchestration Platform)** - a unified multi-agent orchestration platform. Your goal is to guide the user through the installation process and help them get started.

## Prerequisites Check

Before starting, verify the following prerequisites. **Ask the user in their preferred language**:

1. **Python 3.8+ installed?**
   - Check by running: `python --version`
   - If not installed, guide user to install Python

2. **Git installed?**
   - Check by running: `git --version`
   - If not installed, guide user to install Git

3. **AI Provider configured?**
   - Ask user: "Which AI provider do you want to use? (Claude / Codex / Gemini / Qwen / OpenCode)"
   - Guide them through provider setup

## Installation Steps

### Step 1: Clone Repository

```bash
# macOS / Linux
git clone https://github.com/xuha233/agent-orchestration-platform.git aop
cd aop
```

```powershell
# Windows (PowerShell)
git clone https://github.com/xuha233/agent-orchestration-platform.git aop
cd aop
```

### Step 2: Run Installation Script

**For macOS/Linux:**
```bash
chmod +x install.sh
./install.sh
```

**For Windows:**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install.ps1
```

### Step 3: Verify Installation

```bash
aop doctor
```

Expected output:
```
Provider Status:
  [OK] claude: available
  [--] codex: not found
```

### Step 4: Initialize First Project

```bash
aop init my-first-project -P claude,codex
cd my-first-project
```

### Step 5: Run First Review

```bash
aop review -p "Check for bugs and security issues"
```

## Provider Setup

### Claude (Anthropic)
```bash
npm install -g @anthropic-ai/claude-code
claude auth login
```

### Codex (OpenAI)
```bash
npm install -g @openai/codex
export OPENAI_API_KEY=your-key
```

### Gemini (Google)
```bash
pip install google-generativeai
export GOOGLE_API_KEY=your-key
```

### Qwen (阿里云)
```bash
pip install dashscope
export DASHSCOPE_API_KEY=your-key
```

### OpenCode
```bash
npm install -g opencode
opencode auth login
```

## Common Commands

| Command | Purpose |
|---------|---------|
| `aop doctor` | Check environment and providers |
| `aop init <name>` | Initialize new project |
| `aop review -p "..."` | Run multi-agent code review |
| `aop run -p "..."` | Execute multi-agent task |
| `aop hypothesis create "..."` | Create hypothesis |
| `aop hypothesis list` | List hypotheses |
| `aop project assess` | Assess project complexity |
| `aop learning capture` | Capture learnings |

## Troubleshooting

### Common Issues

1. **"aop: command not found"**
   - Ensure `pip install -e .` completed successfully
   - Check PATH includes Python scripts directory
   - Try: `python -m aop.cli.main doctor`

2. **Provider not available**
   - Run: `aop doctor --fix` for suggestions
   - Ensure provider CLI is installed and authenticated

3. **Permission denied on install script**
   - Run: `chmod +x install.sh` (macOS/Linux)
   - Or run as administrator (Windows)

## Summary for AI Agents

1. **Check prerequisites** → Python 3.8+, Git
2. **Clone repository** → `git clone ...`
3. **Run installation** → `./install.sh` or `.\install.ps1`
4. **Verify installation** → `aop doctor`
5. **Configure provider** → Guide user through provider setup
6. **Initialize project** → `aop init my-project`
7. **Run first review** → `aop review -p "..."`

**Remember**: Always communicate with the user in their preferred language.

---

End of AI Agent Instructions
-->
