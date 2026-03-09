<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-orange" alt="Providers: 5 built-in" />
  <img src="https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey" alt="Platform: Windows | macOS | Linux" />
  <img src="https://img.shields.io/badge/version-v0.4.0-blueviolet" alt="Version: v0.4.0" />
  <img src="https://img.shields.io/badge/tests-288%20passed-brightgreen" alt="Tests: 288 passed" />
</p>

<h1 align="center">AOP - Agent Orchestration Platform</h1>

<p align="center">
  <strong>自动化多 Agent 协作平台</strong><br>
  <em>一行命令。Agent 团队。搞定。</em>
</p>

<p align="center">
  <a href="#-一行命令agent-团队干活">快速开始</a> • 
  <a href="#-选-mco-还是-aop">对比 MCO</a> • 
  <a href="#-核心功能">核心功能</a> • 
  <a href="#-命令参考">命令一览</a>
</p>

---

[English](README.md) | 简体中文

---

## 🚀 一行命令。Agent 团队。搞定。

```bash
aop agent run "做一个电商系统"
```

AOP 会自动：
1. **澄清需求**（不确定会追问）
2. **生成假设**（可验证的假设）
3. **拆解任务**（并行执行计划）
4. **调度 Agent**（多个 Provider 协同工作）
5. **验证结果**（自动验证，收集证据）
6. **提取学习**（沉淀知识供后续项目使用）

**你说需求，AOP 帮你干完。**

---

## 🏃 快速开始

### 开箱即用（推荐）

```bash
# 安装
pip install git+https://github.com/xuha233/agent-orchestration-platform.git

# 检查环境
aop doctor

# 一行命令启动 Agent 团队
aop agent run "帮我分析这个项目的架构"
```

### 交互式模式

```bash
# AOP 会追问澄清问题
aop agent run -i "做一个 REST API"
```

### 恢复中断的工作

```bash
# 列出所有冲刺
aop agent list

# 恢复指定冲刺
aop agent run -r sprint-abc123
```

### 高级用法

需要精细控制时：

```bash
# 多 Agent 代码审查
aop review -p "检查安全问题" -P claude,gemini --synthesize

# 通用多 Provider 任务
aop run -p "分析架构" -P claude,codex

# Web Dashboard
aop dashboard --open-browser
```

---

## ⚡ 选 MCO 还是 AOP？

| 你的场景 | 推荐 |
|---------|------|
| "我想说一句话，Agent 自己干活" | **AOP** `aop agent run "..."` |
| "我要精细控制每个参数" | **MCO** 更灵活的命令行 |
| "我要 CI/CD 集成代码审查" | **MCO** SARIF 输出成熟 |
| "我要开发大项目，需要知识沉淀" | **AOP** 自动学习提取 |
| "我经常被打断，需要恢复" | **AOP** Sprint 持久化恢复 |

**一句话总结：MCO 是引擎，AOP 是自动化流水线。**

---

## ✨ 核心功能

### 🤖 全自动化

| 你需要的 | AOP 做的 |
|---------|---------|
| 让多个 AI 同时工作 | ✅ 并行执行，自动去重 |
| 不想手动管理超时 | ✅ 动态超时延长，Agent 自己申请延期 |
| 想要自动化验证 | ✅ 智能验证器，自动收集证据 |
| 需要知识沉淀 | ✅ 学习提取，跨项目共享 |
| 希望能恢复中断的工作 | ✅ Sprint 持久化，随时恢复 |

### 🧠 智能层

**代码库自动分析**
- 语言/框架/架构自动识别
- 项目复杂度评估
- 团队配置建议

**假设驱动开发 (HDD)**
- 从需求生成可验证假设
- 依赖感知的执行顺序
- 跟踪验证状态

### 📚 知识层

**学习自动提取**
- 什么有效 / 什么无效
- 关键洞察和风险
- 改进建议

**跨项目知识库**
- 相似问题匹配
- 历史解决方案复用

---

## 📋 命令参考

### 🚀 Agent 自动化（开箱即用）

