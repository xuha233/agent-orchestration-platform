# CLAUDE.md / AGENTS.md 自动启动流程分析

## 问题现象

用户在 CLAUDE.md 和 AGENTS.md 中添加了"首次启动流程"指令，期望 Agent 启动时自动执行，但实际未生效。

## 根本原因

### 1. CLAUDE.md 是"上下文"而非"可执行脚本"

根据 Claude Code 官方文档：

> CLAUDE.md files are loaded into the context window at the start of every session.
> CLAUDE.md is context, not enforcement.

**这意味着：**
- CLAUDE.md 的内容会被读取并加载到 session 中
- 但 Agent **不会自动执行**其中的指令
- Agent 启动后默认显示欢迎界面，**等待用户输入**

### 2. AGENTS.md 同样是 Prompt 上下文

OpenCode 的配置：

```json
{
  "agent": {
    "build": {
      "prompt": "{file:./AGENTS.md}"
    }
  }
}
```

这只会把 AGENTS.md 的内容加载到 agent 的 prompt 中，不会自动执行。

### 3. OpenClaw 的实现方式

OpenClaw 的 SKILL.md 使用 description 字段定义触发条件：

```yaml
---
description: "触发：(1) AOP 命令，(2) 用户说 '帮我分解任务'..."
---
```

当用户输入匹配的内容时，Claude 会自动加载这个 skill。**但这仍然需要用户输入触发。**

## 正确的使用方式

### 方案 A：使用 Skill 机制（推荐）

创建 .claude/skills/aop-startup/SKILL.md：

```yaml
---
name: aop-startup
description: "AOP 启动流程 - 当用户说 '启动'、'开始'、'init'、'status' 时触发"
---
```

用户输入 /aop-startup 或匹配的触发词即可启动。

### 方案 B：在 CLAUDE.md 中说明使用方式

```markdown
## 🚀 快速启动

**启动 Claude Code 后，输入以下命令开始工作：**

- op status - 显示项目状态
- op run <任务> - 启动开发任务
```

### 方案 C：使用 Hook（高级）

Claude Code 支持 Hook 机制，可以在特定事件触发时执行脚本：

```json
// .claude/settings.json
{
  "hooks": {
    "SessionStart": {
      "command": "echo '请输入 aop status 开始'"
    }
  }
}
```

## 结论

**CLAUDE.md 和 AGENTS.md 不能实现"启动时自动执行"**。这是因为：

1. 它们被设计为上下文信息，而非可执行脚本
2. Agent 默认等待用户输入才会开始工作
3. 要实现自动化，需要使用 Skill 或 Hook 机制

## 修改后的文件

1. .claude/CLAUDE.md - 去掉"自动执行"描述，改为"快速启动"说明
2. AGENTS.md - 同步更新
3. .claude/skills/aop-startup/SKILL.md - 新建，提供 /aop-startup 命令

## 测试验证

1. 在项目目录启动 Claude Code：cd G:\docker\aop && claude
2. 输入 op status 或 /aop-startup
3. 确认状态面板正确显示
