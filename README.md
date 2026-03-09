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
  <strong>Automated Multi-Agent Orchestration Platform</strong><br>
  <em>One Command. Agent Team. Done.</em>
</p>

<p align="center">
  <a href="#-one-line-agent-team">Quick Start</a> • 
  <a href="#-vs-mco">vs MCO</a> • 
  <a href="#-core-features">Core Features</a> • 
  <a href="#-command-reference">Commands</a>
</p>

---

English | [简体中文](README.zh-CN.md)

---

## 🚀 One Line. Agent Team. Done.

```bash
aop agent run "Build an e-commerce system"
```

AOP automatically:
1. **Clarifies requirements** (asks follow-up questions if unclear)
2. **Generates hypotheses** (testable assumptions)
3. **Decomposes tasks** (parallel execution plan)
4. **Dispatches agents** (multiple providers working together)
5. **Validates results** (auto-verification with evidence)
6. **Extracts learnings** (knowledge for future projects)

**You state the goal. AOP handles the rest.**

---

## 🏃 Quick Start

### Zero-Config (Recommended)

```bash
# Install
pip install git+https://github.com/xuha233/agent-orchestration-platform.git

# Check environment
aop doctor

# One-liner to launch Agent team
aop agent run "Help me analyze this project's architecture"
```

### Interactive Mode

```bash
# AOP will ask clarifying questions
aop agent run -i "Build a REST API"
```

### Resume Interrupted Work

```bash
# List all sprints
aop agent list

# Resume a specific sprint
aop agent run -r sprint-abc123
```

### Advanced Usage

For fine-grained control:

```bash
# Multi-agent code review
aop review -p "Check for security issues" -P claude,gemini --synthesize

# General multi-provider task
aop run -p "Analyze architecture" -P claude,codex

# Web Dashboard
aop dashboard --open-browser
```

---

## ⚡ MCO or AOP?

| Your Scenario | Recommendation |
|--------------|----------------|
| "I want to say one sentence, agents do the work" | **AOP** `aop agent run "..."` |
| "I need fine-grained control over every parameter" | **MCO** more flexible CLI |
| "CI/CD integration with SARIF output" | **MCO** mature SARIF support |
| "Building a large project, need knowledge retention" | **AOP** auto learning extraction |
| "My work gets interrupted frequently" | **AOP** Sprint persistence + resume |

**In one sentence: MCO is the engine. AOP is the automation pipeline.**

---

## ✨ Core Features

### 🤖 Full Automation

| What You Need | What AOP Does |
|--------------|----------------|
| Multiple agents working together | ✅ Parallel execution with auto-deduplication |
| No manual timeout management | ✅ Dynamic timeout extension — agents request their own |
| Automated validation | ✅ Smart validator with evidence collection |
| Knowledge retention | ✅ Learning extraction, cross-project sharing |
| Resume interrupted work | ✅ Sprint persistence, recover anytime |

### 🧠 Intelligence Layer

**Codebase Auto-Analysis**
- Language/framework/architecture auto-detection
- Project complexity assessment
- Team configuration recommendations

**Hypothesis-Driven Development (HDD)**
- Generate testable assumptions from requirements
- Dependency-aware execution ordering
- Track validation status

### 📚 Knowledge Layer

**Auto Learning Extraction**
- What worked / What didn't
- Key insights and risks
- Suggestions for improvement

**Cross-Project Knowledge Base**
- Similar problem matching
- Historical solution reuse

---

## 📋 Command Reference

### 🚀 Agent Automation (Zero-Config)

| Command | Purpose |
|---------|---------|
| `aop agent run "task"` | 🌟 One-liner, fully automated execution |
| `aop agent run -i "task"` | Interactive mode with follow-up questions |
| `aop agent run -r <sprint-id>` | Resume interrupted sprint |
| `aop agent status` | View current sprint status |
| `aop agent next` | Get AI-suggested next steps |
| `aop agent list` | List all sprints |

### 🔧 Fine-Grained Control

| Command | Purpose |
|---------|---------|
| `aop review -p "..."` | Multi-agent code review |
| `aop run -p "..."` | Execute multi-agent task |
| `aop dashboard` | Launch web UI |

### 🧠 Hypothesis & Learning

| Command | Purpose |
|---------|---------|
| `aop hypothesis create "..."` | Create hypothesis |
| `aop hypothesis list` | List hypotheses |
| `aop hypothesis update H-xxx -s validated` | Update status |
| `aop learning capture` | Capture learning |
| `aop learning export` | Export to Markdown |

### 🏗 Project & Environment

| Command | Purpose |
|---------|---------|
| `aop doctor` | Check environment and provider status |
| `aop init <name>` | Initialize new project |
| `aop project assess` | Assess project complexity |

### 🎯 Orchestrator Management

| Command | Purpose |
|---------|---------|
| `aop orchestrator doctor` | Detect available orchestrators |
| `aop orchestrator list` | List available orchestrators |
| `aop orchestrator use <type>` | Set project orchestrator |

---

## 🔌 Supported Providers

