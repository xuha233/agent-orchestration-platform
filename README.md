<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-orange" alt="Providers: 5 built-in" />
  <img src="https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey" alt="Platform: Windows | macOS | Linux" />
  <img src="https://img.shields.io/badge/tests-135%20passed-brightgreen" alt="Tests: 135 passed" />
</p>

<h1 align="center">AOP - Agent Orchestration Platform</h1>

<p align="center">
  <strong>Unified Multi-Agent Orchestration Platform</strong><br>
  <em>Workflow Methodology + Execution Engine, All in One</em>
</p>

<p align="center">
  <a href="#-core-features">Core Features</a> • 
  <a href="#-quick-install">Quick Install</a> • 
  <a href="#-usage">Usage</a> • 
  <a href="#-architecture">Architecture</a>
</p>

---

English | [简体中文](README.zh-CN.md)

---

## 🎯 What is AOP?

AOP (Agent Orchestration Platform) is a unified platform for multi-agent collaboration that combines:

- **Execution Engine** — Parallel dispatch, result aggregation, cross-agent deduplication
- **Workflow Methodology** — Hypothesis-driven development, learning capture, team configuration
- **Data Persistence** — Local storage, export to Markdown, session continuity

```
One command. Multiple agents working in parallel.
```

**Why Multi-Agent?**

| Single Agent | Multi-Agent (AOP) |
|--------------|-------------------|
| Single perspective | Multiple perspectives |
| One reasoning style | Diverse reasoning styles |
| Potential blind spots | Cross-validation |
| Sequential execution | Parallel execution |

**Wall-clock time ≈ slowest agent**, not the sum of all agents.

---

## ✨ Core Features

### 🤖 Multi-Agent Parallel Execution

```
┌─────────────────────────────────────────┐
│         Orchestrator (Primary Agent)     │
│  • Create hypotheses                     │
│  • Assign tasks to sub-agents            │
│  • Monitor execution                     │
│  • Aggregate and deduplicate results     │
│  • Capture learnings                     │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│ Claude│ │ Codex │ │Gemini │ │ Qwen  │
│Review │ │Build  │ │Analyze│ │ Test  │
└───────┘ └───────┘ └───────┘ └───────┘
```

**Key Capabilities:**
- Run multiple AI providers in parallel
- Automatic cross-agent deduplication
- Per-provider timeout configuration
- Token usage tracking across all agents

### 🧪 Hypothesis-Driven Development (HDD)

AOP implements a structured approach to development through hypothesis management:

```bash
# Create a hypothesis
aop hypothesis create "Adding cache reduces response time by 50%" -p quick_win

# List all hypotheses
aop hypothesis list

# Update hypothesis status after validation
aop hypothesis update H-D5BFC589 -s validated
```

**Workflow: Hypothesis → Validate → Learn → Iterate**

| State | Description |
|-------|-------------|
| `pending` | Hypothesis created, awaiting validation |
| `validated` | Hypothesis confirmed through testing |
| `refuted` | Hypothesis disproven |
| `inconclusive` | Results ambiguous, needs more data |

**Priority Levels:**
- `quick_win` — Can be validated quickly (< 1 hour)
- `deep_dive` — Requires significant investigation

### 📚 Learning Capture

Capture and persist learnings across development phases:

```bash
# Capture what worked and what didn't
aop learning capture \
  --phase scan \
  --worked "QThread for background scanning" \
  --insight "Avoid blocking wait() in UI threads"

# List all captured learnings
aop learning list

# Export to Markdown for documentation
aop learning export -o LESSONS_LEARNED.md
```

**Output Example:**
```markdown
# Lessons Learned

## What Worked
- QThread for background scanning
- QueuedConnection for thread-safe signals

## Key Insights
- Avoid blocking wait() in UI threads
- Async cancel improves responsiveness
```

### 📊 Project Complexity Assessment

Automatically assess project complexity and get team configuration recommendations:

```bash
aop project assess \
  --problem-clarity medium \
  --data-availability high \
  --tech-novelty low \
  --business-risk medium
```

**Project Types:**
| Type | Characteristics | Recommended Team |
|------|-----------------|------------------|
| `exploratory` | High novelty, low data | Research-focused |
| `optimization` | Clear goals, existing code | Performance team |
| `transformation` | Medium risk, medium clarity | Balanced team |
| `compliance_sensitive` | High business risk | Security-focused |

### 🔍 Multi-Provider Code Review

```bash
aop review -p "Review for bugs and security issues" -P claude,codex
```

