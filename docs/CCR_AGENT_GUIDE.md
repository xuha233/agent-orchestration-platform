# Claude Code Router 安装指南（Agent 参考）

> 本文档用于指导 Agent 帮助用户安装和配置 Claude Code Router，以便 Claude Code 能使用第三方模型 API。

## 项目概述

**Claude Code Router** 是一个强大的工具，允许将 Claude Code 的请求路由到不同的 LLM 提供商。

### 核心功能

- **模型路由**：根据场景（后台任务、思考、长上下文）自动选择模型
- **多提供商支持**：OpenRouter、DeepSeek、Gemini、Ollama、Volcengine、SiliconFlow 等
- **请求/响应转换**：通过 transformers 适配不同提供商 API
- **动态模型切换**：在 Claude Code 中使用 `/model` 命令切换模型
- **CLI 模型管理**：`ccr model` 交互式配置
- **GitHub Actions 集成**：CI/CD 管道支持

---

## 安装流程

### 步骤 1：确认前置条件

**询问用户：**

```
是否已安装 Claude Code？请运行以下命令确认：

claude --version

如果未安装，请先运行：

npm install -g @anthropic-ai/claude-code
```

### 步骤 2：安装 Claude Code Router

```bash
npm install -g @musistudio/claude-code-router
```

### 步骤 3：询问配置信息

逐一询问用户以下信息：

#### 3.1 模型提供商名称

```
请问您想使用哪个模型提供商？

可选：
- openrouter（推荐，支持多种模型）
- deepseek（性价比高）
- gemini（Google 模型）
- ollama（本地运行）
- volcengine（火山引擎）
- siliconflow（硅基流动）

或输入自定义提供商名称：
```

#### 3.2 API Base URL

根据用户选择的提供商，提供默认 URL 或询问自定义 URL：

```
API 端点地址：

【DeepSeek】https://api.deepseek.com/chat/completions
【Gemini】https://generativelanguage.googleapis.com/v1beta/models/
【OpenRouter】https://openrouter.ai/api/v1/chat/completions
【Ollama】http://localhost:11434/v1/chat/completions
【火山引擎】https://ark.cn-beijing.volces.com/api/v3/chat/completions
【硅基流动】https://api.siliconflow.cn/v1/chat/completions

请输入 API 地址（或按 Enter 使用默认值）：
```

#### 3.3 API Key

```
请提供您的 API Key（格式通常为 sk-xxx）：

⚠️ 注意：这个信息会被安全存储在本地配置文件 ~/.claude-code-router/config.json 中
```

#### 3.4 可用模型列表

```
请提供您想使用的模型名称列表（逗号分隔）：

【DeepSeek 示例】deepseek-chat, deepseek-reasoner
【Gemini 示例】gemini-2.5-flash, gemini-2.5-pro
【OpenRouter 示例】anthropic/claude-sonnet-4, google/gemini-2.5-pro-preview
【Ollama 示例】qwen2.5-coder:latest

请输入模型列表：
```

#### 3.5 默认模型

```
请指定默认使用的模型（格式：provider_name,model_name）：

示例：deepseek,deepseek-chat

请输入默认模型：
```

---

## 步骤 4：创建配置文件

根据用户提供的信息，创建 `~/.claude-code-router/config.json` 文件。

### 配置文件结构

```json
{
  "LOG": true,
  "API_TIMEOUT_MS": 600000,
  "Providers": [
    {
      "name": "<提供商名称>",
      "api_base_url": "<API 地址>",
      "api_key": "<API Key>",
      "models": ["<模型1>", "<模型2>"],
      "transformer": {
        "use": ["<转换器>"]
      }
    }
  ],
  "Router": {
    "default": "<提供商>,<模型名>"
  }
}
```

### 常见提供商配置示例

#### DeepSeek

```json
{
  "name": "deepseek",
  "api_base_url": "https://api.deepseek.com/chat/completions",
  "api_key": "sk-xxx",
  "models": ["deepseek-chat", "deepseek-reasoner"],
  "transformer": {
    "use": ["deepseek"],
    "deepseek-chat": { "use": ["tooluse"] }
  }
}
```

#### OpenRouter

```json
{
  "name": "openrouter",
  "api_base_url": "https://openrouter.ai/api/v1/chat/completions",
  "api_key": "sk-or-xxx",
  "models": [
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-pro-preview"
  ],
  "transformer": {
    "use": ["openrouter"]
  }
}
```

#### Gemini

```json
{
  "name": "gemini",
  "api_base_url": "https://generativelanguage.googleapis.com/v1beta/models/",
  "api_key": "xxx",
  "models": ["gemini-2.5-flash", "gemini-2.5-pro"],
  "transformer": {
    "use": ["gemini"]
  }
}
```

#### Ollama（本地）

