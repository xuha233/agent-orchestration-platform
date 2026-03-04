<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-orange" alt="Providers: 5 built-in" />
  <img src="https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey" alt="Platform: Windows | macOS | Linux" />
  <img src="https://img.shields.io/badge/version-v0.3.0-blueviolet" alt="Version: v0.3.0" />
  <img src="https://img.shields.io/badge/tests-288%20passed-brightgreen" alt="Tests: 288 passed" />
</p>

<h1 align="center">AOP - Agent Orchestration Platform</h1>

<p align="center">
  <strong>自动化多 Agent 协作平台</strong><br>
  <em>Workflow + Execution + LLM Intelligence, All in One</em>
</p>

<p align="center">
  <a href="#-为什么选择-aop">为什么选择</a> • 
  <a href="#-vs-mco">对比 MCO</a> • 
  <a href="#-快速开始">快速开始</a> • 
  <a href="#-核心功能">核心功能</a>
</p>

---

[English](README.md) | 简体中文

---

## 🚀 为什么选择 AOP?

**一条命令，多个 Agent 并行工作。**

```
你的想法 → AOP → 多个 Agent 并行执行 → 自动聚合结果
```

AOP 是一个**自动化优先**的多 Agent 协作平台，不仅仅是调度器：

| 你需要的 | AOP 提供的 |
|---------|-----------|
| 让多个 AI 同时工作 | ✅ 并行执行，自动去重 |
| 不想手动管理超时 | ✅ 动态超时延长，Agent 自己申请延期 |
| 想要自动化验证 | ✅ 智能验证器，自动收集证据 |
| 需要知识沉淀 | ✅ 学习提取，跨项目共享 |
| 项目复杂度评估 | ✅ 自动分析，团队配置建议 |
| 希望能恢复中断的工作 | ✅ Sprint 持久化，随时恢复 |

---

## ⚡ AOP vs MCO

MCO (Multi-CLI Orchestrator) 是优秀的执行引擎，AOP 在此基础上增加了**完整的自动化工作流层**：

| 特性 | MCO | AOP |
|------|-----|-----|
| **执行模型** | 并行调度 ✅ | 并行调度 ✅ |
| **超时管理** | 固定超时 | 🆕 **动态延长**：Agent 可申请延期 |
| **假设管理** | ❌ | ✅ 假设驱动开发 (HDD) |
| **学习沉淀** | ❌ | ✅ 自动提取，跨项目共享 |
| **项目评估** | ❌ | ✅ 复杂度分析，团队建议 |
| **代码分析** | ❌ | ✅ 语言/框架/架构自动识别 |
| **智能验证** | ❌ | ✅ 自动验证假设，收集证据 |
| **知识库** | ❌ | ✅ 相似问题匹配，解决方案复用 |
| **状态恢复** | ❌ | ✅ Sprint 持久化，中断恢复 |
| **LLM 集成** | CLI 调用 | ✅ 原生 LLM 客户端 (Claude/Local) |
| **依赖调度** | ❌ | ✅ 拓扑排序，批量并行 |

**一句话总结**：MCO 是引擎，AOP 是完整的自动化流水线。

---

## 🏃 快速开始

### 一键安装

把这个提示词发给你的 AI 助手（Claude / GPT / OpenCode 等）：

```
帮我安装 AOP：https://github.com/xuha233/agent-orchestration-platform
阅读 README 中的 AI Agent 安装指南，帮我完成安装和配置。
```

### 手动安装

```bash
# 安装
pip install git+https://github.com/xuha233/agent-orchestration-platform.git

# 验证环境
aop doctor

# 运行第一个任务
aop run -p "分析当前项目的架构" -P claude,gemini
```

---

## ✨ 核心功能

### 🤖 自动化执行层

#### 动态超时延长

Agent 执行复杂任务时，可以申请延长超时：

```python
# Agent 输出结构化请求
[TIMEOUT_EXTENSION_REQUEST]
{"requested_seconds": 300, "reason": "需要更多时间分析", "progress_summary": "已完成 50%"}
[/TIMEOUT_EXTENSION_REQUEST]

# 主 Agent 自动批准，Agent 继续执行
```

**优势**：不再因为固定超时而丢失已完成的工作。

#### 假设依赖图

根据假设之间的依赖关系，自动规划执行顺序：

```python
from aop.workflow.hypothesis.graph import HypothesisGraph

graph = HypothesisGraph()
graph.add_hypothesis("h1", dependencies=[])     # 先执行
graph.add_hypothesis("h2", dependencies=["h1"]) # h1 完成后执行
graph.add_hypothesis("h3", dependencies=["h1"]) # 与 h2 并行

batches = graph.get_execution_order()
# [["h1"], ["h2", "h3"]]  ← h2 和 h3 并行执行
```

