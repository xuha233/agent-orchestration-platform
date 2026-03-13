<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-LGPL--3.0-blue.svg" alt="License: LGPL-3.0" />
  <img src="https://img.shields.io/badge/providers-5%20built--in-orange" alt="Providers: 5 built-in" />
  <img src="https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey" alt="Platform: Windows | macOS | Linux" />
  <img src="https://img.shields.io/badge/version-v0.5.0-blueviolet" alt="Version: v0.5.0" />
  <img src="https://img.shields.io/badge/tests-288%20passed-brightgreen" alt="Tests: 288 passed" />
</p>

<h1 align="center">AOP - MVP 生成器</h1>

<p align="center">
  <strong>面向创业者的创意验证加速器</strong><br>
  <em>一个想法。一行命令。一个 MVP。</em>
</p>

<p align="center">
  <a href="#-几小时内把想法变成-mvp">快速开始</a> • 
  <a href="#-适合谁用">适合谁</a> • 
  <a href="#-核心功能">核心功能</a> • 
  <a href="#-命令参考">命令</a>
</p>

---

[English](README.md) | 简体中文

---

## 💡 几小时内把想法变成 MVP

**有 app 想法但不会写代码？** AOP 帮你快速验证。

```bash
aop run "我想做一个二手书交易平台，用户上传书本，其他人购买，我抽成"
```

AOP 会：
1. **结构化你的想法** - 追问关键问题（目标用户、核心功能、盈利模式）
2. **生成假设** - 列出需要验证的商业和技术假设
3. **设计 MVP** - 功能列表、用户流程、数据模型
4. **生成原型** - 可点击的交互原型（HTML + 模拟数据）
5. **验证报告** - 提供验证方法和下一步建议

**你描述想法。AOP 输出可测试的 MVP。**

---

## 🎯 适合谁？

| 用户类型 | 需求 | AOP 帮你 |
|---------|------|----------|
| **非技术创业者** | "我有 app 想法，但不会编程" | 生成 demo 给投资人/合伙人看 |
| **产品经理** | "需要快速验证多个功能假设" | 快速原型，决定开发优先级 |
| **独立开发者** | "想用最少时间试错" | 最小投入，最大学习 |
| **学生/创客** | "参加黑客松/课程项目" | 快速产出，惊艳全场 |

---

## 🚀 快速开始

### 安装

```bash
pip install git+https://github.com/xuha233/agent-orchestration-platform.git
```


### 可选功能

#### 🧪 mem0 智能记忆（实验性）

启用语义搜索和智能记忆管理：

```bash
pip install mem0ai faiss-cpu
```

安装后，在 Dashboard 设置页面开启「mem0 智能记忆」开关即可使用。

### 验证你的第一个想法

```bash
# 检查环境
aop doctor

# 描述你的想法
aop run "做一个支持团队协作的任务管理工具"

# 或使用交互模式（AOP 会追问）
aop run -i "我想创建一个..."
```

### 恢复中断的工作

```bash
# 列出所有项目
aop agent list

# 继续之前的工作
aop agent run -r sprint-abc123
```

---

## ✨ 核心功能

### 🎨 MVP 生成

| 输入 | 输出 |
|-----|------|
| 用自然语言描述想法 | 可点击的原型（HTML） |
| 不需要技术知识 | 功能列表 + 用户流程 |
| 描述模糊？没问题 | AOP 会追问澄清 |

### 🧪 假设驱动验证

每个 MVP 都附带可验证的假设：

```
H-001: 如果用户能在 30 秒内上传书本，他们会发布更多商品
H-002: 如果收取 10% 佣金，卖家仍会使用平台
H-003: 直接消息功能增加信任和转化率
```

### 📊 验证报告

每个项目包含：
- **测试什么** - 具体验证方法
- **如何衡量** - 成功指标
- **下一步** - 迭代建议

### 💾 知识留存

- 记录每个项目的验证过程
- 学习心得可导出分享
- 类似想法可复用过往经验

---

## 🔄 AOP vs 其他工具

| 你的情况 | 推荐工具 |
|---------|---------|
| "我有个想法，需要快速做原型给别人看" | **AOP** - 专为创意验证设计 |
| "我需要生产级代码来启动项目" | **MCO** 或 **Claude Code** - 完整开发 |
| "我想精细控制 Agent 行为" | **MCO** - 更多配置选项 |
| "我需要 CI/CD 集成和 SARIF 输出" | **MCO** - 成熟的 SARIF 支持 |

