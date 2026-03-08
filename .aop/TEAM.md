# TEAM.md - Agent 团队角色

## 核心架构

基于 **Orchestrator-Worker 模式**：

```
┌─────────────────────────────────────────┐
│         Lead Agent (Orchestrator)       │
│  - 分析任务复杂度                        │
│  - 分解任务                              │
│  - 委派执行                              │
│  - 汇总结果                              │
└───────────────┬─────────────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│  Dev    │ │ Review  │ │  Test   │
│ Agent   │ │  Agent  │ │  Agent  │
└─────────┘ └─────────┘ └─────────┘
    │           │           │
    ▼           ▼           ▼
 独立上下文   独立上下文   独立上下文
```

## 子 Agent 角色

### Developer Agent（开发者）

**职责**: 代码实现、Bug 修复、重构优化

**启动方式**:
```
Task(
  name="developer",
  prompt="""
【目标】具体的开发任务描述
【输出格式】文件列表、代码片段
【工具指导】Read/Edit/Bash
【任务边界】只做 X，不做 Y

立即开始执行。
""",
  subagent_type="general-purpose"
)
```

**特点**:
- 可以启动多个 Developer Agent 并行工作
- 每个 Agent 有独立上下文窗口
- 返回压缩后的结果给 Lead Agent

---

### Reviewer Agent（审查者）

**职责**: 代码审查、安全检查、性能分析

**启动方式**:
```
Task(
  name="reviewer",
  prompt="""
【目标】审查指定代码的质量
【输出格式】问题列表、改进建议
【工具指导】Read/Grep
【任务边界】只审查，不修改

立即开始执行。
""",
  subagent_type="general-purpose"
)
```

**审查维度**:
- 代码质量
- 安全漏洞
- 性能问题
- 架构设计

---

### Tester Agent（测试者）

**职责**: 测试用例设计、测试执行、问题报告

**启动方式**:
```
Task(
  name="tester",
  prompt="""
【目标】为 X 功能编写测试
【输出格式】测试文件、测试结果
【工具指导】Read/Edit/Bash
【任务边界】只测试，不修改主代码

立即开始执行。
""",
  subagent_type="general-purpose"
)
```

**测试类型**:
- 单元测试
- 集成测试
- 边界测试
- 回归测试

---

### Researcher Agent（研究者）

**职责**: 信息搜索、技术调研、文档编写

**启动方式**:
```
Task(
  name="researcher",
  prompt="""
【目标】调研 X 技术方案
【输出格式】调研报告、对比表格
【工具指导】WebSearch/Read
【任务边界】只调研，不实现

立即开始执行。
""",
  subagent_type="general-purpose"
)
```

**适用场景**:
- 技术选型
- 最佳实践调研
- 问题诊断

---

## 协作规则

### 1. 任务分解

**根据复杂度决定子 Agent 数量**：

| 任务类型 | 分解策略 | 示例 |
|---------|---------|------|
| 单文件修改 | 1 个 Developer | 修复一个 bug |
| 多模块开发 | N 个 Developer（按模块） | 实现用户系统 |
| 功能开发 + 审查 | Developer + Reviewer | 新功能上线 |
| 完整迭代 | Developer + Reviewer + Tester | 发布新版本 |

### 2. 并行执行

**同时启动多个子 Agent**：
```
# 阶段 1：并行开发
Task(name="dev-auth", prompt="...")
Task(name="dev-api", prompt="...")
Task(name="dev-db", prompt="...")

# 阶段 2：等待完成后，启动审查
# （Lead Agent 汇总结果后决定）
Task(name="reviewer", prompt="...")
```

### 3. 结果汇总

**Lead Agent 职责**：
- 收集所有子 Agent 的输出
- 整合结果，解决冲突
- 决定下一步行动

### 4. 错误处理

**子 Agent 失败时**：
- 记录错误信息
- 决定是否重试或降级
- Lead Agent 可以直接接管

---

## ⚠️ 重要原则

### 来自 Anthropic 的最佳实践

1. **教会 Lead Agent 如何委派**
   - 详细描述任务目标、输出格式、工具指导、边界

2. **根据复杂度调整努力**
   - 简单任务：1 个 Agent，少工具调用
   - 复杂任务：多 Agent 并行，多工具调用

3. **工具选择至关重要**
   - 确保 Agent 知道有哪些工具可用
   - 选择正确的工具比努力更重要

4. **先宽后窄**
   - 先探索整体，再深入细节

5. **并行化提速**
   - 同时启动子 Agent
   - 子 Agent 内部并行工具调用

---

## 对比：失败 vs 成功

| 方式 | 后端类型 | 结果 |
|------|----------|------|
| TeamCreate + Task | `in-process` | ❌ idle 永远不执行 |
| 原生 Task + `subagent_type="general-purpose"` | 独立进程 | ✅ 正常执行 |

---

*团队是弹性的，根据任务需要动态创建。每个子 Agent 有独立上下文，完成后返回压缩结果。*
