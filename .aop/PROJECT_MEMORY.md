# PROJECT_MEMORY.md - 项目记忆

## 项目概况

**名称:** Agent Orchestration Platform (AOP)
**版本:** v0.5.0
**当前定位:** MVP Generator for idea validation
**一句话描述:** 帮助非技术创始人、产品经理和独立开发者把想法快速转成可验证的 MVP 原型，同时保留 AOP 的多 Agent 编排、记忆和工作台能力。

## 当前真实状态

### 已完成 ✅
- CLI 主流程已成型：`aop run`、`aop doctor`、`aop dashboard`、`aop hypothesis`、`aop learning`
- Dashboard 主工作台已可用：聊天入口、快捷操作、项目记忆、工作区管理、设置页
- 多中枢抽象已落地：Claude Code、Codex、OpenCode、OpenClaw、API
- Primary Agent 已支持 Claude Code、OpenCode、Codex
- 会话隔离、自动记忆、STATE.md 跨会话记忆、mem0 实验性记忆已接入
- Orchestrator 已集成预检、动态超时、LLM-as-Judge、错误恢复、知识库、任务调度
- OpenCode 初始化、工作区自动初始化、`aop project add` 等工程化能力已落地
- 当前测试主干健康：`576 passed`

### 进行中 🔄
- 收口产品定位与项目记忆，统一 `README / .aop / 初始化模板 / 提示词`
- 继续打磨 Dashboard 到“可连续使用”的 MVP 工作台体验
- 继续补强 Primary Agent 与 AgentDriver 的联动闭环

### 下一阶段 ⏭
- 围绕 MVP Generator 主线补足端到端工作流
- 把项目记忆、STATE、自动初始化、Dashboard 首页状态进一步统一
- 补更高层的集成测试与产品演示路径

## 关键决策

### 2026-03-01 到 2026-03-07：打稳 AOP 基础编排层
- 完成多 Agent 编排、动态超时、LLM 评估、错误恢复、知识库、项目评估
- 为后续产品形态提供底层能力

### 2026-03-05 到 2026-03-07：Dashboard 形成主工作台
- 建立聊天入口、快捷命令、项目记忆、工作区、设置等核心界面
- 解决 Windows subprocess、流式输出、session 隔离等关键问题

### 2026-03-11 到 2026-03-16：产品叙事转向 MVP Generator
- README 和对外描述从“通用多 Agent 编排平台”收束为“想法验证与 MVP 生成器”
- 保留编排内核，但把用户入口聚焦到 `idea -> hypothesis -> prototype -> validation`

### 2026-03-13 到 2026-03-16：Codex 接入完成
- Codex 已接入 orchestrator、primary agent、dashboard
- 当前支持 Claude Code / Codex / OpenCode 多种主要入口

## 当前架构认知

### 对外产品层
- MVP 生成
- 假设驱动验证
- 项目记忆与学习沉淀
- Dashboard 工作台

### 内部执行层
- Primary Agent
- Orchestrator 抽象层
- 多 Provider / 多中枢调度
- STATE / memory / mem0 记忆系统

## 重要文件

- `README.md` - 英文主说明，当前产品定位以此为准
- `README.zh-CN.md` - 中文说明
- `src/aop/primary/` - Primary Agent 实现（Claude/OpenCode/Codex/OpenClaw）
- `src/aop/orchestrator/` - 中枢抽象层
- `src/aop/dashboard/app.py` - Dashboard 主入口
- `src/aop/memory/` - 记忆加载与 mem0 集成
- `src/aop/state/` - STATE.md 跨会话记忆
- `.aop/` - 当前仓库自己的项目记忆与状态

## 当前已知不一致点

- 历史文档里仍残留一部分 `v0.4.0` / 通用编排平台叙事
- 某些初始化模板和项目记忆模板仍偏旧版敏捷教练 / 多 Agent 描述
- README 测试数字曾落后于真实测试结果

## 接手开发时的默认判断

- 以 `README.md` 和当前代码实现为准，不以旧记忆为准
- 当前主线不是继续发散做“更多抽象”，而是围绕 MVP Generator 把体验闭环做扎实
- 修改涉及产品定位时，优先同步 README、`.aop` 记忆和初始化模板

---

*保持更新：每次重要决策后更新此文件。*
