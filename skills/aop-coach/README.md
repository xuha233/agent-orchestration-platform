# AOP 敏捷教练 Skill

OpenClaw 专用 AOP 敏捷教练 Skill，实现多 Agent 编排、假设驱动开发、任务分解与调度。

## 安装

### 前提条件

- AOP 已安装（`pip install -e .`）
- OpenClaw 已配置

### 方法 1：让 AI 助手帮你安装

将以下内容发给你的 AI 助手（OpenCode、Claude 等）：

```
帮我安装 AOP OpenClaw Skill。AOP 项目路径是 [你的路径]。
```

AI 助手会自动检测你的操作系统并执行正确的安装命令。

### 方法 2：跨平台安装命令

**Python（推荐，跨平台）：**

```bash
cd /path/to/aop

python -c "
import shutil
from pathlib import Path

src = Path('skills/aop-coach')
dst = Path.home() / '.openclaw' / 'skills' / 'aop-coach'
dst.mkdir(parents=True, exist_ok=True)

for f in ['SKILL.md', 'README.md']:
    shutil.copy(src / f, dst / f)

(dst / 'references').mkdir(exist_ok=True)
for f in ['TEAM.md', 'WORKFLOW.md']:
    shutil.copy(src / 'references' / f, dst / 'references' / f)

print(f'✅ Skill installed to: {dst}')
"
```

**Windows PowerShell：**

```powershell
cd G:\docker\aop

$src = "skills\aop-coach"
$dst = "$env:USERPROFILE\.openclaw\skills\aop-coach"

New-Item -ItemType Directory -Path $dst -Force | Out-Null
Copy-Item -Path "$src\SKILL.md", "$src\README.md" -Destination $dst
New-Item -ItemType Directory -Path "$dst\references" -Force | Out-Null
Copy-Item -Path "$src\references\TEAM.md", "$src\references\WORKFLOW.md" -Destination "$dst\references"

Write-Host "✅ Skill installed to: $dst" -ForegroundColor Green
```

**macOS/Linux：**

```bash
cd /path/to/aop

src="skills/aop-coach"
dst="$HOME/.openclaw/skills/aop-coach"

mkdir -p "$dst/references"
cp "$src/SKILL.md" "$src/README.md" "$dst/"
cp "$src/references/TEAM.md" "$src/references/WORKFLOW.md" "$dst/references/"

echo "✅ Skill installed to: $dst"
```

### 方法 3：运行安装脚本

```powershell
# Windows
cd skills/aop-coach
.\install.ps1
```

```bash
# macOS/Linux
cd skills/aop-coach
chmod +x install.sh
./install.sh
```

## 配置 OpenClaw

安装后，在 OpenClaw workspace 的 `AGENTS.md` 中添加：

```markdown
## AOP 敏捷教练集成

触发条件：`-aop run/review/hypothesis/status/dashboard`

识别到 AOP 命令后，读取 `~/.openclaw/skills/aop-coach/SKILL.md` 切换到敏捷教练身份。
```

## 使用

```
-aop run 实现用户登录功能
-aop review 检查 auth.py 的安全性
-aop hypothesis create "使用 Redis 可提升 50% 性能"
-aop status
```

## 核心能力

| 能力 | 说明 |
|------|------|
| 假设驱动开发 | 每个行动都有可验证的假设 |
| AAIF 循环 | 探索 → 构建 → 验证 → 学习 |
| 子 Agent 调度 | Claude Code Team / OpenClaw sessions_spawn |
| 学习捕获 | 自动记录经验教训 |

## 故障排除

**Agent idle 不执行**：切换到队友会话查看错误（Shift+Up/Down + Enter）

**API 403 错误**：创建团队时指定模型 `Use Sonnet for each teammate`

## 相关链接

- AOP 项目：https://github.com/xuha233/agent-orchestration-platform
- OpenClaw 文档：https://docs.openclaw.ai