```
Running review with 2 providers...
████████████████████████████████████████ 100%

Results:
  Duration: 45.2s
  Findings: 12 (3 critical, 5 high, 4 medium)
  Token Usage: 125K (claude: 80K, codex: 45K)
```

**Cross-Agent Deduplication:** Identical findings from multiple agents are merged with `detected_by` provenance tracking.

### 🔌 5 Built-in Providers

| Provider | CLI Command | Install |
|----------|-------------|---------|
| Claude | `claude` | `npm install -g @anthropic-ai/claude-code` |
| Codex | `codex` | `npm install -g @openai/codex` |
| Gemini | `gemini` | `pip install google-generativeai` |
| Qwen | `qwen` | `pip install dashscope` |
| OpenCode | `opencode` | `npm install -g opencode` |

**Extensible Adapter Contract:** Adding a new provider requires implementing:
- `detect()` — Check binary presence and auth status
- `run()` — Spawn CLI process with prompt
- `normalize()` — Extract structured findings from raw output

### 🌍 Cross-Platform Compatibility

| Platform | Status | Shell | Process Management |
|----------|--------|-------|-------------------|
| Windows | ✅ | PowerShell | `terminate()` / `kill()` |
| macOS | ✅ | Bash/Zsh | `SIGTERM` / `SIGKILL` |
| Linux | ✅ | Bash | `SIGTERM` / `SIGKILL` |

**Automatic Platform Detection:**
```python
from aop.core.compat import PlatformDetector

detector = PlatformDetector()
print(detector.current_platform)  # WINDOWS / MACOS / LINUX
print(detector.config.shell)       # powershell / bash
```

### 💾 Data Persistence

All data is persisted locally in `.aop/` directory:

```
.aop/
├── hypotheses.json     # Hypothesis records
├── learning.json       # Captured learnings
├── data/               # Session data
│   └── sessions.json
└── config.yaml         # Project configuration
```

---

## 🚀 Quick Install

### Option 1: One-Click Install

**macOS / Linux:**
```bash
git clone https://github.com/xuha233/agent-orchestration-platform.git aop
cd aop
chmod +x install.sh && ./install.sh
```

**Windows PowerShell:**
```powershell
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

### Verify Installation

```bash
aop doctor
```

```
             Provider Status             
┌──────────┬───────────┬─────────┬──────┐
│ Provider │ Status    │ Version │ Auth │
├──────────┼───────────┼─────────┼──────┤
│ claude   │ Available │ -       │ OK   │
│ codex    │ Not found │ -       │ -    │
│ gemini   │ Available │ -       │ OK   │
│ qwen     │ Available │ -       │ OK   │
│ opencode │ Not found │ -       │ -    │
└──────────┴───────────┴─────────┴──────┘
```

---

## 📋 Commands Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `aop doctor` | Check environment and providers | `aop doctor --json` |
| `aop init` | Initialize new project | `aop init my-project -P claude,codex` |
| `aop review` | Multi-agent code review | `aop review -p "Review for bugs"` |
| `aop run` | Execute multi-agent task | `aop run -p "Analyze architecture"` |
| `aop hypothesis create` | Create hypothesis | `aop hypothesis create "..." -p quick_win` |
| `aop hypothesis list` | List hypotheses | `aop hypothesis list --state pending` |
| `aop hypothesis update` | Update hypothesis status | `aop hypothesis update H-001 -s validated` |
| `aop learning capture` | Capture learning | `aop learning capture -p build -w "..."` |
| `aop learning list` | List learnings | `aop learning list` |
| `aop learning export` | Export to Markdown | `aop learning export -o LESSONS.md` |
| `aop project assess` | Assess project complexity | `aop project assess -p high -t medium` |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Config file not found |
| 3 | Provider unavailable |

---

## 🏗 Architecture

### Layered Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Layer                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Hypothesis  │ │  Learning   │ │    Team     │            │
│  │  Manager    │ │    Log      │ │  Config     │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────────────────────────────────────┐            │
│  │           Persistence Manager                │            │
│  └─────────────────────────────────────────────┘            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Execution Layer                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  Orchestrator│ │   Review    │ │   Report    │            │
│  │   Runtime    │ │   Engine    │ │  Formatters │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   Adapter   │ │   Retry     │ │   Error     │            │
│  │   Shim      │ │   Policy    │ │  Handler    │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────┬───────────┼───────────┬─────────┐
        ▼         ▼           ▼           ▼         ▼
    ┌───────┐ ┌───────┐ ┌───────┐ ┌────────┐ ┌──────┐
    │ Claude│ │ Codex │ │Gemini │ │OpenCode│ │ Qwen │
    └───────┘ └───────┘ └───────┘ └────────┘ └──────┘
```

