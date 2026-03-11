# Agent 启动时自动发送自我介绍 - 解决方案

## 需求

用户点击 Web 页面的"启动 Agent"按钮后，Agent 自动：
1. 发送自我介绍
2. 检查项目初始化情况
3. 显示项目状态面板

---

## 现状分析

### OpenClaw 的实现方式

OpenClaw 通过 **AGENTS.md 的 Every Session 指令** 实现：

```
用户发送第一条消息（如 "你好"）
    ↓
Agent 读取 AGENTS.md（已注入到 system prompt）
    ↓
AGENTS.md 中的 Every Session 指令生效
    ↓
Agent 自我介绍 + 检查项目 + 显示状态
```

**关键点**：需要用户发送第一条消息触发，不是真正的"自动发送"。

### Claude Code / OpenCode 的差异

| Agent | 配置文件 | 自动执行 |
|-------|---------|---------|
| OpenClaw | AGENTS.md (Gateway 注入) | ❌ 需要用户触发 |
| Claude Code | CLAUDE.md (项目目录) | ❌ 需要用户触发 |
| OpenCode | AGENTS.md + opencode.json | ❌ 需要用户触发 |

**所有 Agent 都需要用户发送第一条消息才会开始工作。**

---

## 解决方案

### 方案 1: Web 页面自动发送消息（推荐）

在 Web 页面启动 Agent 后，自动发送一条初始消息：

```javascript
// Web 页面启动 Agent 后
function startAgent(agentType, projectPath) {
    // 启动 Agent
    window.open(agentUrl, "_blank");
    
    // 自动发送初始消息
    setTimeout(() => {
        sendMessage("aop status");
    }, 1000);
}
```

**优点**：
- 简单直接
- 无需修改 Agent 配置
- 用户体验一致

**需要**：Web 页面支持自动发送消息功能

---

### 方案 2: AGENTS.md Every Session 指令

在 AGENTS.md 中定义"Every Session"指令：

```markdown
## Every Session

**会话开始时，立即执行：**

1. 自我介绍："你好，我是 AOP 敏捷教练 🦁..."
2. 检查项目初始化
3. 显示状态面板

**不要等待用户请求，收到第一条消息时立即执行。**
```

**优点**：
- 所有 Agent 通用
- 配置简单

**缺点**：
- 仍需要用户发送第一条消息

---

### 方案 3: OpenClaw Hook（高级）

创建 `session-start` Hook，在收到第一条消息时自动注入初始化指令：

```typescript
// ~/.openclaw/hooks/session-start/handler.ts
const handler = async (event) => {
  if (event.type !== "message" || event.action !== "received") return;
  
  // 检测是否是新会话
  // 如果是，注入初始化指令
};
```

**优点**：
- 自动化程度高
- 可扩展

**缺点**：
- 需要编写代码
- 只对 OpenClaw 生效

---

## 推荐实现

### 第一步：更新 AGENTS.md

确保 AGENTS.md 包含 Every Session 指令（已创建）：
- `C:\Users\Ywj\.openclaw\workspace-claude-code\AGENTS.md`
- `C:\Users\Ywj\.openclaw\workspace-opencode\AGENTS.md`

### 第二步：Web 页面配置

如果 Web 页面支持"启动时发送消息"，配置初始消息为：
```
aop status
```

或者配置为简单的问候：
```
你好
```

### 第三步：测试

1. 启动 Agent
2. 发送 "aop status" 或 "你好"
3. Agent 应该自动执行自我介绍和项目检查

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `workspace-claude-code/AGENTS.md` | Claude Code 项目指令 |
| `workspace-opencode/AGENTS.md` | OpenCode 项目指令 |
| `hooks/session-start/` | OpenClaw Hook（可选） |
| `scripts/start-claude-code.ps1` | 启动脚本（可选） |

---

## 下一步

请确认：
1. Web 页面是否支持"启动时自动发送消息"？
2. 如果支持，如何配置？
3. 如果不支持，是否需要开发这个功能？