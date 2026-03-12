<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-orange" alt="Providers: 5 built-in" />
  <img src="https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey" alt="Platform: Windows | macOS | Linux" />
  <img src="https://img.shields.io/badge/version-v0.5.0-blueviolet" alt="Version: v0.5.0" />
  <img src="https://img.shields.io/badge/tests-288%20passed-brightgreen" alt="Tests: 288 passed" />
</p>

<h1 align="center">AOP - MVP Generator</h1>

<p align="center">
  <strong>Idea Validation Accelerator for Entrepreneurs</strong><br>
  <em>One Idea. One Command. One MVP.</em>
</p>

<p align="center">
  <a href="#-turn-ideas-into-mvps-in-hours">Quick Start</a> • 
  <a href="#-who-is-this-for">Who It's For</a> • 
  <a href="#-core-features">Core Features</a> • 
  <a href="#-command-reference">Commands</a>
</p>

---

English | [简体中文](README.zh-CN.md)

---

## 💡 Turn Ideas into MVPs in Hours

**Have an app idea but can't code?** AOP helps you validate it fast.

```bash
aop run "I want to build a second-hand book marketplace where users upload books and others buy them"
```

AOP will:
1. **Structure your idea** - Ask clarifying questions (target users, core features, monetization)
2. **Generate hypotheses** - List assumptions that need validation
3. **Design MVP** - Feature list, user flow, data model
4. **Build prototype** - Clickable interactive prototype (HTML + mock data)
5. **Validate** - Provide validation methods and next steps

**You describe the idea. AOP delivers a testable MVP.**

---

## 🎯 Who Is This For?

| User Type | What You Need | How AOP Helps |
|-----------|---------------|---------------|
| **Non-technical founders** | "I have an app idea but can't code" | Generate demo for investors/partners |
| **Product managers** | "Need to validate multiple feature hypotheses" | Quick prototypes to decide priorities |
| **Indie hackers** | "Want to test ideas fast without wasting time" | Minimal effort, maximum learning |
| **Students/Makers** | "Need a prototype for hackathon/course" | Ship something impressive, fast |

---

## 🚀 Quick Start

### Install

```bash
pip install git+https://github.com/xuha233/agent-orchestration-platform.git
```

### Validate Your First Idea

```bash
# Check environment
aop doctor

# Describe your idea
aop run "Build a task management app with team collaboration"

# Or use interactive mode (AOP will ask questions)
aop run -i "I want to create a..."
```

### Resume Interrupted Work

```bash
# List all projects
aop agent list

# Continue where you left off
aop agent run -r sprint-abc123
```

---

## ✨ Core Features

### 🎨 MVP Generation

| Input | Output |
|-------|--------|
| Your idea in plain language | Clickable prototype (HTML) |
| No technical knowledge needed | Feature list + user flow |
| Vague description? No problem | AOP asks clarifying questions |

### 🧪 Hypothesis-Driven Validation

Every MVP comes with testable hypotheses:

```
H-001: If users can upload books in < 30 seconds, they will list more items
H-002: If we charge 10% commission, sellers will still use the platform
```

### 📊 Validation Report

Each project includes:
- **What to test** - Specific validation methods
- **How to measure** - Success metrics
- **Next steps** - Iteration suggestions

### 💾 Knowledge Retention

- Every project's validation journey is recorded
- Learnings can be exported and shared
- Similar ideas can reuse past insights

---

## 🔄 AOP vs Other Tools

| Your Situation | Recommended Tool |
|----------------|------------------|
| "I have an idea, need a quick prototype to show people" | **AOP** - Designed for idea validation |
| "I need production-ready code for my startup" | **MCO** or **Claude Code** - For full development |
| "I want fine-grained control over agents" | **MCO** - More configuration options |
| "I need CI/CD integration with SARIF output" | **MCO** - Mature SARIF support |

**The ecosystem: AOP handles 0→1 (validation), other tools handle 1→100 (scaling).**

---

## 📋 Command Reference

### 🚀 Idea to MVP (Zero-Config)

| Command | Purpose |
|---------|---------|
| `aop run "your idea"` | 🌟 Describe idea, get MVP |
| `aop run -i "your idea"` | Interactive mode with follow-up questions |
| `aop agent run -r <sprint-id>` | Resume interrupted project |
| `aop agent status` | View current project status |
| `aop agent list` | List all projects |

### 🧠 Hypothesis & Learning

| Command | Purpose |
|---------|---------|
| `aop hypothesis list` | List hypotheses for current project |
| `aop hypothesis create "..."` | Add new hypothesis |
| `aop learning export` | Export learnings to Markdown |

### 🔧 Advanced

| Command | Purpose |
|---------|---------|
| `aop dashboard` | Launch web UI |
| `aop doctor` | Check environment |
| `aop project assess` | Analyze existing project |

---

## 🔌 Supported Providers

| Provider | Type | Setup |
|----------|------|-------|
| Claude | CLI | `claude auth login` |
| Codex | CLI | `OPENAI_API_KEY=xxx` |
| Gemini | API | `GOOGLE_API_KEY=xxx` |
| Qwen | API | `DASHSCOPE_API_KEY=xxx` |
| OpenCode | CLI | No config needed |

---

## 📊 Example Output

When you run:

```bash
aop run "Create a second-hand book marketplace"
```

You get:

