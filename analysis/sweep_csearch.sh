#!/bin/bash
# sweep_csearch.sh -- 从小m到大m运行 csearch.exe, 记录时间/结果到 CSV (持久化).
# 用法: bash sweep_csearch.sh [start_m] [end_m]
# 资源随 m 缩放: moves ~ M0 * m^2 (每 move O(32m)), restarts 固定.
set -u
cd "$(dirname "$0")"
EXE=./csearch.exe
OUT=results/csearch_sweep.csv
LOGDIR=results/csearch_logs
mkdir -p "$LOGDIR"
START=${1:-8}
END=${2:-37}

# 表头 (若文件不存在)
if [ ! -f "$OUT" ]; then
  echo "m,n,found,time_sec,best_bad,verify_bad,restarts,moves_per_restart,seed,note" > "$OUT"
fi

for ((m=START; m<=END; m++)); do
  n=$((2*m))
  # 资源缩放: 每个 restart 的 moves 随 m 增大; 这里设 moves = 200000 * m (粗略)
  MOVES=$(( 200000 * m ))
  RESTARTS=40
  SEED=$m
  LOG="$LOGDIR/csearch_m${m}.log"
  echo ">>> m=$m (moves/restart=$MOVES, restarts=$RESTARTS) start $(date +%T)" >&2
  # 给每m一个墙钟上限, 防止无限 (timeout 秒)
  WALL=$(( 600 ))
  timeout "$WALL" "$EXE" "$m" "$RESTARTS" "$MOVES" "$SEED" > "$LOG" 2>&1
  rc=$?
  if [ $rc -eq 124 ]; then
    note="TIMEOUT"
  else
    note="ok"
  fi
  # 解析
  if grep -q "^FOUND" "$LOG"; then
    found=1
    time_sec=$(grep "^FOUND" "$LOG" | sed -E 's/.*time=([0-9.]+)s.*/\1/')
    verify_bad=$(grep "^verify_bad=" "$LOG" | sed -E 's/verify_bad=([0-9]+).*/\1/')
    best_bad=$verify_bad
    # 独立 Python 验证
    cells=$(grep "^cells:" "$LOG")
    echo "$cells" > "$LOGDIR/csearch_m${m}.cells"
    if [ -f verify_cells.py ]; then
      pyverify=$(python3 verify_cells.py "$LOGDIR/csearch_m${m}.cells" 2>&1 | tail -1)
      note="py:${pyverify}"
    fi
  else
    found=0
    time_sec=$(grep -oE "time=[0-9.]+s" "$LOG" | tail -1 | sed -E 's/time=([0-9.]+)s/\1/')
    best_bad=$(grep -oE "best_bad=[0-9]+" "$LOG" | sed -E 's/best_bad=([0-9]+)/\1/')
    verify_bad="NA"
  fi
  echo "$m,$n,$found,${time_sec:-NA},$best_bad,$verify_bad,$RESTARTS,$MOVES,$SEED,$note" >> "$OUT"
  echo "    -> m=$m found=$found time=${time_sec:-NA}s best_bad=${best_bad:-NA} $note" >&2
done
echo "DONE. CSV: $OUT" >&2