### Core Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `core/engine/review.py` | 540 | Multi-provider review execution |
| `core/adapter/shim.py` | 438 | Provider adapter base class |
| `report/formatters.py` | 477 | Output format generation |
| `workflow/persistence.py` | 309 | Data persistence layer |
| `workflow/hypothesis/` | 200+ | Hypothesis management |
| `workflow/learning/` | 150+ | Learning capture |
| `workflow/team/` | 300+ | Team configuration |
| `core/types/` | 500+ | Type definitions and contracts |

### Execution Model

AOP uses a **parallel dispatch, wait-all** execution model:

1. **Assign** — Dispatch task to selected providers
2. **Execute in Parallel** — All providers work simultaneously
3. **Monitor** — Track progress, detect stalls, handle timeouts
4. **Deduplicate** — Merge identical findings with provenance
5. **Report** — Generate structured output

**Key Properties:**
- One provider's timeout or failure never stops others
- Transient errors are retried with exponential backoff
- Every invocation returns fresh output (no cache replay)
- Cross-platform process termination (Windows/POSIX)

### Provider Adapter Contract

```python
class ShimAdapterBase(Protocol):
    """Base class for provider adapters."""
    
    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        ...
    
    def detect(self) -> DetectionResult:
        """Check binary presence and auth status."""
        ...
    
    def spawn(self, ctx: SpawnContext) -> TaskRunRef:
        """Spawn CLI process with prompt."""
        ...
    
    def poll(self, ref: TaskRunRef) -> PollResult:
        """Check execution status."""
        ...
    
    def cancel(self, ref: TaskRunRef) -> None:
        """Cancel running task."""
        ...
    
    def normalize(self, raw: str | bytes, ctx: NormalizeContext) -> List[Finding]:
        """Extract structured findings from raw output."""
        ...
```

### Output Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| `report` | Human-readable terminal output | Local development |
| `json` | Structured JSON | CI/CD integration |
| `sarif` | SARIF format | GitHub Code Scanning |
| `markdown-pr` | Markdown with PR formatting | Pull request comments |
| `summary` | Concise summary | Quick overview |

---

## ⚙️ Configuration

Create `.aop.yaml` in project root:

```yaml
# .aop.yaml
providers:
  - claude
  - codex

defaults:
  timeout: 600           # Default timeout in seconds
  stall_timeout: 300     # Stall detection timeout
  hard_timeout: 3600     # Maximum execution time
  format: report         # Output format
  result_mode: all       # Result aggregation mode

# Provider-specific configuration
provider_timeouts:
  qwen: 900
  codex: 900

# Sub-agent configuration
subagent:
  default_timeout: 600
  complex_task_timeout: 1800
  max_parallel: 3

# Workflow configuration
workflow:
  hypothesis_storage: .aop/hypotheses.json
  learning_storage: .aop/learning.json
  auto_capture: true
```

### Timeout Recommendations

| Task Type | Suggested Timeout |
|-----------|-------------------|
| Simple code review | 300s (5 min) |
| UI component development | 600s (10 min) |
| Feature integration | 900s (15 min) |
| Complex refactoring | 1800s (30 min) |
| Architecture analysis | 3600s (1 hour) |

---

## 🔧 Advanced Usage

### Parallel Review with Multiple Providers

```bash
aop review \
  --repo . \
  --prompt "Review for security vulnerabilities and performance issues." \
  --providers claude,codex,gemini \
  --format json \
  --output results.json
```

### CI/CD Integration

```bash
# SARIF output for GitHub Code Scanning
aop review --format sarif --output results.sarif

# PR-ready markdown
aop review --format markdown-pr --output review.md
```

### Restrict File Access

```bash
aop run \
  --repo . \
  --prompt "Analyze the adapter layer." \
  --providers claude,codex \
  --allow-paths src/core/adapter \
  --target-paths src/core/adapter \
  --enforcement-mode strict
```

---

## 🛠 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/aop

# Code check
ruff check src/aop/
mypy src/aop/
```

**Test Coverage:** 135 tests, all passing

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Best Practices](docs/best-practices.md) | Practical guide from real projects |
| [Config Example](examples/.aop.yaml.example) | Complete configuration example |

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

MIT License — See [LICENSE](LICENSE) file

---

## ⭐ Star History

If you find AOP helpful, please consider giving it a star!

```bash
gh repo star xuha233/agent-orchestration-platform
```
