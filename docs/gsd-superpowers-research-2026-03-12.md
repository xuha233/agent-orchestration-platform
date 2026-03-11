# GSD & Superpowers 项目研究报告

> 研究时间：2026-03-12
> 目的：为 AOP MVP 生成器寻找可借鉴的设计模式

---

## 一、项目概览

### 1.1 Get Shit Done (GSD)

| 维度 | 信息 |
|------|------|
| **定位** | 轻量级元提示 + 上下文工程 + 规范驱动开发系统 |
| **核心问题** | 解决"上下文腐烂"(Context Rot) |
| **支持平台** | Claude Code, OpenCode, Gemini CLI, Codex |
| **安装方式** | `npx get-shit-done-cc@latest` |
| **Stars** | 3.5k+ |

### 1.2 Superpowers

| 维度 | 信息 |
|------|------|
| **定位** | 完整软件开发工作流，基于可组合"技能"系统 |
| **核心特点** | 技能自动触发，不需要用户手动调用 |
| **支持平台** | Claude Code, Cursor, Codex, OpenCode, Gemini CLI |
| **作者** | Jesse Vincent (obra) |
| **安装方式** | 插件市场 / 手动安装 |

---

## 二、核心设计对比

### 2.1 GSD 核心设计

#### 上下文工程

GSD 认为上下文腐烂是核心问题。解决方案：

| 文件 | 作用 |
|------|------|
| `PROJECT.md` | 项目愿景，始终加载 |
| `RESEARCH.md` | 生态知识（栈、特性、架构、陷阱） |
| `REQUIREMENTS.md` | 分 v1/v2 的需求，可追溯 |
| `ROADMAP.md` | 路线图，进度跟踪 |
| `STATE.md` | 决策、阻塞、位置 — 跨会话记忆 |
| `PLAN.md` | 原子任务，XML 结构，验证步骤 |
| `SUMMARY.md` | 发生了什么，改了什么 |

#### XML 提示格式

```xml
<task type="auto">
  <name>Create login endpoint</name>
  <files>src/app/api/auth/login/route.ts</files>
  <action>
    Use jose for JWT (not jsonwebtoken - CommonJS issues).
    Validate credentials against users table.
    Return httpOnly cookie on success.
  </action>
  <verify>curl -X POST localhost:3000/api/auth/login returns 200 + Set-Cookie</verify>
  <done>Valid credentials return cookie, invalid return 401</done>
</task>
```

**优点**：精确指令，不猜测，内置验证。

#### 波次执行 (Wave Execution)

独立任务并行，依赖任务顺序执行。

#### 原子 Git 提交

每个任务完成后立即提交，可追溯。

### 2.2 Superpowers 核心设计

#### 技能系统

| 技能 | 触发时机 | 作用 |
|------|----------|------|
| brainstorming | 写代码前 | 通过问题细化想法 |
| writing-plans | 设计确认后 | 分解为 2-5 分钟的小任务 |
| subagent-driven-development | 有计划后 | 分派子 Agent 执行 |
| test-driven-development | 实现过程中 | RED-GREEN-REFACTOR |
| systematic-debugging | 遇到 bug | 4 阶段根因分析 |

#### 自动触发

Agent 在执行任务前会自动检查相关技能。

---

## 三、与 AOP 的关系

### 3.1 定位对比

| 项目 | 定位 | 目标用户 |
|------|------|----------|
| **GSD** | 规范驱动开发系统 | 开发者 |
| **Superpowers** | 软件开发工作流 | 开发者 |
| **AOP** | MVP 生成器 | 创业者，非技术用户 |

### 3.2 可借鉴内容

#### 从 GSD 借鉴

1. 上下文工程 (STATE.md)
2. XML 任务格式
3. 波次执行
4. 原子提交

#### 从 Superpowers 借鉴

1. 技能系统
2. 头脑风暴流程
3. 自动触发机制

---

## 四、建议行动

### 短期可集成

1. STATE.md 模式 — 跨会话记忆
2. 原子提交 — MVP 生成过程可追溯
3. 任务 XML 格式 — 结构化 MVP 设计

### 中期可考虑

1. 技能自动触发
2. 波次执行优化

### 长期差异化

- 不做完整开发（GSD/Superpowers 的领域）
- 聚焦 0→1 验证
- 创业者友好

---

**下一步**：选择具体功能点，设计集成方案。