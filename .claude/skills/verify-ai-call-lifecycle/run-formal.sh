#!/usr/bin/env bash
# 用 TLC 跑 AiCallLifecycle.tla。首次运行会下载 tla2tools.jar 到 .verify/tools/。
# 用法： .claude/skills/verify-ai-call-lifecycle/run-formal.sh
# 退出码：0 = 所有不变量成立；非 0 = TLC 报错或违反（会打印反例轨迹）。

set -euo pipefail

TLA_VERSION="${TLA_VERSION:-v1.7.4}"
ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
SKILL_DIR="$ROOT/.claude/skills/verify-ai-call-lifecycle"
WORK_DIR="$ROOT/.verify/formal"
TOOLS_DIR="$ROOT/.verify/tools"
JAR="$TOOLS_DIR/tla2tools.jar"

command -v java >/dev/null || { echo "FAIL: java not found in PATH" >&2; exit 2; }

mkdir -p "$WORK_DIR" "$TOOLS_DIR"

if [[ ! -f "$JAR" ]]; then
  echo "downloading tla2tools.jar $TLA_VERSION -> $JAR"
  curl -fsSL -o "$JAR.part" \
    "https://github.com/tlaplus/tlaplus/releases/download/$TLA_VERSION/tla2tools.jar"
  mv "$JAR.part" "$JAR"
fi

cp "$SKILL_DIR/formal/AiCallLifecycle.tla" "$WORK_DIR/"
cp "$SKILL_DIR/formal/AiCallLifecycle.cfg" "$WORK_DIR/"

cd "$WORK_DIR"
# -deadlock：终态没有后继是模型的正常收尾，不是错误。
exec java -cp "$JAR" tlc2.TLC \
  -workers 1 -deadlock -metadir "$WORK_DIR/states" \
  -config AiCallLifecycle.cfg AiCallLifecycle.tla
