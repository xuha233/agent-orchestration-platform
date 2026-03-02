<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-orange" alt="Providers: 5 built-in" />
  <img src="https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey" alt="Platform: Windows | macOS | Linux" />
  <img src="https://img.shields.io/badge/tests-135%20passed-brightgreen" alt="Tests: 135 passed" />
</p>

<h1 align="center">AOP - Agent Orchestration Platform</h1>

<p align="center">
  <strong>统一的多 Agent 编排平台</strong><br>
  <em>工作流方法论 + 执行引擎，一套搞定</em>
</p>

<p align="center">
  <a href="#-核心特性">核心特性</a> • 
  <a href="#-快速安装">快速安装</a> • 
  <a href="#-使用场景">使用场景</a> • 
  <a href="#-架构">架构</a>
</p>

---

[English](README.md) | 简体中文

---

## 🎯 什么是 AOP？

AOP (Agent Orchestration Platform) 是一个统一的多 Agent 协作平台，整合了：

- **执行引擎** — 并行调度、结果聚合、跨 Agent 去重
- **工作流方法论** — 假设驱动开发、学习捕获、团队配置
- **数据持久化** — 本地存储、Markdown 导出、会话连续性

```
一条命令，多个 Agent 并行工作。
```

**为什么选择多 Agent？**

| 单个 Agent | 多 Agent (AOP) |
|------------|----------------|
| 单一视角 | 多视角交叉验证 |
| 一种推理风格 | 多样化推理风格 |
| 潜在盲区 | 互相补充发现 |
| 串行执行 | 并行执行 |

**实际耗时 ≈ 最慢的 Agent**，而非所有 Agent 之和。

---

## ✨ 核心特性

### 🤖 多 Agent 并行执行

```
┌─────────────────────────────────────────┐
│         Orchestrator (主 Agent)          │
│  • 创建假设                              │
│  • 分配任务给子 Agent                    │
│  • 监控执行                              │
│  • 聚合和去重结果                        │
│  • 捕获学习                              │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│ Claude│ │ Codex │ │Gemini │ │ Qwen  │
│Review │ │Build  │ │Analyze│ │ Test  │
└───────┘ └───────┘ └───────┘ └───────┘
```

**核心能力：**
- 多个 AI Provider 并行运行
- 自动跨 Agent 去重
- 按 Provider 配置超时
- 跨所有 Agent 的 Token 使用统计

### 🧪 假设驱动开发 (HDD)

AOP 通过假设管理实现结构化的开发方法：

```bash
# 创建假设
aop hypothesis create "添加缓存可减少 50% 响应时间" -p quick_win

# 列出所有假设
aop hypothesis list

# 验证后更新状态
aop hypothesis update H-D5BFC589 -s validated
```

**工作流：假设 → 验证 → 学习 → 迭代**

| 状态 | 描述 |
|------|------|
| `pending` | 假设已创建，等待验证 |
| `validated` | 通过测试确认 |
| `refuted` | 被证伪 |
| `inconclusive` | 结果模糊，需要更多数据 |

**优先级：**
- `quick_win` — 可快速验证（< 1 小时）
- `deep_dive` — 需要深入调查

### 📚 学习捕获

跨开发阶段捕获和持久化学习：

```bash
# 捕获什么有效、什么失败
aop learning capture \
  --phase scan \
  --worked "QThread 后台扫描" \
  --insight "避免 UI 线程中阻塞的 wait()"

# 列出所有捕获的学习
aop learning list

# 导出到 Markdown 用于文档
aop learning export -o LESSONS_LEARNED.md
```

**输出示例：**
```markdown
# Lessons Learned

## What Worked
- QThread 后台扫描
- QueuedConnection 跨线程安全信号

## Key Insights
- 避免 UI 线程中阻塞的 wait()
- 异步取消提高响应性
```

### 📊 项目复杂度评估

自动评估项目复杂度并获取团队配置建议：

```bash
aop project assess \
  --problem-clarity medium \
  --data-availability high \
  --tech-novelty low \
  --business-risk medium
```

**项目类型：**
| 类型 | 特征 | 推荐团队 |
|------|------|----------|
| `exploratory` | 高新颖性，低数据 | 研究导向 |
| `optimization` | 目标清晰，已有代码 | 性能团队 |
| `transformation` | 中等风险，中等清晰度 | 平衡团队 |
| `compliance_sensitive` | 高业务风险 | 安全导向 |

### 🔍 多 Provider 代码审查

```bash
aop review -p "检查 bug 和安全问题" -P claude,codex
```

```
Running review with 2 providers...
████████████████████████████████████████ 100%

Results:
  Duration: 45.2s
  Findings: 12 (3 critical, 5 high, 4 medium)
  Token Usage: 125K (claude: 80K, codex: 45K)
```

**跨 Agent 去重：** 多个 Agent 发现的相同问题会自动合并，保留 `detected_by` 来源追踪。

