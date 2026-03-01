# AOP 一键安装脚本 (Windows PowerShell)
# 用法: .\install.ps1 [-Dev]

param(
  [switch]\
)

Write-Host "AOP - Agent Orchestration Platform 安装脚本" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# 检查前置要求
Write-Host ""
Write-Host "检查前置要求..." -ForegroundColor Yellow

\ = \True

# 检查 Python
if (Get-Command python -ErrorAction SilentlyContinue) {
  \ = python --version 2>&1
  Write-Host "[OK] Python: \" -ForegroundColor Green
} else {
  Write-Host "[X] Python 未安装" -ForegroundColor Red
  \ = \False
}

# 检查 pip
if (Get-Command pip -ErrorAction SilentlyContinue) {
  Write-Host "[OK] pip 已安装" -ForegroundColor Green
} else {
  Write-Host "[X] pip 未安装" -ForegroundColor Red
  \ = \False
}

if (-not \) {
  Write-Host ""
  Write-Host "缺少必要依赖，请先安装 Python 3.10+ 和 pip。" -ForegroundColor Red
  exit 1
}

# 安装 AOP
Write-Host ""
Write-Host "安装 AOP..." -ForegroundColor Yellow

if (\) {
  pip install -e ".[dev]"
} else {
  pip install -e .
}

# 验证安装
Write-Host ""
Write-Host "验证安装..." -ForegroundColor Yellow

aop doctor

Write-Host ""
Write-Host "安装成功!" -ForegroundColor Green
Write-Host ""
Write-Host "快速开始:" -ForegroundColor Cyan
Write-Host "  aop doctor              # 检查环境"
Write-Host "  aop init my-project     # 创建项目"
Write-Host "  aop review -p 'Review for bugs'  # 代码审查"