# PROJECT_MEMORY.md - 项目记忆

## 项目概况

**名称:** Agent Orchestration Platform (AOP)
**版本:** v0.4.0
**描述:** 统一的多 Agent 编排平台，融合 MCO 执行引擎 + AAIF 工作流方法论 + Anthropic 多 Agent 最佳实践

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
- 会话管理
- **多 Agent 并行调度框架**

### 进行中 🔄
- Dashboard 功能完善
- Agent 团队状态展示

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

### 2026-03-08: Team 功能 Bug 发现与解决
- **问题**: TeamCreate 导致 Agent 使用 `in-process` 后端，进入 idle 模式永远不执行
- **解决**: 放弃 TeamCreate，使用原生 Task + `subagent_type="general-purpose"`
- **发现者**: Claude Code 自主 debug

### 2026-03-08: 多 Agent 架构优化
- **参考**: Anthropic "How we built our multi-agent research system"
- **改进**:
  - Orchestrator-Worker 模式
  - 任务复杂度评估机制
  - 详细委派指导（目标/输出格式/工具/边界）
  - 并行化策略
  - AAIF 循环整合

## 架构设计

### Orchestrator-Worker 模式

```
Lead Agent (Orchestrator)
├── 分析任务复杂度
├── 分解任务
├── 并行委派
└── 汇总结果

子 Agent (Workers)
├── Developer Agent
├── Reviewer Agent
├── Tester Agent
└── Researcher Agent
```

### 任务复杂度评估

| 复杂度 | 子 Agent 数量 | 工具调用次数 |
|--------|--------------|-------------|
| 简单 | 1 | 3-10 |
| 中等 | 2-4 | 10-15 |
| 复杂 | 5-10+ | 15+ |

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
