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
  <strong>Automated Multi-Agent Orchestration Platform</strong><br>
  <em>Workflow + Execution + LLM Intelligence, All in One</em>
</p>

<p align="center">
  <a href="#-why-aop">Why AOP</a> • 
  <a href="#-vs-mco">vs MCO</a> • 
  <a href="#-quick-start">Quick Start</a> • 
  <a href="#-core-features">Core Features</a>
</p>

---

English | [简体中文](README.zh-CN.md)

---

## 🚀 Why AOP?

**One command. Multiple agents working in parallel.**

```
Your Idea → AOP → Multiple Agents Execute in Parallel → Auto-Aggregated Results
```

AOP is an **automation-first** multi-agent orchestration platform — not just a scheduler:

| What You Need | What AOP Provides |
|--------------|-------------------|
| Multiple AI agents working together | ✅ Parallel execution with auto-deduplication |
| No manual timeout management | ✅ Dynamic timeout extension — agents request their own extensions |
| Automated validation | ✅ Smart validator with evidence collection |
| Knowledge retention | ✅ Learning extraction, cross-project sharing |
| Project complexity assessment | ✅ Auto-analysis with team configuration recommendations |
| Resume interrupted work | ✅ Sprint persistence, recover anytime |

---

## ⚡ AOP vs MCO

MCO (Multi-CLI Orchestrator) is an excellent execution engine. AOP builds on top with a **complete automation workflow layer**:

| Feature | MCO | AOP |
|---------|-----|-----|
| **Execution Model** | Parallel dispatch ✅ | Parallel dispatch ✅ |
| **Timeout Management** | Fixed timeout | 🆕 **Dynamic Extension**: Agents can request extensions |
| **Hypothesis Management** | ❌ | ✅ Hypothesis-Driven Development (HDD) |
| **Learning Capture** | ❌ | ✅ Auto-extraction, cross-project sharing |
| **Project Assessment** | ❌ | ✅ Complexity analysis, team recommendations |
| **Codebase Analysis** | ❌ | ✅ Language/framework/architecture auto-detection |
| **Smart Validation** | ❌ | ✅ Auto-validate hypotheses, collect evidence |
| **Knowledge Base** | ❌ | ✅ Similar problem matching, solution reuse |
| **State Recovery** | ❌ | ✅ Sprint persistence, resume interrupted work |
| **LLM Integration** | CLI calls | ✅ Native LLM client (Claude/Local) |
| **Dependency Scheduling** | ❌ | ✅ Topological sort, batch parallel execution |

**In one sentence**: MCO is the engine. AOP is the complete automation pipeline.

---

## 🏃 Quick Start

### One-Click Install

Send this prompt to your AI assistant (Claude / GPT / OpenCode / etc.):

```
Help me install AOP: https://github.com/xuha233/agent-orchestration-platform
Read the AI Agent Installation Guide in the README and help me complete the setup.
```

### Manual Install

```bash
# Install
pip install git+https://github.com/xuha233/agent-orchestration-platform.git

# Verify environment
aop doctor

# Run your first task
aop run -p "Analyze the current project architecture" -P claude,gemini
```

---

## ✨ Core Features

### 🤖 Automation Layer

#### Dynamic Timeout Extension

Agents can request timeout extensions for complex tasks:

```python
# Agent outputs structured request
[TIMEOUT_EXTENSION_REQUEST]
{"requested_seconds": 300, "reason": "Need more time for analysis", "progress_summary": "50% complete"}
[/TIMEOUT_EXTENSION_REQUEST]

# Main agent auto-approves, agent continues execution
```

**Benefit**: No more lost work due to fixed timeouts.

#### Hypothesis Dependency Graph

Automatically plan execution order based on hypothesis dependencies:

```python
from aop.workflow.hypothesis.graph import HypothesisGraph

graph = HypothesisGraph()
graph.add_hypothesis("h1", dependencies=[])     # Execute first
graph.add_hypothesis("h2", dependencies=["h1"]) # After h1
graph.add_hypothesis("h3", dependencies=["h1"]) # Parallel with h2

batches = graph.get_execution_order()
# [["h1"], ["h2", "h3"]]  ← h2 and h3 run in parallel
```

### 🧠 Intelligence Layer