### 🔌 5 个内置 Provider

| Provider | CLI 命令 | 安装方式 |
|----------|---------|----------|
| Claude | `claude` | `npm install -g @anthropic-ai/claude-code` |
| Codex | `codex` | `npm install -g @openai/codex` |
| Gemini | `gemini` | `pip install google-generativeai` |
| Qwen | `qwen` | `pip install dashscope` |
| OpenCode | `opencode` | `npm install -g opencode` |

**可扩展适配器契约：** 添加新 Provider 需要实现：
- `detect()` — 检查二进制文件和认证状态
- `run()` — 启动 CLI 进程并捕获输出
- `normalize()` — 从原始输出提取结构化发现

### 🌍 跨平台兼容性

| 平台 | 状态 | Shell | 进程管理 |
|------|------|-------|----------|
| Windows | ✅ | PowerShell | `terminate()` / `kill()` |
| macOS | ✅ | Bash/Zsh | `SIGTERM` / `SIGKILL` |
| Linux | ✅ | Bash | `SIGTERM` / `SIGKILL` |

**自动平台检测：**
```python
from aop.core.compat import PlatformDetector

detector = PlatformDetector()
print(detector.current_platform)  # WINDOWS / MACOS / LINUX
print(detector.config.shell)       # powershell / bash
```

### 💾 数据持久化

所有数据持久化到本地 `.aop/` 目录：

```
.aop/
├── hypotheses.json     # 假设记录
├── learning.json       # 捕获的学习
├── data/               # 会话数据
│   └── sessions.json
└── config.yaml         # 项目配置
```

---

## 🚀 快速安装

### 方式一：一键安装

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

### 方式二：手动安装

```bash
git clone https://github.com/xuha233/agent-orchestration-platform.git
cd agent-orchestration-platform
pip install -e .
```

### 验证安装

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

## 📋 命令参考

| 命令 | 用途 | 示例 |
|------|------|------|
| `aop doctor` | 检查环境和 Provider | `aop doctor --json` |
| `aop init` | 初始化新项目 | `aop init my-project -P claude,codex` |
| `aop review` | 多 Agent 代码审查 | `aop review -p "检查 bug"` |
| `aop run` | 执行多 Agent 任务 | `aop run -p "分析架构"` |
| `aop hypothesis create` | 创建假设 | `aop hypothesis create "..." -p quick_win` |
| `aop hypothesis list` | 列出假设 | `aop hypothesis list --state pending` |
| `aop hypothesis update` | 更新假设状态 | `aop hypothesis update H-001 -s validated` |
| `aop learning capture` | 捕获学习 | `aop learning capture -p build -w "..."` |
| `aop learning list` | 列出学习 | `aop learning list` |
| `aop learning export` | 导出到 Markdown | `aop learning export -o LESSONS.md` |
| `aop project assess` | 评估项目复杂度 | `aop project assess -p high -t medium` |

### 退出码

| 代码 | 含义 |
|------|------|
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 配置文件未找到 |
| 3 | Provider 不可用 |

---

## 🏗 架构

### 分层设计

```
┌─────────────────────────────────────────────────────────────┐
│                    工作流层                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   假设      │ │   学习      │ │   团队      │            │
│  │   管理      │ │   捕获      │ │   配置      │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────────────────────────────────────┐            │
│  │              持久化管理器                     │            │
│  └─────────────────────────────────────────────┘            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    执行层                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  编排器     │ │   审查      │ │   报告      │            │
│  │  运行时     │ │   引擎      │ │  格式化     │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │  适配器     │ │   重试      │ │   错误      │            │
│  │  基类       │ │   策略      │ │   处理      │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────┬───────────┼───────────┬─────────┐
        ▼         ▼           ▼           ▼         ▼
    ┌───────┐ ┌───────┐ ┌───────┐ ┌────────┐ ┌──────┐
    │ Claude│ │ Codex │ │Gemini │ │OpenCode│ │ Qwen │
    └───────┘ └───────┘ └───────┘ └────────┘ └──────┘
```

### 核心模块

| 模块 | 行数 | 用途 |
|------|------|------|
| `core/engine/review.py` | 540 | 多 Provider 审查执行 |
| `core/adapter/shim.py` | 438 | Provider 适配器基类 |
| `report/formatters.py` | 477 | 输出格式生成 |
| `workflow/persistence.py` | 309 | 数据持久化层 |
| `workflow/hypothesis/` | 200+ | 假设管理 |
| `workflow/learning/` | 150+ | 学习捕获 |
| `workflow/team/` | 300+ | 团队配置 |
| `core/types/` | 500+ | 类型定义和契约 |

### 执行模型

AOP 使用 **并行调度、等待全部完成** 的执行模型：

