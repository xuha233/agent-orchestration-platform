# WORKFLOW.md - 工作流程

## 假设驱动开发 (HDD)

核心循环：**探索 → 构建 → 验证 → 学习**

### 1. 探索 (Explore)
- 理解用户需求
- 搜索代码库了解上下文
- 生成假设（如果...那么...）
- 设置验证标准

### 2. 构建 (Build)
- 设计解决方案
- 编写代码实现
- 遵循现有代码风格
- 保持最小改动

### 3. 验证 (Validate)
- 运行测试
- 检查代码质量
- 验证假设是否成立
- 收集证据

### 4. 学习 (Learn)
- 提取经验教训
- 更新项目记忆
- 优化工作流程
- 归档假设结果

## Agent 角色

### Orchestrator（敏捷教练/项目经理）
- 澄清需求
- 生成假设
- 编排任务
- 跟踪进度
- 提取学习

### Developer（开发者）
- 实现代码
- 修复 bug
- 重构优化
- 编写测试

### Reviewer（审查者）
- 代码审查
- 安全检查
- 性能分析
- 风格检查

### Tester（测试者）
- 编写测试用例
- 执行测试
- 报告问题
- 验证修复

## 并行工作流示例

### 新功能开发（使用 Claude Code Team 功能）

```
1. [Orchestrator] TeamCreate(team_name="feature-team", members=["developer", "reviewer", "tester"])
2. [Orchestrator] Task(agent="developer", prompt="实现功能代码...")
3. [Orchestrator] 监控进度，等待 developer 完成
4. [Orchestrator] Task(agent="reviewer", prompt="审查代码...")
5. [Orchestrator] 根据审查结果决定下一步
6. [Orchestrator] Task(agent="tester", prompt="编写测试...")
7. [Orchestrator] 验证假设，提取学习
```

### Bug 修复

```
1. [Orchestrator] 分析问题，生成假设
2. [Orchestrator] Task(agent="developer", prompt="定位并修复 bug...")
3. [Orchestrator] Task(agent="tester", prompt="验证修复...")
4. [Orchestrator] 更新记忆，防止复发
```

### 代码重构

```
1. [Orchestrator] 识别重构目标
2. [Orchestrator] Task(agent="developer", prompt="实施重构...")
3. [Orchestrator] Task(agent="reviewer", prompt="检查质量...")
4. [Orchestrator] Task(agent="tester", prompt="确保功能不变...")
5. [Orchestrator] 记录改进效果
```

## 假设格式

```
假设: 如果 [行动]，那么 [预期结果]
优先级: P0/P1/P2/P3
验证标准: [如何验证]
状态: pending/testing/validated/refuted
```

## 故障处理

如果子 Agent 不响应：
1. **发送明确的开始信号**：`SendMessage(to="developer", content="请开始执行任务，第一步是...")`
2. **检查 prompt 格式**：确保包含"立即开始执行"
3. **直接接管**：如果仍然无响应，Orchestrator 直接执行

---

*工作流程是活的，根据项目需要持续优化。利用 Claude Code Team 功能实现高效并行调度。*
