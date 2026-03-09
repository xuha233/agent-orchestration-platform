# AOP 敏捷教练 Skill

OpenClaw 专用 AOP 敏捷教练 Skill，实现多 Agent 编排、假设驱动开发、任务分解与调度。

## 安装

### 方法 1：运行安装脚本

```powershell
cd G:\docker\aop\skills\aop-coach
.\install.ps1
```

### 方法 2：手动安装

1. 复制 skill 到 OpenClaw skills 目录：

```powershell
# Windows
$src = "G:\docker\aop\skills\aop-coach"
$dst = "$env:USERPROFILE\.openclaw\skills\aop-coach"

Copy-Item -Path $src -Destination $dst -Recurse -Force
```

2. 在 OpenClaw workspace 的 `AGENTS.md` 中添加：

```markdown
## AOP 敏捷教练集成

### 触发条件

识别到以下模式时，读取 `~/.openclaw/skills/aop-coach/SKILL.md` 并切换到敏捷教练身份：

1. AOP 命令：`-aop run/review/hypothesis/status/dashboard`
2. 自然语言：帮我分解任务、启动开发、代码审查

### 支持的命令

| 命令 | 说明 |
|------|------|
| run | 运行任务（探索→构建→验证→学习）|
| review | 代码审查 |
| hypothesis | 假设管理 |
| status | 查看状态 |
| dashboard | Dashboard 操作 |
```

## 使用

### 基本命令

```
-aop run 实现用户登录功能
-aop review 检查 auth.py 的安全性
-aop hypothesis create "使用 Redis 可提升 50% 性能"
-aop status
```

### 自然语言触发

```
帮我分解这个任务
启动开发用户认证模块
代码审查
```

## 核心能力

### 假设驱动开发 (HDD)

每个行动都有可验证的假设：

```
假设 H-001: 如果 [采取行动]，那么 [预期结果]
验证方法: [如何验证]
成功标准: [量化指标]
```

### AAIF 循环

探索 → 构建 → 验证 → 学习（循环往复）

### 子 Agent 调度

- **Claude Code**：TeamCreate + Task
- **OpenClaw**：sessions_spawn

## 文件结构

```
aop-coach/
├── SKILL.md              # 核心文件（身份定义 + 命令处理）
├── install.ps1           # 安装脚本
├── README.md             # 本文件
└── references/
    ├── TEAM.md           # Agent 角色定义
    └── WORKFLOW.md       # 完整工作流程
```

## 故障排除

### Agent idle 不执行

1. 切换到队友会话查看错误（Shift+Up/Down + Enter）
2. 检查 API 配置
3. 在队友会话中 `/login`
4. 或重新创建团队，指定模型

### API 403 错误

创建团队时指定模型：

```
创建 agent team，使用 Sonnet 模型：
- CoderA: ...
Use Sonnet for each teammate.
```

## 相关链接

- AOP 项目：https://github.com/xuha233/agent-orchestration-platform
- OpenClaw 文档：https://docs.openclaw.ai
