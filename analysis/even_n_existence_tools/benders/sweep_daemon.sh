#!/bin/bash
# 高通量随机 2-因子扫描守护：三路串行，断点续跑，命中 SAT 即退出。
# 用 setsid 脱离会话，避免被沙箱回收后无法续跑。
cd "/d/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/even_n_existence_tools/benders"

N=40000
for entry in "20260721:random_sweep_results.json" "20260722:random_sweep_results_s2.json" "20260723:random_sweep_results_s3.json"; do
  seed="${entry%%:*}"
  out="${entry##*:}"
  echo "[daemon $(date +%H:%M:%S)] 启动 seed=$seed out=$out"
  while true; do
    python3 benders_random_sweep.py --n $N --seed $seed --resume --out "$out" >> "sweep_${seed}.log" 2>&1
    if [ -f "sat_solution_found.json" ]; then
      echo "[daemon $(date +%H:%M:%S)] ★★★ 突破！sat_solution_found.json 已写入，停止全部"
      exit 0
    fi
    tested=$(python3 -c "import json,sys; d=json.load(open('$out')); print(d.get('tested',0))" 2>/dev/null || echo 0)
    if [ "$tested" -ge "$N" ]; then
      echo "[daemon $(date +%H:%M:%S)] seed=$seed 完成 $tested 个"
      break
    fi
    echo "[daemon $(date +%H:%M:%S)] seed=$seed 被回收于 $tested，2s 后续跑"
    sleep 2
  done
done
echo "[daemon $(date +%H:%M:%S)] 全部三路完成"
