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

---

## 任务派遣（使用原生 Task）

**⚠️ 必须包含 `subagent_type="general-purpose"`，否则 Agent 会 idle！**

### 新功能开发

```
Task(name="developer", prompt="实现用户登录功能...立即开始执行...", subagent_type="general-purpose")
# 等待完成
Task(name="reviewer", prompt="审查登录功能的代码质量...立即开始执行...", subagent_type="general-purpose")
# 最后
Task(name="tester", prompt="为登录功能编写测试...立即开始执行...", subagent_type="general-purpose")
```

### Bug 修复

```
Task(name="developer", prompt="定位并修复 XXX 问题...立即开始执行...", subagent_type="general-purpose")
Task(name="tester", prompt="验证修复是否生效...立即开始执行...", subagent_type="general-purpose")
```

### 代码重构

```
Task(name="developer", prompt="重构 XXX 模块...立即开始执行...", subagent_type="general-purpose")
Task(name="reviewer", prompt="检查重构后的代码质量...立即开始执行...", subagent_type="general-purpose")
```

---

## 假设格式

```
假设: 如果 [行动]，那么 [预期结果]
优先级: P0/P1/P2/P3
验证标准: [如何验证]
状态: pending/testing/validated/refuted
```

---

## ⛔ 禁止使用 TeamCreate

TeamCreate → `in-process` 后端 → Agent idle → 永远不执行

使用原生 Task → 独立后端 → Agent 直接执行 → 成功
