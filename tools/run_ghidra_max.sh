#!/usr/bin/env bash
# 用"榨干预算"的设置在三个嵌入原生库上重跑 Ghidra：
#   - 全新项目 + 放宽分析阶段超时（-analysisTimeoutPerFile，默认 300s）
#   - 每函数 1200s 反编译预算
#   - maxJumptableEntries 1024 → 16384，maxInstructions 20M，maxPayload 512MB
#
# 用法：bash tools/run_ghidra_max.sh [ghidra_install_root]
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

GH_ROOT="${1:-/opt/homebrew/Cellar/ghidra/12.1.4/libexec}"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home}"
GH="$GH_ROOT/support/analyzeHeadless"
PROJ="ghidra-proj-max"
OUT="out"
mkdir -p "$OUT" "$PROJ"

run_one () {  # proj_name  bin  outname
  local proj="$1" bin="$2" out="$3"
  echo "=== [$(date +%H:%M:%S)] import $bin (long analysis) ==="
  "$GH" "$PROJ" "$proj" -import "work/embedded/$bin" \
      -analysisTimeoutPerFile 7200 \
      -postScript DumpDecompMax.java "-" "$OUT/$out" 1200 20 \
      -scriptPath ghidra-scripts 2>&1 | grep -E "DumpDecompMax:|ERROR|Analysis succeeded" | tail -3
}

run_one cua   macho1.bin max-cua.txt
run_one input macho5.bin max-input.txt
run_one audio macho6.bin max-audio.txt

echo "=== [$(date +%H:%M:%S)] done ==="
for f in max-cua max-input max-audio; do
  [ -f "$OUT/$f.txt" ] && echo "$f: $(grep -c '^// ==== ' "$OUT/$f.txt") functions, $(du -h "$OUT/$f.txt" | cut -f1)"
done
