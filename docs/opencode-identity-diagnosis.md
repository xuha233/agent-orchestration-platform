# OpenCode 身份加载问题诊断报告

**日期**: 2026-03-11  
**项目**: G:\docker\aop  
**OpenCode 版本**: 1.2.24

---

## 问题摘要

OpenCode 无法加载自定义身份提示词，始终返回默认的 "我是 opencode..." 身份。

---

## 诊断过程

### 1. 配置文件检查

| 文件路径 | 状态 | 问题 |
|----------|------|------|
| `G:\docker\aop\opencode.json` | ✅ 存在 | 缺少必需字段 |
| `G:\docker\aop\AGENTS.md` | ✅ 存在 | BOM 标记 |
| `G:\docker\aop\.opencode\agents\aop-coach.md` | ✅ 存在 | BOM 标记 |
| `C:\Users\Ywj\.config\opencode\opencode.json` | ✅ 存在 | 无冲突 |

### 2. 官方文档验证

查阅 https://opencode.ai/docs/agents 确认配置要求：

- `description`: **必需字段**，描述 agent 功能
- `mode`: 可选，默认 `all`
- `prompt`: 支持 `{file:./path}` 语法
- `model`: 可选，覆盖全局模型

---

## 根因分析

### 根因 1: 缺少必需的 `description` 字段

**严重程度**: 🔴 高

当前 `opencode.json` 配置：

```json
{
  "agent": {
    "build": {
      "mode": "primary",
      "model": "myprovider/qianfan-code-latest",
      "prompt": "{file:./AGENTS.md}",
      "temperature": 0.3,
      "tools": { ... }
    }
  }
}
```

根据官方文档，`description` 是**必需配置项**：

> Use the `description` option to provide a brief description of what the agent does and when to use it.
> This is a **required** config option.

缺少此字段可能导致 OpenCode 无法正确加载自定义 agent 配置。

### 根因 2: UTF-8 BOM 标记

**严重程度**: 🟡 中

以下文件开头包含 UTF-8 BOM (`\ufeff`):

- `G:\docker\aop\AGENTS.md`
- `G:\docker\aop\.opencode\agents\aop-coach.md`

BOM 标记可能影响：
- YAML front matter 解析（Markdown agent）
- `{file:./path}` 语法加载文件内容

### 根因 3: 未指定默认 agent

**严重程度**: 🟢 低

`opencode.json` 中未设置 `default_agent` 字段，OpenCode 默认使用内置 `build` agent。

---

## 解决方案

### 方案 A: 修复 `opencode.json` 配置（推荐）

在 `agent.build` 中添加 `description` 字段：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "myprovider/qianfan-code-latest",
  "agent": {
    "build": {
      "description": "AOP 敏捷教练 - 多 Agent 编排、假设驱动开发、任务分解与调度",
      "mode": "primary",
      "model": "myprovider/qianfan-code-latest",
      "prompt": "{file:./AGENTS.md}",
      "temperature": 0.3
    }
  }
}
```

### 方案 B: 使用 Markdown agent

1. **移除 BOM 标记**（使用支持无 BOM 保存的编辑器）

2. **验证配置**：

```markdown
---
description: AOP 敏捷教练 - 多 Agent 编排、假设驱动开发
mode: primary
model: myprovider/qianfan-code-latest
temperature: 0.3
tools:
  write: true
  edit: true
  bash: true
  read: true
  grep: true
  glob: true
---

# AOP 敏捷教练

你是 AOP 敏捷教练...
```

3. **设置默认 agent**（可选）：

```json
{
  "default_agent": "aop-coach"
}
```

### 方案 C: 启动时指定 agent

```bash
opencode --agent aop-coach
```

或在会话中按 `Tab` 切换 agent。

---

## 验证步骤

1. 修复配置后，重启 OpenCode
2. 输入 `自我介绍一下`
3. 预期输出：

```
我是 AOP 敏捷教练，负责协调多 Agent 团队完成复杂开发任务...
```

4. 按 `Tab` 键，确认 agent 列表中显示 `aop-coach`

---

## 参考

- OpenCode Agents 文档: https://opencode.ai/docs/agents
- OpenCode Config Schema: https://opencode.ai/config.json

---

## 附录：配置文件对比

### 正确配置示例（来自官方文档）

```json
{
  "$schema": "https://opencode.ai/config.json",
  "agent": {
    "build": {
      "description": "Full development agent with all tools enabled",
      "mode": "primary",
      "model": "anthropic/claude-sonnet-4-20250514",
      "prompt": "{file:./prompts/build.txt}",
      "tools": {
        "write": true,
        "edit": true,
        "bash": true
      }
    }
  }
}
```

### 当前配置问题对照

| 字段 | 官方要求 | 当前配置 | 状态 |
|------|----------|----------|------|
| `description` | 必需 | 缺失 | ❌ |
| `mode` | 可选 | `primary` | ✅ |
| `prompt` | 可选 | `{file:./AGENTS.md}` | ✅ |
| `model` | 可选 | 已设置 | ✅ |
| `temperature` | 可选 | `0.3` | ✅ |
| `tools` | 可选 | 已设置 | ✅ |
