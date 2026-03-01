<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-orange" alt="Providers: 5 built-in" />
</p>

<h1 align="center">AOP - Agent Orchestration Platform</h1>

<p align="center">
  <strong>Unified Multi-Agent Orchestration Platform</strong><br>
  <em>Workflow + Execution, All in One</em>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> • 
  <a href="#-commands">Commands</a> • 
  <a href="#-provider-setup">Provider Setup</a> • 
  <a href="#-architecture">Architecture</a>
</p>

---

## 🎯 Overview

AOP combines the **MCO execution engine** with the **AAIF workflow methodology**:

| Feature | Description |
|---------|-------------|
| 🚀 **Parallel Execution** | Multiple agents work simultaneously, wall-clock time ≈ slowest agent |
| 📊 **Hypothesis-Driven** | Hypothesis → Validation → Learning iteration cycle |
| ⚡ **Zero Config** | Up and running in 5 minutes |
| 🔌 **Multi-Provider** | Supports Claude, Codex, Gemini, Qwen, OpenCode |

---

## 📦 Installation

### Option 1: One-Click Install (Recommended)

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

### Option 2: Manual Install

```bash
git clone https://github.com/xuha233/agent-orchestration-platform.git
cd agent-orchestration-platform
pip install -e .
```

---

## 🚀 Quick Start

### 1. Check Environment

```bash
aop doctor
```

```
Provider Status:
  [OK] claude: available (v1.0.0)
  [OK] codex: available
  [--] gemini: not found
```

### 2. Initialize Project

```bash
aop init my-project -P claude,codex
cd my-project
```

Creates:
```
my-project/
  .aop.yaml       # Configuration
  runs/           # Run records
  hypotheses.md   # Hypothesis template
```

### 3. Code Review

```bash
aop review -p "Review for bugs and security issues"
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
  3. [MEDIUM] Missing input validation in src/api/user.py:23
```

### 4. Hypothesis-Driven Development

```bash
# Create hypothesis
aop hypothesis create "Adding cache reduces 50% response time" -p quick_win

# List hypotheses
aop hypothesis list

# Update hypothesis status
aop hypothesis update H-001 --state validated
```

---

## 📋 Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `aop doctor` | Check environment | `aop doctor --json` |
| `aop init` | Initialize project | `aop init my-project -P claude,codex` |
| `aop review` | Multi-agent code review | `aop review -p "Review for bugs"` |
| `aop run` | Execute multi-agent task | `aop run -p "Analyze architecture"` |
| `aop hypothesis` | Hypothesis management | `aop hypothesis create "..."` |
| `aop project` | Project assessment | `aop project assess` |
| `aop learning` | Capture learnings | `aop learning capture --phase build` |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Layer (AAIF)                    │
│  Project Assessment │ Hypothesis │ Team │ Learning │ Phase  │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Execution Layer (MCO)                    │
│  Parallel Scheduling │ Aggregation │ Dedup │ Error Handling │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────┬───────────┼───────────┬─────────┐
        ▼         ▼           ▼           ▼         ▼
    ┌───────┐ ┌───────┐ ┌───────┐ ┌────────┐ ┌──────┐
    │ Claude│ │ Codex │ │Gemini │ │OpenCode│ │ Qwen │
    └───────┘ └───────┘ └───────┘ └────────┘ └──────┘
```

---

## 🔌 Provider Setup

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

### Qwen (Alibaba Cloud)
```bash
# Option 1: DashScope API
pip install dashscope
export DASHSCOPE_API_KEY=your-key

# Option 2: Ollama Local
ollama pull qwen2.5-coder
```

### OpenCode
```bash
npm install -g opencode
opencode auth login
```

---

## ⚙️ Configuration

Create `.aop.yaml` in your project root:

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

AOP automatically searches for `.aop.yaml` in current and parent directories.

---

## 🛠 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Linting
ruff check src/aop/
mypy src/aop/
```

---

## 📚 Related Projects

| Project | Description |
|---------|-------------|
| [MCO](https://github.com/xuha233/mco) | Multi-agent code review execution engine |
| [AAIF](https://github.com/xuha233/agent-team-template) | AI Agile Incubation Framework |

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.