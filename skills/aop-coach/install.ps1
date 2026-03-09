# AOP 敏捷教练 Skill 安装脚本 (OpenClaw)
# 用法: .\install.ps1 [-OpenClawSkillsPath "path"]

param(
  [string]$OpenClawSkillsPath = "$env:USERPROFILE\.openclaw\skills"
)

Write-Host "AOP 敏捷教练 Skill 安装脚本" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

# 检测 OpenClaw 技能目录
$defaultPath = $OpenClawSkillsPath
if (-not (Test-Path $defaultPath)) {
  Write-Host "创建 OpenClaw skills 目录: $defaultPath" -ForegroundColor Yellow
  New-Item -ItemType Directory -Path $defaultPath -Force | Out-Null
}

# 源目录（脚本所在目录）
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDir = $scriptDir

# 目标目录
$targetDir = Join-Path $defaultPath "aop-coach"

Write-Host ""
Write-Host "安装 AOP 敏捷教练 Skill..." -ForegroundColor Yellow
Write-Host "  源目录: $sourceDir"
Write-Host "  目标目录: $targetDir"

# 创建目标目录
if (-not (Test-Path $targetDir)) {
  New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

# 复制文件
$filesToCopy = @(
  "SKILL.md",
  "references\TEAM.md",
  "references\WORKFLOW.md"
)

foreach ($file in $filesToCopy) {
  $src = Join-Path $sourceDir $file
  $dst = Join-Path $targetDir $file
  
  if (Test-Path $src) {
    $dstDir = Split-Path -Parent $dst
    if (-not (Test-Path $dstDir)) {
      New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }
    Copy-Item $src $dst -Force
    Write-Host "  [OK] $file" -ForegroundColor Green
  } else {
    Write-Host "  [SKIP] $file (不存在)" -ForegroundColor Yellow
  }
}

# 验证安装
Write-Host ""
Write-Host "验证安装..." -ForegroundColor Yellow

$skillFile = Join-Path $targetDir "SKILL.md"
if (Test-Path $skillFile) {
  Write-Host "[OK] AOP 敏捷教练 Skill 安装成功!" -ForegroundColor Green
} else {
  Write-Host "[X] 安装失败" -ForegroundColor Red
  exit 1
}

# 更新 AGENTS.md 提示
Write-Host ""
Write-Host "下一步:" -ForegroundColor Cyan
Write-Host "  1. 将以下内容添加到 OpenClaw workspace 的 AGENTS.md:"
Write-Host ""
Write-Host "     ## AOP 敏捷教练集成"
Write-Host "     触发条件: -aop run/review/hypothesis/status/dashboard"
Write-Host "     Skill 位置: ~/.openclaw/skills/aop-coach/SKILL.md"
Write-Host ""
Write-Host "  2. 重启 OpenClaw 或开始新会话"
Write-Host ""
Write-Host "快速测试:" -ForegroundColor Cyan
Write-Host "  在 OpenClaw 中输入: -aop status"
