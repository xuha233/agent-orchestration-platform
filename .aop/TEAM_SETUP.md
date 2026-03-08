# TEAM_SETUP.md - Claude Code Team 触发器

## 触发方式

当用户说以下任一关键词时，立即执行团队创建流程：
- `use team`
- `创建团队`
- `start team`
- `建立团队`

## 执行步骤

### 步骤 1：创建团队

```
TeamCreate(
  team_name="开发团队",
  members=["developer", "reviewer", "tester"]
)
```

### 步骤 2：确认团队已创建

回复用户：
> 团队已创建。请告诉我你想要团队完成什么任务？

### 步骤 3：根据用户任务派遣 Agent

```
Task(
  agent="developer",
  prompt="【任务描述】

请立即开始执行，第一步是...",
  mode="acceptEdits"
)
```

**重要**：Task 的 prompt 必须包含"立即开始执行"，否则 Agent 可能不响应。

### 步骤 4：监控和获取输出

```
TaskOutput(task_id="developer@task-name")
```

---

## 团队角色

| 角色 | 职责 |
|------|------|
| developer | 代码实现、Bug 修复、重构优化 |
| reviewer | 代码审查、安全检查、性能分析 |
| tester | 测试用例、测试执行、问题报告 |

---

## 故障排除

如果 Agent 启动后不执行：
1. 确保 prompt 包含"立即开始执行"
2. 发送明确的开始信号
3. 如果仍然无响应，Orchestrator 直接接管任务

---

*这是一个轻量级触发器，不干扰 Claude Code 的内置 Team 功能。*