| 命令 | 用途 |
|------|------|
| `aop agent run "任务"` | 🌟 一行命令，全自动执行 |
| `aop agent run -i "任务"` | 交互式追问模式 |
| `aop agent run -r <sprint-id>` | 恢复中断的冲刺 |
| `aop agent status` | 查看当前冲刺状态 |
| `aop agent next` | 获取 AI 建议的下一步 |
| `aop agent list` | 列出所有冲刺 |

### 🔧 精细控制

| 命令 | 用途 |
|------|------|
| `aop review -p "..."` | 多 Agent 代码审查 |
| `aop run -p "..."` | 执行多 Agent 任务 |
| `aop dashboard` | 启动 Web UI |

### 🧠 假设与学习

| 命令 | 用途 |
|------|------|
| `aop hypothesis create "..."` | 创建假设 |
| `aop hypothesis list` | 列出假设 |
| `aop hypothesis update H-xxx -s validated` | 更新状态 |
| `aop learning capture` | 捕获学习 |
| `aop learning export` | 导出为 Markdown |

### 🏗 项目与环境

| 命令 | 用途 |
|------|------|
| `aop doctor` | 检查环境和 Provider 状态 |
| `aop init <name>` | 初始化新项目 |
| `aop project assess` | 评估项目复杂度 |

### 🎯 Orchestrator 管理

| 命令 | 用途 |
|------|------|
| `aop orchestrator doctor` | 检测可用的 Orchestrator |
| `aop orchestrator list` | 列出可用的 Orchestrator |
| `aop orchestrator use <type>` | 设置项目的 Orchestrator |

---

## 🔌 支持 Provider

| Provider | 安装命令 |
|----------|---------|
| Claude | `npm install -g @anthropic-ai/claude-code` |
| Codex | `npm install -g @openai/codex` |
| Gemini | `pip install google-generativeai` |
| Qwen | `pip install dashscope` |
| OpenCode | `npm install -g opencode` |

---

## 🏗 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Automation Layer                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  Agent      │ │  Hypothesis │ │  Learning   │            │
│  │  Driver     │ │  Generator  │ │  Extractor  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   Auto      │ │  Codebase   │ │   Sprint    │            │
│  │  Validator  │ │   Analyzer  │ │ Persistence │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                   Orchestrator Layer                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │Claude-Code  │ │  OpenCode   │ │  OpenClaw   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐                                            │
│  │  API Mode   │  ← 直接 LLM API 调用                       │
│  └─────────────┘                                            │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                    Execution Layer                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  Parallel   │ │   Timeout   │ │   Report    │            │
│  │  Dispatch   │ │   Manager   │ │  Formatters │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────┬───────────┼───────────┬─────────┐
        ▼         ▼           ▼           ▼         ▼
    ┌───────┐ ┌───────┐ ┌───────┐ ┌────────┐ ┌──────┐
    │ Claude│ │ Codex │ │Gemini │ │OpenCode│ │ Qwen │
    └───────┘ └───────┘ └───────┘ └────────┘ └──────┘
```

---

## 📊 测试覆盖

| 模块 | 测试数 | 状态 |
|------|-------|------|
| TimeoutManager | 13 | ✅ |
| HypothesisGraph | 14 | ✅ |
| KnowledgeBase | 14 | ✅ |
| AutoValidator | 15+ | ✅ |
| LearningExtractor | 12+ | ✅ |
| CodebaseAnalyzer | 6 | ✅ |
| TaskScheduler | 7 | ✅ |
| SprintPersistence | 4 | ✅ |

**总计：288 tests passing**

---

## 🛠 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check src/aop/
mypy src/aop/
```

---

## 🙏 致谢

