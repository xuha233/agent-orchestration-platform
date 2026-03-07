# WORKFLOW.md - 工作流程

## ⚠️ 重要说明

**当前版本不支持真正的多 Agent 调度！**

WORKFLOW.md 中的"Orchestrator: xxx"、"Developer: xxx"等描述是**角色切换**，不是启动独立 Agent。
- 当你切换到"Developer"角色时，你**自己直接执行**开发任务
- 当你切换到"Reviewer"角色时，你**自己直接执行**审查任务
- **禁止使用 Claude Code 的 Team 功能**（TeamCreate、Task()、SendMessage 等）

---

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

## 工作流示例（单人执行，角色切换）

### 新功能开发
1. [Orchestrator 角色] 生成假设 "如果添加 X 功能，那么用户效率提升 Y%"
2. [Developer 角色] 实现功能代码
3. [Tester 角色] 编写测试用例
4. [Reviewer 角色] 代码审查
5. [Orchestrator 角色] 验证假设，提取学习

### Bug 修复
1. [Orchestrator 角色] 分析问题，生成假设
2. [Developer 角色] 定位并修复
3. [Tester 角色] 验证修复
4. [Orchestrator 角色] 更新记忆，防止复发

### 代码重构
1. [Orchestrator 角色] 识别重构目标
2. [Developer 角色] 实施重构
3. [Reviewer 角色] 检查质量
4. [Tester 角色] 确保功能不变
5. [Orchestrator 角色] 记录改进效果

## 假设格式

```
假设: 如果 [行动]，那么 [预期结果]
优先级: P0/P1/P2/P3
验证标准: [如何验证]
状态: pending/testing/validated/refuted
```

---

*工作流程是活的，根据项目需要持续优化。*
