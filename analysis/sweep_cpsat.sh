#!/bin/bash
# sweep_cpsat.sh -- 用 R9b 快速 CP-SAT 模型对递增 m 计时, 记录状态/时间到 CSV (持久化).
# 这是"旧方法"(CP-SAT) + "所有当前理论"(R9b 2-因子) 的正确基线, 用于"从小m看时间".
set -u
cd "$(dirname "$0")"
PY=/c/Users/djr82/.workbuddy/binaries/python/envs/default/Scripts/python.exe
EXE=solve_m37_r9b.py
OUT=results/cpsat_sweep.csv
LOGDIR=results/cpsat_logs
mkdir -p "$LOGDIR"
START=${1:-14}
END=${2:-36}

if [ ! -f "$OUT" ]; then
  echo "m,n,status,found,verify,solve_time,build_time,line_cons,workers,timelimit,note" > "$OUT"
fi

for ((m=START; m<=END; m++)); do
  n=$((2*m))
  # 随 m 增大放宽 cap
  if   [ $m -le 20 ]; then CAP=120
  elif [ $m -le 26 ]; then CAP=300
  elif [ $m -le 32 ]; then CAP=600
  else                      CAP=1200; fi
  W=8
  LOG="$LOGDIR/cpsat_m${m}.log"
  echo ">>> m=$m cap=${CAP}s start $(date +%T)" >&2
  timeout $((CAP+60)) "$PY" "$EXE" --m "$m" --timelimit "$CAP" --workers "$W" > "$LOG" 2>&1
  rc=$?
  if [ $rc -eq 124 ]; then note="WALL_TIMEOUT"; else note="ok"; fi
  status=$(grep -oE "status=[A-Z]+" "$LOG" | tail -1 | sed -E 's/status=//')
  found=$(grep -oE "found=[0-9]+" "$LOG" | tail -1 | sed -E 's/found=//')
  verify=$(grep -oE "no-3-collinear=(True|False)" "$LOG" | tail -1 | sed -E 's/no-3-collinear=//')
  solve_time=$(grep -oE "solve_time=[0-9.]+s" "$LOG" | tail -1 | sed -E 's/solve_time=([0-9.]+)s/\1/')
  build_time=$(grep -oE "build=[0-9.]+s" "$LOG" | tail -1 | sed -E 's/build=([0-9.]+)s/\1/')
  line_cons=$(grep -oE "line_cons=[0-9]+" "$LOG" | tail -1 | sed -E 's/line_cons=//')
  echo "$m,$n,$status,$found,$verify,${solve_time:-NA},${build_time:-NA},${line_cons:-NA},$W,$CAP,$note" >> "$OUT"
  echo "    -> m=$m status=$status found=$found verify=$verify solve=${solve_time:-NA}s $note" >&2
done
echo "DONE. CSV: $OUT" >&2