1. **分配** — 将任务分配给选定的 Providers
2. **并行执行** — 所有 Provider 同时工作
3. **监控** — 追踪进度、检测停滞、处理超时
4. **去重** — 合并相同发现并保留来源
5. **报告** — 生成结构化输出

**关键特性：**
- 一个 Provider 的超时或失败不会阻止其他 Provider
- 瞬态错误使用指数退避重试
- 每次调用返回全新输出（无缓存重放）
- 跨平台进程终止（Windows/POSIX）

### Provider 适配器契约

```python
class ShimAdapterBase(Protocol):
    """Provider 适配器基类。"""
    
    @property
    def provider_name(self) -> str:
        """Provider 标识符。"""
        ...
    
    def detect(self) -> DetectionResult:
        """检查二进制文件和认证状态。"""
        ...
    
    def spawn(self, ctx: SpawnContext) -> TaskRunRef:
        """启动 CLI 进程。"""
        ...
    
    def poll(self, ref: TaskRunRef) -> PollResult:
        """检查执行状态。"""
        ...
    
    def cancel(self, ref: TaskRunRef) -> None:
        """取消运行中的任务。"""
        ...
    
    def normalize(self, raw: str | bytes, ctx: NormalizeContext) -> List[Finding]:
        """从原始输出提取结构化发现。"""
        ...
```

### 输出格式

| 格式 | 描述 | 用途 |
|------|------|------|
| `report` | 人类可读的终端输出 | 本地开发 |
| `json` | 结构化 JSON | CI/CD 集成 |
| `sarif` | SARIF 格式 | GitHub Code Scanning |
| `markdown-pr` | PR 格式的 Markdown | Pull Request 评论 |
| `summary` | 简洁摘要 | 快速概览 |

---

## ⚙️ 配置

在项目根目录创建 `.aop.yaml`：

```yaml
# .aop.yaml
providers:
  - claude
  - codex

defaults:
  timeout: 600           # 默认超时（秒）
  stall_timeout: 300     # 停滞检测超时
  hard_timeout: 3600     # 最大执行时间
  format: report         # 输出格式
  result_mode: all       # 结果聚合模式

# Provider 特定配置
provider_timeouts:
  qwen: 900
  codex: 900

# 子 Agent 配置
subagent:
  default_timeout: 600
  complex_task_timeout: 1800
  max_parallel: 3

# 工作流配置
workflow:
  hypothesis_storage: .aop/hypotheses.json
  learning_storage: .aop/learning.json
  auto_capture: true
```

### 超时建议

| 任务类型 | 建议超时 |
|---------|---------|
| 简单代码审查 | 300s (5分钟) |
| UI 组件开发 | 600s (10分钟) |
| 功能集成 | 900s (15分钟) |
| 复杂重构 | 1800s (30分钟) |
| 架构分析 | 3600s (1小时) |

---

## 🔧 高级用法

### 多 Provider 并行审查

```bash
aop review \
  --repo . \
  --prompt "检查安全漏洞和性能问题" \
  --providers claude,codex,gemini \
  --format json \
  --output results.json
```

### CI/CD 集成

```bash
# SARIF 输出用于 GitHub Code Scanning
aop review --format sarif --output results.sarif

# PR 就绪的 Markdown
aop review --format markdown-pr --output review.md
```

### 限制文件访问

```bash
aop run \
  --repo . \
  --prompt "分析适配器层" \
  --providers claude,codex \
  --allow-paths src/core/adapter \
  --target-paths src/core/adapter \
  --enforcement-mode strict
```

---

## 🛠 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行覆盖率
pytest --cov=src/aop

# 代码检查
ruff check src/aop/
mypy src/aop/
```

**测试覆盖：** 135 个测试，全部通过

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [最佳实践](docs/best-practices.md) | 基于真实项目的实践指南 |
| [配置示例](examples/.aop.yaml.example) | 完整配置示例 |

---

## 🙏 致谢

AOP 的执行引擎灵感来源于并借鉴了 [MCO (Multi-CLI Orchestrator)](https://github.com/mco-org/mco) 项目。我们衷心感谢 MCO 团队在多 Agent 编排模式方面的出色工作。

工作流方法论层基于 [AAIF (AI Agile Incubation Framework)](https://github.com/xuha233/agent-team-template)，提供了假设驱动开发方法。

---

## 📚 相关项目

| 项目 | 说明 |
|------|------|
| [MCO](https://github.com/mco-org/mco) | Multi-CLI Orchestrator — 执行引擎灵感来源 |
| [AAIF](https://github.com/xuha233/agent-team-template) | AI 敏捷孵化框架 |
| [OpenClaw](https://github.com/open-claw/open-claw) | AI Agent 桌面客户端 |

---

## 📄 License

MIT License — 详见 [LICENSE](LICENSE) 文件

---

## ⭐ Star

如果 AOP 对你有帮助，请考虑给个 Star！

```bash
gh repo star xuha233/agent-orchestration-platform
```