AOP 的执行层灵感来自 [MCO (Multi-CLI Orchestrator)](https://github.com/mco-org/mco) 项目的概念。感谢 MCO 团队在多 Agent 编排模式上的优秀工作。

工作流方法论基于 [AAIF (AI Agile Incubation Framework)](https://github.com/xuha233/agent-team-template)，提供假设驱动开发方法。

---

## 📚 相关项目

| 项目 | 描述 |
|------|------|
| [MCO](https://github.com/mco-org/mco) | Multi-CLI Orchestrator — 执行引擎灵感来源 |
| [AAIF](https://github.com/xuha233/agent-team-template) | AI Agile Incubation Framework |
| [OpenClaw](https://github.com/open-claw/open-claw) | AI Agent 桌面客户端 |

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

---

<!--
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
                    🤖 AI AGENT INSTRUCTIONS 🤖
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
-->

## 🤖 AI Agent 安装指南

> 这部分是给 AI 助手（Claude, GPT, OpenCode 等）的指导。如果你是人类用户，可以忽略。

### 概述

你正在帮助用户安装 **AOP (Agent Orchestration Platform)** — 一个自动化优先的多 Agent 协作平台。

### 前置检查

**用用户的语言询问：**

1. **Python 3.10+?** → 运行 `python --version`
2. **Git 已安装?** → 运行 `git --version`
3. **选择哪个 Provider?** → Claude / Codex / Gemini / Qwen / OpenCode
4. **安装到哪个目录?**

### 安装步骤

```bash
# 1. 克隆
git clone https://github.com/xuha233/agent-orchestration-platform.git aop
cd aop

# 2. 安装
pip install -e .

# 3. 验证
aop doctor
```

### Provider 配置

| Provider | 配置命令 |
|----------|---------|
| Claude | `claude auth login` |
| Codex | `export OPENAI_API_KEY=xxx` |
| Gemini | `export GOOGLE_API_KEY=xxx` |
| Qwen | `export DASHSCOPE_API_KEY=xxx` |
| OpenCode | 无需配置 |

### 快速开始

```bash
# 检测可用的 Orchestrator
aop orchestrator doctor

# 一行命令启动
aop agent run "你的任务描述"
```

### 常见问题

- **Git clone 失败** → 检查网络，或手动下载 ZIP
- **Provider 显示 "Not found"** → 安装对应 CLI，配置 API Key
- **`aop` 命令找不到** → 确保 pip install 成功，检查 PATH


### OpenClaw Skill 安装（可选）

如果用户使用 [OpenClaw](https://github.com/open-claw/open-claw)，可以安装 AOP 敏捷教练 Skill：

**检测操作系统并提供对应命令：**

```bash
# 检测操作系统
# Windows: $env:OS 或 ver
# macOS/Linux: uname -a

# 跨平台安装命令（Python 方式，最通用）
python -c "
import shutil
from pathlib import Path

# 源目录（AOP 项目中的 skill）
src = Path('skills/aop-coach')

# 目标目录
if Path.home().name == 'Users' or Path.home().name == 'home':
    dst = Path.home() / '.openclaw' / 'skills' / 'aop-coach'
else:
    dst = Path.home() / '.openclaw' / 'skills' / 'aop-coach'

dst.mkdir(parents=True, exist_ok=True)

for f in ['SKILL.md', 'README.md']:
    shutil.copy(src / f, dst / f)

(dst / 'references').mkdir(exist_ok=True)
for f in ['TEAM.md', 'WORKFLOW.md']:
    shutil.copy(src / 'references' / f, dst / 'references' / f)

print(f'Skill installed to: {dst}')
"
```

**或者使用平台原生命令：**

Windows PowerShell:
```powershell
$src = "skills\aop-coach"
$dst = "$env:USERPROFILE\.openclaw\skills\aop-coach"
New-Item -ItemType Directory -Path $dst -Force | Out-Null
Copy-Item -Path "$src\SKILL.md", "$src\README.md" -Destination $dst
New-Item -ItemType Directory -Path "$dst\references" -Force | Out-Null
Copy-Item -Path "$src\references\TEAM.md", "$src\references\WORKFLOW.md" -Destination "$dst\references"
Write-Host "Skill installed to: $dst"
```

macOS/Linux:
```bash
src="skills/aop-coach"
dst="$HOME/.openclaw/skills/aop-coach"
mkdir -p "$dst/references"
cp "$src/SKILL.md" "$src/README.md" "$dst/"
cp "$src/references/TEAM.md" "$src/references/WORKFLOW.md" "$dst/references/"
echo "Skill installed to: $dst"
```

**安装后告知用户：**
- 在 OpenClaw 中输入 `-aop status` 测试
- 详细使用方法见 `skills/aop-coach/README.md`

---
### 安装完成后

**询问用户：** "安装完成！你想用 AOP 做什么项目？"

**运行 Agent：**
```bash
aop agent run "[用户的描述]"
```

---

<!-- End of AI Agent Instructions -->
