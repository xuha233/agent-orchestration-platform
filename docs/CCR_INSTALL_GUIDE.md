# Claude Code Router 安装指南

本文档用于指导 Agent 帮助用户安装和配置 Claude Code Router，以便 Claude Code 能使用第三方模型 API。

## 什么是 Claude Code Router？

Claude Code Router 是一个强大的工具，允许将 Claude Code 的请求路由到不同的模型提供商，支持：
- OpenRouter
- DeepSeek
- Gemini
- Ollama
- Volcengine
- SiliconFlow
- 等更多...

## 安装流程

### 步骤 1：确认前置条件

询问用户：
```
是否已经安装了 Claude Code？请运行以下命令确认：
claude --version

如果未安装，请先运行：
npm install -g @anthropic-ai/claude-code
```

### 步骤 2：安装 Claude Code Router

指导用户运行：
```bash
npm install -g @musistudio/claude-code-router
```

### 步骤 3：询问配置信息

逐一询问用户以下信息：

1. **模型提供商名称**
   ```
   请问您想使用哪个模型提供商？
   可选：openrouter, deepseek, gemini, ollama, volcengine, siliconflow 等
   ```

2. **API Base URL**
   ```
   请提供 API 端点地址，例如：
   - OpenRouter: https://openrouter.ai/api/v1/chat/completions
   - DeepSeek: https://api.deepseek.com/chat/completions
   - Gemini: https://generativelanguage.googleapis.com/v1beta/models/
   - 自定义：请输入您的 API 地址
   ```

3. **API Key**
   ```
   请提供您的 API Key（格式通常为 sk-xxx）：
   注意：这个信息会被安全存储在本地配置文件中
   ```

4. **可用模型列表**
   ```
   请提供您想使用的模型名称列表，例如：
   - deepseek-chat, deepseek-reasoner
   - gemini-2.5-flash, gemini-2.5-pro
   - 或其他您有权限访问的模型
   ```

5. **默认模型**
   ```
   请指定默认使用的模型（provider_name,model_name 格式）：
   例如：deepseek,deepseek-chat
   ```

### 步骤 4：创建配置文件

根据用户提供的信息，创建 `~/.claude-code-router/config.json` 文件：

```json
{
  "LOG": true,
  "API_TIMEOUT_MS": 600000,
  "Providers": [
    {
      "name": "<用户提供的提供商名称>",
      "api_base_url": "<用户提供的 API 地址>",
      "api_key": "<用户提供的 API Key>",
      "models": [<用户提供的模型列表>],
      "transformer": {
        "use": ["<对应的转换器>"]
      }
    }
  ],
  "Router": {
    "default": "<用户指定的默认模型>"
  }
}
```

### 步骤 5：验证安装

指导用户运行：
```bash
# 启动 Claude Code Router
ccr code

# 或使用 UI 模式管理配置
ccr ui

# 或使用 CLI 模式选择模型
ccr model
```

## 常见提供商配置示例

### DeepSeek

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

### OpenRouter

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

### Gemini

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

### Ollama（本地）

```json
{
  "name": "ollama",
  "api_base_url": "http://localhost:11434/v1/chat/completions",
  "api_key": "ollama",
  "models": ["qwen2.5-coder:latest"]
}
```

### 火山引擎

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

## Transformer 说明

不同的提供商需要不同的 transformer 来适配 API 格式：

| 提供商 | Transformer | 说明 |
|--------|-------------|------|
| Anthropic | anthropic | 保持原始格式 |
| DeepSeek | deepseek | 适配 DeepSeek API |
| Gemini | gemini | 适配 Gemini API |
| OpenRouter | openrouter | 适配 OpenRouter API |
| Groq | groq | 适配 Groq API |

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

- **default**: 默认模型
- **background**: 后台任务模型（可节省成本）
- **think**: 推理密集型任务
- **longContext**: 长上下文任务
- **webSearch**: 网页搜索任务

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

# 导出配置预设
ccr preset export my-preset

# 安装配置预设
ccr preset install /path/to/preset
```

## 环境变量激活

如果想让 `claude` 命令直接使用 Router，可以激活环境变量：

```bash
# 在 shell 中执行
eval "$(ccr activate)"

# 或添加到 shell 配置文件（持久化）
echo 'eval "$(ccr activate)"' >> ~/.bashrc
# 或
echo 'eval "$(ccr activate)"' >> ~/.zshrc
```

## 故障排除

### 安装失败

1. 检查 Node.js 版本（需要 v18+）
2. 检查网络连接
3. 尝试使用代理：`npm config set proxy http://127.0.0.1:7890`

### API 调用失败

1. 检查 API Key 是否正确
2. 检查 API Base URL 是否正确
3. 检查模型名称是否正确
4. 查看日志：`~/.claude-code-router/claude-code-router.log`

### 模型不支持工具调用

某些模型可能需要特殊配置：

```json
{
  "transformer": {
    "use": ["tooluse"]
  }
}
```

## 参考链接

- 项目地址：https://github.com/musistudio/claude-code-router
- Claude Code 文档：https://docs.anthropic.com/en/docs/claude-code/quickstart
- 问题反馈：https://github.com/musistudio/claude-code-router/issues
