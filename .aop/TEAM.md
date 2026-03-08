# TEAM.md - Agent 团队角色

## ⚠️ 关键发现

**TeamCreate 会导致 Agent 使用 `in-process` 后端，进入 idle 模式！**

正确方式：直接使用 Task + `subagent_type="general-purpose"`

---

## 角色

### Developer（开发者）

**职责**: 代码实现、Bug 修复、重构优化

```
Task(name="developer", prompt="...立即开始执行...", subagent_type="general-purpose")
```

---

### Reviewer（审查者）

**职责**: 代码审查、安全检查、性能分析

```
Task(name="reviewer", prompt="...立即开始执行...", subagent_type="general-purpose")
```

---

### Tester（测试者）

**职责**: 测试用例设计、测试执行、问题报告

```
Task(name="tester", prompt="...立即开始执行...", subagent_type="general-purpose")
```

---

## 协作规则

1. **独立执行** - 每个 Task 启动独立 Agent（独立后端）
2. **顺序或并行** - 根据任务依赖关系决定
3. **结果汇总** - Orchestrator 收集各 Agent 结果

## 对比

| 方式 | 后端类型 | Agent 行为 | 结果 |
|------|----------|-----------|------|
| TeamCreate + Task | `in-process` | idle，等待消息 | ❌ 失败 |
| 原生 Task | 独立进程 | 直接执行 prompt | ✅ 成功 |
