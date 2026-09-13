#!/usr/bin/env bash
# 通用 Agent Skills 安装入口；支持多客户端、多目标与逐技能 ZIP 导出。
# 执行 bash install.sh --list-apps 查看客户端和实际目标。Python 3.9+。
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
exec python3 "${SRC}/scripts/install.py" "$@"