**生态定位：AOP 负责 0→1（验证），其他工具负责 1→100（规模化）。**

---

## 📋 命令参考

### 🚀 想法变 MVP（零配置）

| 命令 | 用途 |
|-----|------|
| `aop run "你的想法"` | 🌟 描述想法，获得 MVP |
| `aop run -i "你的想法"` | 交互模式，会追问问题 |
| `aop agent run -r <sprint-id>` | 恢复中断的项目 |
| `aop agent status` | 查看当前项目状态 |
| `aop agent list` | 列出所有项目 |

### 🧠 假设与学习

| 命令 | 用途 |
|-----|------|
| `aop hypothesis list` | 列出当前项目的假设 |
| `aop hypothesis create "..."` | 创建新假设 |
| `aop learning export` | 导出学习心得为 Markdown |

### 🔧 高级功能

| 命令 | 用途 |
|-----|------|
| `aop dashboard` | 启动 Web 界面 |
| `aop doctor` | 检查环境 |
| `aop project assess` | 分析现有项目 |

---

## 🔌 支持的 Provider

| Provider | 类型 | 配置 |
|----------|-----|------|
| Claude | CLI | `claude auth login` |
| Codex | CLI | `OPENAI_API_KEY=xxx` |
| Gemini | API | `GOOGLE_API_KEY=xxx` |
| Qwen | API | `DASHSCOPE_API_KEY=xxx` |
| OpenCode | CLI | 无需配置 |

---

## 📊 示例输出

当你运行：

```bash
aop run "创建一个二手书交易平台"
```

你会得到：

### 1. 结构化的想法
```
目标用户：大学生、读书爱好者
核心功能：
  - 书本上架（照片、成色、价格）
  - 搜索和浏览
  - 直接消息
  - 安全支付
盈利模式：10% 交易佣金
```

### 2. 假设
```
H-001: 学生会在 2 分钟内完成上架
H-002: 10% 佣金对于便利性是可以接受的
H-003: 直接消息增加信任和转化率
```

### 3. MVP 原型
- 单个 HTML 文件，带模拟数据
- 可点击流程：浏览 → 详情 → 消息 → 支付
- 响应式设计

### 4. 验证报告
```
如何测试：
  1. 向 10 个目标用户展示原型
  2. 测量上架完成时间
  3. 调查对佣金的接受度
  4. 追踪消息功能使用情况

成功标准：
  - 80% 在 2 分钟内完成上架
  - 70% 接受 10% 佣金
  - 50% 使用消息功能
```

---

## 🏗 架构

```
┌─────────────────────────────────────────┐
│          MVP 生成层                      │
│  想法结构化 | MVP 设计器                  │
│  原型构建器 | 报告生成器                  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────┴───────────────────────┐
│         编排层                           │
│  Claude-Code | OpenCode | OpenClaw      │
│  多 Provider 并行调度                   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────┴───────────────────────┐
│          执行层                          │
│  任务调度器 | 超时管理器                 │
│  结果综合 | 报告格式化                   │
└─────────────────────────────────────────┘
```

---

## 📊 测试覆盖

| 模块 | 测试数 | 状态 |
|-----|--------|------|
| MVP 生成器 | 15+ | ✅ |
| HypothesisManager | 14 | ✅ |
| KnowledgeBase | 14 | ✅ |
| AutoValidator | 15+ | ✅ |
| LearningExtractor | 12+ | ✅ |
| TaskScheduler | 7 | ✅ |
| SprintPersistence | 4 | ✅ |

**总计：288 个测试通过**

---

## 🛠 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check src/aop/
```

---

## 🙏 致谢

- 执行层灵感来自 [MCO](https://github.com/mco-org/mco)
- 工作流方法论基于 [AAIF](https://github.com/xuha233/agent-team-template)

---

## 📚 相关项目

| 项目 | 定位 |
|-----|------|
| [MCO](https://github.com/mco-org/mco) | 1→100 规模化（完整开发） |
| [AAIF](https://github.com/xuha233/agent-team-template) | 方法论基础 |
| [OpenClaw](https://github.com/open-claw/open-claw) | 桌面客户端 |

---

## 📄 许可证

LGPL-3.0 License — 详见 [LICENSE](LICENSE)
