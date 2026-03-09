#!/bin/bash
# AOP 敏捷教练 Skill 安装脚本 (macOS/Linux)
# 用法: ./install.sh

set -e

echo "AOP 敏捷教练 Skill 安装脚本"
echo "============================"

# 默认 OpenClaw skills 目录
OPENCLAW_SKILLS="${OPENCLAW_SKILLS:-$HOME/.openclaw/skills}"

# 源目录（脚本所在目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 目标目录
TARGET_DIR="$OPENCLAW_SKILLS/aop-coach"

echo ""
echo "安装 AOP 敏捷教练 Skill..."
echo "  源目录: $SCRIPT_DIR"
echo "  目标目录: $TARGET_DIR"

# 创建目录
mkdir -p "$TARGET_DIR/references"

# 复制文件
cp "$SCRIPT_DIR/SKILL.md" "$TARGET_DIR/"
cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/"
cp "$SCRIPT_DIR/references/TEAM.md" "$TARGET_DIR/references/"
cp "$SCRIPT_DIR/references/WORKFLOW.md" "$TARGET_DIR/references/"

# 验证
if [ -f "$TARGET_DIR/SKILL.md" ]; then
    echo ""
    echo "✅ AOP 敏捷教练 Skill 安装成功!"
    echo ""
    echo "下一步:"
    echo "  1. 在 OpenClaw 中输入: -aop status"
    echo "  2. 或查看详细文档: $TARGET_DIR/README.md"
else
    echo "❌ 安装失败"
    exit 1
fi