```json
{
  "name": "ollama",
  "api_base_url": "http://localhost:11434/v1/chat/completions",
  "api_key": "ollama",
  "models": ["qwen2.5-coder:latest"]
}
```

#### 火山引擎

```json
{
  "name": "volcengine",
  "api_base_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
  "api_key": "xxx",
  "models": ["deepseek-v3-250324"],
  "transformer": {
    "use": ["deepseek"]
  }
}
```

---

## 步骤 5：验证安装

```bash
# 启动 Claude Code Router
ccr code

# 或使用 UI 模式管理配置
ccr ui

# 或使用 CLI 模式选择模型
ccr model
```

---

## Transformer 说明

不同的提供商需要不同的 transformer 来适配 API 格式：

| 提供商 | Transformer | 说明 |
|--------|-------------|------|
| Anthropic | `anthropic` | 保持原始格式 |
| DeepSeek | `deepseek` | 适配 DeepSeek API |
| Gemini | `gemini` | 适配 Gemini API |
| OpenRouter | `openrouter` | 适配 OpenRouter API |
| Groq | `groq` | 适配 Groq API |

### 特殊 Transformer

| Transformer | 用途 |
|-------------|------|
| `tooluse` | 优化工具调用 |
| `maxtoken` | 设置 max_tokens 参数 |
| `reasoning` | 处理推理内容字段 |
| `enhancetool` | 增强工具调用容错性 |

---

## 路由配置

Router 对象定义不同场景使用的模型：

```json
{
  "Router": {
    "default": "deepseek,deepseek-chat",
    "background": "ollama,qwen2.5-coder:latest",
    "think": "deepseek,deepseek-reasoner",
    "longContext": "gemini,gemini-2.5-pro",
    "longContextThreshold": 60000,
    "webSearch": "gemini,gemini-2.5-flash"
  }
}
```

| 字段 | 说明 |
|------|------|
| `default` | 默认模型 |
| `background` | 后台任务模型（可节省成本） |
| `think` | 推理密集型任务（如 Plan Mode） |
| `longContext` | 长上下文任务（> 60K tokens） |
| `longContextThreshold` | 触发长上下文模型的阈值 |
| `webSearch` | 网页搜索任务 |

---

## 常用命令

```bash
# 使用 Router 启动 Claude Code
ccr code

# 启动 Web UI 管理配置
ccr ui

# CLI 模式管理模型
ccr model

# 重启服务（修改配置后）
ccr restart

# 查看状态
ccr status

# 停止服务
ccr stop

# 启动服务
ccr start

# 环境变量激活（让 claude 命令直接使用 Router）
eval "$(ccr activate)"

# 预设管理
ccr preset export my-preset
ccr preset install /path/to/preset
ccr preset list
```

---

## 子 Agent 路由

在子 Agent 的提示词开头添加特殊标签来指定模型：

```
<CCR-SUBAGENT-MODEL>openrouter,anthropic/claude-3.5-sonnet</CCR-SUBAGENT-MODEL>
Please help me analyze this code snippet...
```

---

## 环境变量激活

如果想让 `claude` 命令直接使用 Router，可以激活环境变量：

```bash
# 在当前 shell 会话中激活
eval "$(ccr activate)"

# 或添加到 shell 配置文件（持久化）
echo 'eval "$(ccr activate)"' >> ~/.bashrc
# 或
echo 'eval "$(ccr activate)"' >> ~/.zshrc
```

---

## 故障排除

### 安装失败

1. 检查 Node.js 版本（需要 >= 18.0.0）
2. 检查网络连接
3. 尝试使用代理

### API 调用失败

1. 检查 API Key 是否正确
2. 检查 API Base URL 是否正确
3. 检查模型名称是否正确
4. 查看日志：
   - 服务器日志：`~/.claude-code-router/logs/ccr-*.log`
   - 应用日志：`~/.claude-code-router/claude-code-router.log`

### 配置修改后不生效

重启服务：`ccr restart`

---

## 参考链接

- **项目地址**：https://github.com/musistudio/claude-code-router
- **Claude Code 文档**：https://docs.anthropic.com/en/docs/claude-code/quickstart
- **问题反馈**：https://github.com/musistudio/claude-code-router/issues

---

## 总结：Agent 引导流程

1. **询问是否需要使用第三方 API**
   - 如果 **否** → 跳过此步骤
   - 如果 **是** → 继续

2. **确认 Claude Code 已安装** → `claude --version`

3. **安装 CCR** → `npm install -g @musistudio/claude-code-router`

4. **询问配置信息**：提供商、BaseURL、API Key、模型列表、默认模型

5. **创建配置文件** → `~/.claude-code-router/config.json`

6. **验证安装** → `ccr code` 或 `ccr ui`

7. **可选：环境变量激活** → `eval "$(ccr activate)"`