| Provider | Install Command |
|----------|-----------------|
| Claude | `npm install -g @anthropic-ai/claude-code` |
| Codex | `npm install -g @openai/codex` |
| Gemini | `pip install google-generativeai` |
| Qwen | `pip install dashscope` |
| OpenCode | `npm install -g opencode` |

---

## 🏗 Architecture

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
│  │  API Mode   │  ← Direct LLM API calls                    │
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

## 📊 Test Coverage

| Module | Tests | Status |
|--------|-------|--------|
| TimeoutManager | 13 | ✅ |
| HypothesisGraph | 14 | ✅ |
| KnowledgeBase | 14 | ✅ |
| AutoValidator | 15+ | ✅ |
| LearningExtractor | 12+ | ✅ |
| CodebaseAnalyzer | 6 | ✅ |
| TaskScheduler | 7 | ✅ |
| SprintPersistence | 4 | ✅ |

**Total: 288 tests passing**

---

## 🛠 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code check
ruff check src/aop/
mypy src/aop/
```

---

## 🙏 Acknowledgments

AOP's execution layer was inspired by concepts from the [MCO (Multi-CLI Orchestrator)](https://github.com/mco-org/mco) project. We gratefully acknowledge the MCO team for their excellent work in multi-agent orchestration patterns.

The workflow methodology is based on [AAIF (AI Agile Incubation Framework)](https://github.com/xuha233/agent-team-template), providing the hypothesis-driven development approach.

---

## 📚 Related Projects

| Project | Description |
|---------|-------------|
| [MCO](https://github.com/mco-org/mco) | Multi-CLI Orchestrator — Execution engine inspiration |
| [AAIF](https://github.com/xuha233/agent-team-template) | AI Agile Incubation Framework |
| [OpenClaw](https://github.com/open-claw/open-claw) | AI Agent desktop client |

---

## 📄 License

MIT License — See [LICENSE](LICENSE)

---

<!--
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
                    🤖 AI AGENT INSTRUCTIONS 🤖
░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
-->

## 🤖 AI Agent Installation Guide

> This section is for AI assistants (Claude, GPT, Copilot, OpenCode, etc.). If you're a human, you can skip this.

### Overview

You are helping install **AOP (Agent Orchestration Platform)** — an automation-first multi-agent orchestration platform.

### Prerequisites Check

**Ask the user in their preferred language:**

1. **Python 3.10+?** → Run `python --version`
2. **Git installed?** → Run `git --version`
3. **Which Provider?** → Claude / Codex / Gemini / Qwen / OpenCode
4. **Install directory?**

### Installation Steps

```bash
# 1. Clone
git clone https://github.com/xuha233/agent-orchestration-platform.git aop
cd aop

# 2. Install
pip install -e .

# 3. Verify
aop doctor
```

### Provider Configuration

| Provider | Config Command |
|----------|---------------|
| Claude | `claude auth login` |
| Codex | `export OPENAI_API_KEY=xxx` |
| Gemini | `export GOOGLE_API_KEY=xxx` |
| Qwen | `export DASHSCOPE_API_KEY=xxx` |
| OpenCode | No config needed |

### Claude Code Router (Optional)

**Ask the user:** "Do you want to use third-party model APIs (DeepSeek, Gemini, OpenRouter, etc.) with Claude Code?"

If **YES**:

1. **Read the agent guide:**
   - File: `docs/CCR_AGENT_GUIDE.md`
   - This file contains complete instructions for guiding users through CCR installation

2. **Plugin location:**
   - `plugins/claude-code-router.zip` - Source code package

3. **Follow the guide to:**
   - Install CCR: `npm install -g @musistudio/claude-code-router`
   - Ask user for: Provider, BaseURL, API Key, Models
   - Create `~/.claude-code-router/config.json`
   - Verify with `ccr code`

If **NO**, skip this step.



### Claude Code Router (Optional)

**Ask the user:** "Do you want to use third-party model APIs (DeepSeek, Gemini, OpenRouter, etc.) with Claude Code?"

If **YES**, install Claude Code Router:

1. **Read the installation guide:**
   - File: `docs/CCR_INSTALL_GUIDE.md`
   - Or visit: https://github.com/musistudio/claude-code-router

2. **Install CCR:**
   ```bash
   npm install -g @musistudio/claude-code-router
   ```

3. **Follow the guide to configure:**
   - Ask user for: Provider name, API Base URL, API Key, Models
   - Create `~/.claude-code-router/config.json`
   - Start with: `ccr code`

If **NO**, skip this step and continue below.

### Quick Start


### Quick Start

```bash
# Check available orchestrators
aop orchestrator doctor

# One-liner to start
aop agent run "Your task description here"
```

### Common Issues

- **Git clone fails** → Check network, or download ZIP manually
- **Provider shows "Not found"** → Install corresponding CLI, configure API Key
- **`aop` command not found** → Ensure pip install succeeded, check PATH

### After Installation

**Ask the user:** "Installation complete! What do you want to build with AOP?"

**Run the agent:**
```bash
aop agent run "[user's description]"
```

---

<!-- End of AI Agent Instructions -->