#### Codebase Auto-Analysis

Automatically detect project language, framework, architecture patterns:

```python
from aop.agent.analyzer import CodebaseAnalyzer

analyzer = CodebaseAnalyzer()
info = analyzer.analyze(".")
# Language: python
# Framework: fastapi
# Patterns: ["MVC", "Layered"]
# Entry points: ["main.py", "app.py"]
```

#### Project Complexity Assessment

Evaluate project complexity and get team configuration recommendations:

```bash
aop project assess \
  --problem-clarity medium \
  --data-availability high \
  --tech-novelty low \
  --business-risk medium
```

| Project Type | Characteristics | Recommended Team |
|-------------|-----------------|------------------|
| `exploratory` | High novelty, low data | Research-focused |
| `optimization` | Clear goals, existing code | Performance team |
| `transformation` | Medium risk, medium clarity | Balanced team |
| `compliance_sensitive` | High business risk | Security-focused |

### 📚 Knowledge Layer

#### Auto Learning Extraction

Automatically extract learnings from execution results:

```python
from aop.agent.learning import LearningExtractor

extractor = LearningExtractor()
learnings = extractor.extract(results)
# Auto-identifies:
# - What worked
# - Key insights
# - Risk identification
# - Improvement suggestions
```

#### Cross-Project Knowledge Base

Auto-match historical solutions for similar problems:

```python
from aop.agent.knowledge import KnowledgeBase

kb = KnowledgeBase()
similar = kb.find_similar({
    "framework": "fastapi",
    "error_type": "validation"
})
# Returns historical solutions for similar problems
```

### 🔄 Workflow Layer

#### Hypothesis-Driven Development (HDD)

```bash
# Create hypothesis
aop hypothesis create "Adding cache reduces response time by 50%" -p quick_win

# List hypotheses
aop hypothesis list --state pending

# Update status
aop hypothesis update H-D5BFC589 -s validated
```

**Workflow**: Hypothesis → Validate → Learn → Iterate

| State | Description |
|-------|-------------|
| `pending` | Awaiting validation |
| `validated` | Confirmed through testing |
| `refuted` | Disproven |
| `inconclusive` | Results ambiguous, needs more data |

#### Sprint Persistence

Interrupted work can be resumed anytime:

```python
from aop.agent.persistence import SprintPersistence

persistence = SprintPersistence()
persistence.save(sprint_context)  # Save current state

# Resume later
loaded = persistence.load("sprint-123")
active = persistence.get_latest_active()
```

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

## 📋 Command Reference

| Command | Purpose |
|---------|---------|
| `aop doctor` | Check environment and provider status |
| `aop init <name>` | Initialize new project |
| `aop review -p "..."` | Multi-agent code review |
| `aop run -p "..."` | Execute multi-agent task |
| `aop hypothesis create "..."` | Create hypothesis |
| `aop hypothesis list` | List hypotheses |
| `aop hypothesis update H-xxx -s validated` | Update hypothesis status |
| `aop learning capture` | Capture learning |
| `aop learning export` | Export learnings to Markdown |
| `aop project assess` | Assess project complexity |

---

## 🏗 Architecture

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

AOP's execution engine is inspired by and builds upon concepts from the [MCO (Multi-CLI Orchestrator)](https://github.com/mco-org/mco) project. We gratefully acknowledge the MCO team for their excellent work in multi-agent orchestration patterns.

The workflow methodology layer is based on [AAIF (AI Agile Incubation Framework)](https://github.com/xuha233/agent-team-template), providing the hypothesis-driven development approach.

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

### Initialize Project

```bash
aop init my-project -P claude,gemini
cd my-project

# Create first hypothesis
aop hypothesis create "If I [user idea], then [expected outcome]" -p quick_win
```

### Common Issues

- **Git clone fails** → Check network, or download ZIP manually
- **Provider shows "Not found"** → Install corresponding CLI, configure API Key
- **`aop` command not found** → Ensure pip install succeeded, check PATH

### After Installation

**Ask the user:** "Installation complete! What project do you want to build with AOP?"

**Create hypothesis based on response:**
```bash
aop hypothesis create "If [idea], then [outcome]" -p quick_win
```

---

<!-- End of AI Agent Instructions -->
