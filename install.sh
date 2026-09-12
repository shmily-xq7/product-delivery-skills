#!/usr/bin/env bash
# 一键安装：把本仓库的 11 个 product-* skill 复制到 AI 助手的用户级技能目录
# 用法：
#   bash install.sh                     # 安装到默认目录 ~/.workbuddy/skills/
#   WORKBUDDY_SKILLS_DIR=~/xx bash install.sh   # 或自定义目标目录
set -euo pipefail

TARGET="${WORKBUDDY_SKILLS_DIR:-$HOME/.workbuddy/skills}"
SRC="$(cd "$(dirname "$0")" && pwd)"

# ── 0. 前置检查 ─────────────────────────────────────────────
if ! ls "$SRC"/product-*/SKILL.md >/dev/null 2>&1; then
  echo "❌ 未在 $(dirname "$0") 找到任何 product-*/SKILL.md —— 请确认在仓库根目录运行"
  exit 1
fi

echo "安装目标：$TARGET"
mkdir -p "$TARGET"

# ── 1. 逐个安装（旧版自动备份） ──────────────────────────────
COUNT=0
for d in "$SRC"/product-*/; do
  name="$(basename "$d")"
  if [ -d "$TARGET/$name" ]; then
    TS="$(date +%Y%m%d-%H%M%S)"
    mv "$TARGET/$name" "$TARGET/${name}.bak-$TS"
    echo "  ↺ 已备份旧版 → ${name}.bak-$TS"
  fi
  cp -R "$d" "$TARGET/$name"
  COUNT=$((COUNT + 1))
  echo "  ✓ $name"
done

# ── 2. 校验 ─────────────────────────────────────────────────
OK=0
for d in "$TARGET"/product-*/; do
  [ -f "$d/SKILL.md" ] && OK=$((OK + 1))
done

echo ""
echo "✅ 已安装 $COUNT 个 skill 到 $TARGET（SKILL.md 校验通过 $OK 个）"
echo "   重启 WorkBuddy（或新开会话）后即可用触发词调用，例如："
echo "   「走完整产品交付流程」「写产品设计文档」「需求访谈」"
echo ""
echo "   可选：product-doc-convert 的脚本需要 python-docx / openpyxl："
echo "         python3 -m venv .venv && .venv/bin/pip install python-docx openpyxl"
