#!/bin/bash
# AOP 一键安装脚本
# 用法: ./install.sh [--dev]

set -e

echo "AOP - Agent Orchestration Platform 安装脚本"
echo "============================================"

# 检测操作系统
OS="\MSYS_NT-10.0-19045"
case "\" in
  Darwin*) OS="macos" ;;
  Linux*)  OS="linux" ;;
  MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
  *)       OS="unknown" ;;
esac

echo "检测到操作系统: \"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查命令是否存在
check_command() {
  if command -v \"\\" &> /dev/null; then
    echo -e \"\OK\ \ 已安装\"
    return 0
  else
    echo -e \"\X\ \ 未安装\"
    return 1
  fi
}

# 检查前置要求
echo ""
echo "检查前置要求..."

all_ok=true

if ! check_command python3; then
  all_ok=false
  echo "  请安装 Python 3.10+"
fi

if ! check_command pip; then
  all_ok=false
  echo "  请安装 pip"
fi

if [ \"\\" = false ]; then
  echo ""
  echo -e \"\缺少必要依赖，请先安装后再运行此脚本。\\"
  exit 1
fi

# 安装 AOP
echo ""
echo "安装 AOP..."

if [ \"\\" = "--dev" ]; then
  pip install -e ".[dev]"
else
  pip install -e .
fi

# 验证安装
echo ""
echo "验证安装..."

if aop doctor; then
  echo ""
  echo -e \"\安装成功!\\"
  echo ""
  echo "快速开始:"
  echo "  aop doctor              # 检查环境"
  echo "  aop init my-project     # 创建项目"
  echo "  aop review -p 'Review for bugs'  # 代码审查"
else
  echo ""
  echo -e \"\安装完成，但部分 provider 不可用。\\"
  echo "请按照 README.md 中的说明配置 provider。"
fi