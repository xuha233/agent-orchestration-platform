# PROJECT_MEMORY.md - 项目记忆

## 项目概况

**名称:** Agent Orchestration Platform (AOP)
**版本:** v0.3.0
**描述:** 统一的多 Agent 编排平台，融合 MCO 执行引擎 + AAIF 工作流方法论

## 核心功能

### 已完成 ✅
- 智能体核心系统（扫描/审查/清理/报告）
- 工具层（Read/Glob/Grep等）
- 中枢抽象层（OrchestratorClient）
- Dashboard Web 界面
- CLI 命令（doctor/run/review/hypothesis）
- 多 Provider 支持（Claude/OpenCode/OpenClaw/API）
- 动态超时延长机制
- 开发者控制台

### 进行中 🔄
- Dashboard 功能完善
- Agent 团队状态展示
- 敏捷教练对话入口

### 待完成 ⏳
- 完整集成测试
- 性能优化
- 文档完善

## 技术栈

- **语言:** Python 3.8+
- **CLI:** Click
- **Web:** Streamlit
- **测试:** pytest
- **中枢:** Claude Code, OpenCode, OpenClaw

## 关键决策

### 2026-03-01: 采用 AOP 框架
- 原因：更灵活，支持假设驱动，适合快速迭代
- 替代：固定四人团队框架

### 2026-03-03: 动态超时延长
- 原因：子 Agent 执行复杂任务时经常超时
- 方案：TimeoutManager + ExtensionProtocol

### 2026-03-05: 中枢抽象层
- 原因：统一不同 Agent 的调用方式
- 方案：OrchestratorClient 抽象基类 + 多适配器

## 重要文件

- `src/aop/orchestrator/` - 中枢抽象层
- `src/aop/agent/` - Agent 系统
- `src/aop/dashboard/` - Web 界面
- `src/aop/cli/` - CLI 命令
- `.aop/` - 项目记忆和配置

## 常用命令

```bash
aop doctor                    # 检查环境
aop orchestrator doctor       # 检查中枢状态
aop run --task \"任务\"        # 运行任务
aop review -p \"提示\"         # 代码审查
aop hypothesis create \"陈述\" # 创建假设
aop dashboard                 # 启动 Web 界面
```

---

*保持更新：每次重要决策后更新此文件。*
