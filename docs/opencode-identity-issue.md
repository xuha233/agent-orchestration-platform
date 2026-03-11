# OpenCode 身份加载问题报告

## 问题描述

**OpenCode 无法加载自定义身份提示词，始终返回默认身份。**

### 期望行为

输入 `自我介绍一下`，应该返回：

```
我是 AOP 敏捷教练，负责协调多 Agent 团队完成复杂开发任务...
```

### 实际行为

输入 `自我介绍一下`，返回：

```
我是 opencode，一个交互式 CLI 工具，帮助用户完成软件工程任务...
```

---

## 环境信息

- OpenCode 版本: 1.2.24
- 项目路径: G:\docker\aop
- 全局配置: C:\Users\Ywj\.config\opencode\opencode.json
- 项目配置: G:\docker\aop\opencode.json

---

## 已尝试的配置方案

### 方案 1: 在 opencode.json 添加 `system` 字段

```json
{
  "system": "你是 AOP 敏捷教练..."
}
```

**结果**: ❌ 不生效，OpenCode 似乎不支持 `system` 字段

---

### 方案 2: 使用 `instructions` 字段指向文件

```json
{
  "instructions": ["AGENTS.md"]
}
```

**结果**: ❌ 不生效

---

### 方案 3: 使用 `agent.build.prompt` 指向文件

```json
{
  "agent": {
    "build": {
      "mode": "primary",
      "prompt": "{file:./AGENTS.md}"
    }
  }
}
```

**结果**: ❌ 不生效

---

### 方案 4: 创建 .opencode/agents/aop-coach.md

文件位置: `G:\docker\aop\.opencode\agents\aop-coach.md`

```markdown
---
description: AOP 敏捷教练
mode: primary
model: myprovider/qianfan-code-latest
---

你是 AOP 敏捷教练...
```

**结果**: ❌ 不生效，按 Tab 切换 agent 时看不到这个 agent

---

## 当前配置文件内容

### G:\docker\aop\opencode.json

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "myprovider": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "volcengine",
      "options": {
        "baseURL": "https://qianfan.baidubce.com/v2/coding",
        "apiKey": "bce-v3/ALTAKSP-9XINGTcXdpipuakqc6P7c/b2f9be4299f952bd519a0fa8043619d7a2f7d601"
      },
      "models": {
        "qianfan-code-latest": {
          "name": "qianfan-code-latest"
        }
      }
    }
  },
  "model": "myprovider/qianfan-code-latest",
  "agent": {
    "build": {
      "mode": "primary",
      "model": "myprovider/qianfan-code-latest",
      "prompt": "{file:./AGENTS.md}"
    }
  }
}
```

### G:\docker\aop\AGENTS.md

文件存在，大小 2909 bytes，包含完整的 AOP 敏捷教练身份定义。

---

## 对比：成功的案例

### Claude Code

配置文件: `.claude/CLAUDE.md`
结果: ✅ 成功加载 AOP 敏捷教练身份

### OpenClaw

配置文件: `~/.openclaw/skills/aop-coach/SKILL.md`
结果: ✅ 成功加载 AOP 敏捷教练身份

---

## 问题分析

可能的原因：

1. **配置文件路径问题** - OpenCode 可能没有正确读取项目级配置
2. **配置格式问题** - 可能需要不同的字段名或格式
3. **缓存问题** - OpenCode 可能缓存了旧配置
4. **优先级问题** - 全局配置可能覆盖了项目配置

---

## 需要验证的事项

1. OpenCode 是否正确读取了 `G:\docker\aop\opencode.json`？
2. `{file:./AGENTS.md}` 语法是否正确？
3. 是否需要重启 OpenCode 或清除缓存？
4. 是否需要在启动时指定 agent？

---

## 相关文档

OpenCode Agents 文档: https://opencode.ai/docs/agents

根据文档，agent 配置应该支持：
- `mode`: primary | subagent
- `model`: 模型 ID
- `prompt`: 自定义提示词（支持 `{file:./path}` 语法）
- `tools`: 工具权限

---

## 请求帮助

请帮我诊断为什么 OpenCode 没有加载自定义身份提示词，并提供解决方案。
