# TEAM.md - Agent 团队角色

## 角色

这些是**思维角色**，通过 Task 的 `name` 参数指定：

### Developer（开发者）

**职责**: 代码实现、Bug 修复、重构优化

**使用方式**:
```
Task(name="developer", prompt="...立即开始执行...")
```

---

### Reviewer（审查者）

**职责**: 代码审查、安全检查、性能分析

**使用方式**:
```
Task(name="reviewer", prompt="...立即开始执行...")
```

---

### Tester（测试者）

**职责**: 测试用例设计、测试执行、问题报告

**使用方式**:
```
Task(name="tester", prompt="...立即开始执行...")
```

---

## 协作规则

1. **独立执行** - 每个 Task 启动独立 Agent
2. **顺序或并行** - 根据任务依赖关系决定
3. **结果汇总** - Orchestrator 收集各 Agent 结果

## ⚠️ 重要

- **不要使用 TeamCreate** - 会导致 Agent idle
- **直接使用 Task** - 原生方式，稳定可靠
- **prompt 必须包含"立即开始执行"** - 确保 Agent 开始工作
