#!/usr/bin/env bash
# 兼容入口：真正的实现在 skills/paper-review-kit/scripts/run_pipeline.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$SCRIPT_DIR/../skills/paper-review-kit/scripts/run_pipeline.sh"
