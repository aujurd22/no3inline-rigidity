#!/bin/bash
# 并行扫描管理器：10 路 worker（12 核机器），每路独立种子+断点续跑。
# 用 PID 文件检测 worker 存活（避免 pgrep 不可用的环境）。
# 后台被回收后重启动本脚本即从各路 JSON 断点继续；命中 SAT 写 sat_solution_found.json 并退出。
cd "/d/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/even_n_existence_tools/benders" || exit 1

TARGET=40000
SEEDS=(20260721 20260722 20260723 20260724 20260725 20260726 20260727 20260728 20260729 20260730)

get_tested() {
  python3 -c "import json;print(json.load(open('random_sweep_p$1.json')).get('tested',0))" 2>/dev/null || echo 0
}

alive() {
  local pidf="random_sweep_p\$1.pid"
  [ -f "$pidf" ] || return 1
  local pid
  pid=$(cat "$pidf" 2>/dev/null)
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

echo "[parallel-manager $(date +%H:%M:%S)] 启动 TARGET=$TARGET workers=${#SEEDS[@]}"

while true; do
  all_done=1
  for s in "${SEEDS[@]}"; do
    if alive "$s"; then
      continue
    fi
    tested=$(get_tested "$s")
    if [ "$tested" -lt "$TARGET" ]; then
      all_done=0
      if [ -f "sat_solution_found.json" ]; then
        echo "[parallel-manager $(date +%H:%M:%S)] 检测到突破，终止"; kill $(cat random_sweep_p*.pid 2>/dev/null) 2>/dev/null
        exit 0
      fi
      nohup python3 benders_random_sweep.py --n "$TARGET" --seed "$s" --save-every 500 --out "random_sweep_p$s.json" >"sweep_p$s.log" 2>&1 &
      echo $! > "random_sweep_p$s.pid"
      echo "[parallel-manager $(date +%H:%M:%S)] 启动 seed=$s (已测 $tested)"
    fi
  done
  if [ "$all_done" = "1" ]; then
    echo "[parallel-manager $(date +%H:%M:%S)] 全部 ${#SEEDS[@]} 路达 TARGET=$TARGET，完成"
    exit 0
  fi
  sleep 20
done