### 1. Structured Idea
```
Target Users: College students, book lovers
Core Features: 
  - Book listing (photo, condition, price)
  - Search and browse
  - Direct messaging
  - Secure payment
Monetization: 10% transaction fee
```

### 2. Hypotheses
```
H-001: Students will list books if process < 2 minutes
H-002: 10% fee is acceptable for convenience
H-003: Direct messaging increases trust and conversion
```

### 3. MVP Prototype
- Single HTML file with mock data
- Clickable flow: Browse → Details → Message → Pay
- Responsive design

### 4. Validation Report
```
How to test:
  1. Show prototype to 10 target users
  2. Measure listing completion time
  3. Survey on fee acceptance
  4. Track message usage patterns

Success criteria:
  - 80% complete listing in < 2 min
  - 70% accept 10% fee
  - 50% use messaging feature
```

---

## 🧩 Skills System

AOP features a composable skill system inspired by [Superpowers](https://github.com/obra/superpowers). Skills are modular capabilities that can be automatically triggered based on context.

### Built-in Skills

| Skill | Trigger | Iron Law |
|-------|---------|----------|
| **hypothesis-driven** | "I want to build...", "I have an idea..." | NO MVP DEVELOPMENT WITHOUT IDENTIFIED HYPOTHESES |
| **mvp-breakdown** | "Start development", "Implement this..." | NO MVP FEATURE WITHOUT HYPOTHESIS VALIDATION PURPOSE |
| **validation-before-launch** | "Launch MVP", "Deploy..." | NO MVP LAUNCH WITHOUT VALIDATION CRITERIA |

### Skill Components

Each skill defines:
- **Triggers** - Keywords/phrases that activate the skill
- **Iron Law** - Hard rules that enforce correct behavior
- **Red Flags** - Anti-patterns to warn against
- **Checklist** - Verification items for task completion

### Using Skills Programmatically

```python
from aop.skills import create_skill_manager, SkillContext

# Create skill manager
manager = create_skill_manager()

# Find matching skills
context = SkillContext(task="I want to build an e-commerce system")
matches = manager.find_matching_skills(context)

# Get iron laws
iron_laws = manager.get_all_iron_laws()

# Check for red flags
red_flags = manager.check_all_red_flags("Just build it first, users will like it")
# Returns: {"hypothesis-driven": ["先做出来再说", "用户会喜欢的"]}
```

### Adding Custom Skills

```python
from aop.skills import SkillBase, SkillMeta, SkillPriority

class MyCustomSkill(SkillBase):
    def get_meta(self) -> SkillMeta:
        return SkillMeta(
            name="my-custom-skill",
            description="Custom skill description",
            triggers=["trigger phrase"],
            priority=SkillPriority.HIGH,
        )
    
    def matches(self, context) -> bool:
        return any(t in context.task for t in self.get_meta().triggers)
    
    def get_prompt(self) -> str:
        return "Skill instructions in Markdown..."
    
    def get_iron_law(self) -> str:
        return "MANDATORY RULE HERE"
    
    def get_red_flags(self) -> list:
        return ["anti-pattern 1", "anti-pattern 2"]
```

## 🏗 Architecture

```
┌─────────────────────────────────────────┐
│          MVP Generation Layer            │
│  Idea Structurer | MVP Designer          │
│  Prototype Builder | Report Generator    │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────┴───────────────────────┐
│         Orchestration Layer              │
│  Claude-Code | OpenCode | OpenClaw      │
│  Multi-Provider Parallel Dispatch       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────┴───────────────────────┐
│          Execution Layer                 │
│  Task Scheduler | Timeout Manager       │
│  Result Synthesis | Report Formatters   │
└─────────────────────────────────────────┘
```

---

## 📊 Test Coverage

| Module | Tests | Status |
|--------|-------|--------|
| MVP Generator | 15+ | ✅ |
| HypothesisManager | 14 | ✅ |
| KnowledgeBase | 14 | ✅ |
| AutoValidator | 15+ | ✅ |
| LearningExtractor | 12+ | ✅ |
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
```

---

## 🙏 Acknowledgments

- Execution layer inspired by [MCO](https://github.com/mco-org/mco)
- Workflow methodology based on [AAIF](https://github.com/xuha233/agent-team-template)

---

## 📚 Related Projects

| Project | Role |
|---------|------|
| [MCO](https://github.com/mco-org/mco) | 1→100 scaling (full development) |
| [AAIF](https://github.com/xuha233/agent-team-template) | Methodology foundation |
| [OpenClaw](https://github.com/open-claw/open-claw) | Desktop client |

---

## 📄 License

MIT License — See [LICENSE](LICENSE)

---

## 🤖 AI Agent Installation Guide

> This section is for AI assistants. If you're a human, skip this.

### Quick Install

```bash
git clone https://github.com/xuha233/agent-orchestration-platform.git aop
cd aop
pip install -e .
aop doctor
```

### Provider Setup

| Provider | Config |
|----------|--------|
| Claude | `claude auth login` |
| Codex | `export OPENAI_API_KEY=xxx` |
| Gemini | `export GOOGLE_API_KEY=xxx` |
| Qwen | `export DASHSCOPE_API_KEY=xxx` |

### After Installation

Ask the user: "What's your idea? Describe it and I'll help you generate an MVP."

Then run:
```bash
aop run "[user's idea]"
```