### 🧠 智能分析层

#### 代码库自动分析

自动识别项目的语言、框架、架构模式：

```python
from aop.agent.analyzer import CodebaseAnalyzer

analyzer = CodebaseAnalyzer()
info = analyzer.analyze(".")
# Language: python
# Framework: fastapi
# Patterns: ["MVC", "Layered"]
# Entry points: ["main.py", "app.py"]
```

#### 项目复杂度评估

评估项目复杂度，获得团队配置建议：

```bash
aop project assess \
  --problem-clarity medium \
  --data-availability high \
  --tech-novelty low \
  --business-risk medium
```

| 项目类型 | 特征 | 推荐团队 |
|---------|------|---------|
| `exploratory` | 高新颖性，低数据 | 研究型团队 |
| `optimization` | 目标清晰，有现有代码 | 性能团队 |
| `transformation` | 中等风险，中等清晰度 | 平衡团队 |
| `compliance_sensitive` | 高业务风险 | 安全团队 |

### 📚 知识管理层

#### 学习自动提取

从执行结果中自动提取学习：

```python
from aop.agent.learning import LearningExtractor

extractor = LearningExtractor()
learnings = extractor.extract(results)
# 自动识别：
# - 什么有效
# - 关键洞察
# - 风险识别
# - 改进建议
```

#### 跨项目知识库

相似问题自动匹配历史解决方案：

```python
from aop.agent.knowledge import KnowledgeBase

kb = KnowledgeBase()
similar = kb.find_similar({
    "framework": "fastapi",
    "error_type": "validation"
})
# 返回历史上解决过类似问题的方案
```

### 🔄 工作流层

#### 假设驱动开发 (HDD)

```bash
# 创建假设
aop hypothesis create "添加缓存可将响应时间降低 50%" -p quick_win

# 列出假设
aop hypothesis list --state pending

# 更新状态
aop hypothesis update H-D5BFC589 -s validated
```

**工作流**：假设 → 验证 → 学习 → 迭代

| 状态 | 描述 |
|------|------|
| `pending` | 待验证 |
| `validated` | 验证通过 |
| `refuted` | 已反驳 |
| `inconclusive` | 结果不明确 |

#### Sprint 持久化

中断的工作可以随时恢复：

```python
from aop.agent.persistence import SprintPersistence

persistence = SprintPersistence()
persistence.save(sprint_context)  # 保存当前状态

# 稍后恢复
loaded = persistence.load("sprint-123")
active = persistence.get_latest_active()
```

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

## 📋 命令参考

| 命令 | 用途 |
|------|------|
| `aop doctor` | 检查环境和 Provider 状态 |
| `aop init <name>` | 初始化新项目 |
| `aop review -p "..."` | 多 Agent 代码审查 |
| `aop run -p "..."` | 执行多 Agent 任务 |
| `aop hypothesis create "..."` | 创建假设 |
| `aop hypothesis list` | 列出假设 |
| `aop hypothesis update H-xxx -s validated` | 更新假设状态 |
| `aop learning capture` | 捕获学习 |
| `aop learning export` | 导出学习到 Markdown |
| `aop project assess` | 评估项目复杂度 |

---

## 🏗 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Layer                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Hypothesis  │ │  Learning   │ │    Team     │            │
│  │  Manager    │ │    Log      │ │  Config     │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Automation Layer (NEW)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   Auto      │ │   Codebase  │ │   Task      │            │
│  │  Validator  │ │   Analyzer  │ │  Scheduler  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐                            │
│  │ Knowledge   │ │   Sprint    │                            │
│  │    Base     │ │ Persistence │                            │
│  └─────────────┘ └─────────────┘                            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Execution Layer                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  Orchestrator│ │   Timeout   │ │   Report    │            │
│  │   Runtime    │ │   Manager   │ │  Formatters │            │
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

AOP 的执行引擎灵感来自 [MCO (Multi-CLI Orchestrator)](https://github.com/mco-org/mco) 项目。感谢 MCO 团队在多 Agent 编排模式上的优秀工作。

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

### 初始化项目

```bash
aop init my-project -P claude,gemini
cd my-project

# 创建第一个假设
aop hypothesis create "如果我[用户想法]，那么[预期结果]" -p quick_win
```

### 常见问题

- **Git clone 失败** → 检查网络，或手动下载 ZIP
- **Provider 显示 "Not found"** → 安装对应 CLI，配置 API Key
- **`aop` 命令找不到** → 确保 pip install 成功，检查 PATH

### 安装完成后

**询问用户：** "安装完成！你想用 AOP 做什么项目？"

**根据回答创建假设：**
```bash
aop hypothesis create "如果[想法]，那么[结果]" -p quick_win
```

---

<!-- End of AI Agent Instructions -->
