# TEAM.md - Agent 团队角色

## ⚠️ 关键发现：API 配置问题

**Team 功能本身正常，问题是子 Agent 的 API 配置！**

### 问题表现

```
Agent 启动 → 发送 idle_notification → 用户以为卡住了
                    ↓
          实际：Agent 遇到 API 403 错误
                    ↓
          解决：切换到队友会话查看错误
```

### 解决方案

1. **创建团队时指定模型**：
```
Use Sonnet for each teammate.
```

2. **切换到队友会话检查**：
   - Shift+Up/Down 选择队友
   - Enter 查看会话
   - 检查是否有 API 错误
   - 如果有，运行 `/login`

---

## In-process 模式操作

### Windows 限制

- **不支持 Split panes 模式**（需要 tmux/iTerm2）
- **只能用 In-process 模式**
- **需要用键盘切换队友**

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| Shift+Up/Down | 选择队友 |
| Enter | 查看队友会话 |
| Escape | 中断队友操作 |
| Ctrl+T | 切换任务列表 |

---

## 核心架构

```
Team Lead (你)
├── 创建团队（自然语言）
├── 分配任务（详细上下文）
├── 切换到队友会话检查状态
└── 汇总结果

Teammates (独立实例)
├── 每人有独立的上下文窗口
├── 可能有独立的 API 配置
└── 需要切换到会话查看执行状态
```

---

## 团队角色

### Developer（开发者）

**职责**: 代码实现、Bug 修复、重构优化

**创建示例**:
```
队友A（数据层）：负责 Model 实体类 + DAL 数据访问层
- 文件范围：src/model/、src/dal/
- 参考：InboundOrderDAL 风格
- 交付物：实体类、DAL 类

Use Sonnet for this teammate.
```

---

### Reviewer（审查者）

**职责**: 代码审查、安全检查、性能分析

**创建示例**:
```
队友B（代码审查）：负责审查所有代码改动
- 审查维度：安全性、性能、可维护性
- 输出：问题列表 + 改进建议
- 不要修改代码，只审查

Use Sonnet for this teammate.
```

---

### Tester（测试者）

**职责**: 测试用例设计、测试执行、问题报告

**创建示例**:
```
队友C（测试）：负责编写和运行测试
- 文件范围：tests/
- 测试类型：单元测试、集成测试
- 输出：测试文件、测试报告

Use Sonnet for this teammate.
```

---

## 创建团队完整流程

### 步骤 1：用自然语言创建团队

```
创建一个 agent team 来开发商品盘点功能：

- 队友A（数据层）：负责 Model + DAL
  文件范围：src/model/、src/dal/
  参考：InboundOrderDAL 风格

- 队友B（业务层）：负责 Interface + BLL
  文件范围：src/interface/、src/bll/

- 队友C（API层）：负责 Controller
  文件范围：src/api/controllers/

Use Sonnet for each teammate.
```

### 步骤 2：切换到队友会话检查

```
Shift+Up/Down  → 选择队友 A
Enter          → 查看会话
（检查是否有错误，是否在执行任务）
Escape         → 返回主会话

Shift+Up/Down  → 选择队友 B
...
```

### 步骤 3：处理 API 错误

如果看到 API 403 错误：
1. 在队友会话中输入 `/login`
2. 按照提示完成认证
3. 重新执行任务

### 步骤 4：等待完成

```
Wait for your teammates to complete their tasks before proceeding
```

---

## 故障排除

### Agent 一直 idle

1. **切换到队友会话**（Shift+Up/Down + Enter）
2. **查看错误信息**
3. **如果是 API 错误，运行 `/login`**
4. **如果模型不支持，重新创建团队并指定模型**

### API 403: coding_plan_model_not_supported

原因：子 Agent 使用的模型不支持 Coding Plan

解决：
```
# 创建团队时指定模型
Use Sonnet for each teammate.

# 或在队友会话中运行
/model claude-sonnet-4-20250514
```

### 子 Agent 没有继承主会话认证

解决：
- 在队友会话中运行 `/login`
- 或使用 OAuth token 方式认证

---

## 最佳实践

1. **创建团队时指定模型**：`Use Sonnet for each teammate`
2. **切换到队友会话检查状态**：不要只看 idle_notification
3. **提供详细上下文**：队友不继承你的对话历史
4. **按层分配 > 按文件分配**：避免冲突
5. **任务粒度适中**：自包含的工作单元

---

## 与 Subagents 的区别

| 对比项 | Subagents | Agent Teams |
|--------|-----------|-------------|
| 上下文 | 独立窗口 | 完全独立的实例 |
| 通信 | 只能向主代理汇报 | 队友之间可直接通信 |
| 需要切换 | 不需要 | 需要（Shift+Up/Down） |
| API 配置 | 继承主会话 | 可能需要单独配置 |
| 适用场景 | 简单、顺序性任务 | 复杂、协作任务 |

**选择指南**：
- 简单任务 → 用 Subagent
- 复杂协作 → 用 Agent Teams（记得切换到队友会话检查）
