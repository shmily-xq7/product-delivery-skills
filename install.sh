#!/usr/bin/env bash
# 默认安装到 Codex；--app workbuddy 或 --target PATH 可指定目标。
# 保留 WORKBUDDY_SKILLS_DIR 环境变量兼容性。Python 3.9+，仅标准库。
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
exec python3 "${SRC}/scripts/install.py" "$@"
