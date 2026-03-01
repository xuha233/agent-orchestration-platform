<p align="center">
  <img src="https://img.shields.io/npm/v/agent-orchestration-platform" alt="npm version" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-green" alt="Providers: 5 built-in" />
</p>

<h1 align="center">AOP - Agent Orchestration Platform</h1>

<p align="center"><strong>Unified Multi-Agent Orchestration - Workflow + Execution, All-in-One</strong></p>

<p align="center"><a href="#quick-start">Quick Start</a> | <a href="#commands">Commands</a> | <a href="#provider-setup">Provider Setup</a></p>

---

## What is AOP

AOP combines **MCO's execution engine** with **AAIF's workflow methodology**:
- **Parallel Execution** — Multiple agents work simultaneously, wall-clock time ~= slowest agent
- **Hypothesis-Driven** — Hypothesis → Validation → Learning iteration loop
- **Zero Config** — 5 minutes to get started, works out of the box

---

## Installation

```bash
# From GitHub
git clone https://github.com/xuha233/agent-orchestration-platform.git
cd agent-orchestration-platform
pip install -e .
```

Or use the one-click installer:
```bash
# macOS / Linux
./install.sh

# Windows PowerShell
.\install.ps1
```

---

## Quick Start

### 1. Check Environment

```bash
aop doctor
```

Output:
```
Provider Status:
  [OK] claude: available (v1.0.0)
  [OK] codex: available
  [--] gemini: not found
  [--] qwen: not found
```

### 2. Code Review

```bash
aop review -p "Review for bugs" -P claude,codex
```

Output:
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

### 3. Project Initialization

```bash
aop init my-project
```

Creates:
```
my-project/
  .aop.yaml       # Config file
  runs/           # Run records
  hypotheses.md   # Hypothesis template
```

### 4. Hypothesis-Driven Development

```bash
# Create hypothesis
aop hypothesis create "Adding cache reduces 50% response time" -p quick_win

# List hypotheses
aop hypothesis list

# Update hypothesis state
aop hypothesis update H-001 --state validated
```

### 5. Project Assessment

```bash
aop project assess --problem-clarity low --tech-novelty high
```

Output:
```
Project Type: exploratory
Recommended Team: product_owner, data, ml
Strategy: fast-fail, learning-focused
```

---

## Commands

| Command | Purpose | Example |
|---------|---------|---------|
| aop doctor | Check environment | aop doctor --json |
| aop init | Initialize project | aop init my-project |
| aop review | Code review | aop review -p "Review for bugs" |
| aop run | Execute task | aop run -p "Summarize architecture" |
| aop hypothesis | Manage hypotheses | aop hypothesis create "..." |
| aop project | Project assessment | aop project assess |
| aop learning | Capture learnings | aop learning capture --phase explore |

---

## Use Cases

| Scenario | Command |
|----------|---------|
| New project | aop init my-project && cd my-project |
| Code review | aop review -p "Review for security issues" -P claude,codex |
| Multi-agent task | aop run -p "Analyze architecture" -P claude,codex,gemini |
| Hypothesis validation | aop hypothesis create "..." && aop hypothesis list |
| Team configuration | aop project assess --tech-novelty high |
| Experience capture | aop learning capture --phase build --worked "CI/CD worked" |

---

## Architecture

```
Workflow Layer (AAIF)
Project Assessment | Hypothesis Mgmt | Team Config | Learning Capture
                    |
                    v
Execution Layer (MCO)
Parallel Dispatch | Result Aggregation | Dedup | Standardized Output
                    |
    Claude Agent | Codex Agent | Gemini Agent | OpenCode | Qwen ...
```

---

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
npm install -g @anthropic-ai/claude-code
# Or use gcloud
gcloud components install ai
gcloud auth login
```

### Qwen (Alibaba)
```bash
# Option 1: DashScope API
pip install dashscope
export DASHSCOPE_API_KEY=your-key

# Option 2: Ollama local
ollama pull qwen2.5-coder
```

### OpenCode
```bash
npm install -g opencode
opencode auth login
```

---

## Configuration

Create .aop.yaml in your project root:

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

AOP automatically searches for .aop.yaml in current and parent directories.

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=aop
```

---

## License

MIT