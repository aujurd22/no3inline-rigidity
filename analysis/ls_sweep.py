#!/usr/bin/env python3
"""
ls_sweep.py -- 配置矩阵扫描，系统性地找"带理论先验的局部搜索"在小 m 上的规律。

比较维度:
  - 模式: greedy(纯贪心, 只接受下降) vs sa(模拟退火, 偶走上坡逃局部极小)
  - 初始化: random vs highprob(高概率区偏置) vs sidon(贪心满足 Sidon 差异集)
  - 锚点比例: 0.0 vs 0.4 (固定一部分点不移动)
  - Sidon 过滤: 关闭 vs 开启(每步保证 FDR/Part-I 差异集)
对每个 (m, config) 跑 R 次重启, 统计求解率 / 平均 final_bad / 平均收敛迭代数。
"""
import json, os, random, time, argparse
from local_search_fix import (run_once, build_prior_table, count_bad,
                              brute_collinear)

CONFIGS = [
    ("C1_greedy_random",      dict(mode="greedy", init="random",   anchors=0.0, sidon_filter=False)),
    ("C2_sa_random",          dict(mode="sa",     init="random",   anchors=0.0, sidon_filter=False)),
    ("C3_sa_highprob",        dict(mode="sa",     init="highprob", anchors=0.0, sidon_filter=False)),
    ("C4_sa_highprob_anch40", dict(mode="sa",     init="highprob", anchors=0.4, sidon_filter=False)),
    ("C5_sa_sidonFilter",     dict(mode="sa",     init="sidon",    anchors=0.0, sidon_filter=True)),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", default="4,5,6,7,8")
    ap.add_argument("--restarts", type=int, default=8)
    ap.add_argument("--iters", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="results/local_search_sweep.json")
    a = ap.parse_args()
    ms = [int(x) for x in a.ms.split(",")]
    rng = random.Random(a.seed)

    out = {"meta": {"ms": ms, "restarts": a.restarts, "iters": a.iters,
                    "seed": a.seed}, "data": {}}
    t0 = time.time()
    for m in ms:
        tbl, tot = build_prior_table(m)
        T0 = max(2.0, float(m)); T1 = 0.2
        out["data"][m] = {}
        for name, cfg in CONFIGS:
            solved = 0; verified = 0; bads = []; conv_iters = []
            for r in range(a.restarts):
                rec = run_once(m, rng, cfg["mode"], cfg["init"], cfg["anchors"],
                               a.iters, T0, T1, cfg["sidon_filter"], tbl, tot)
                if rec["solved"]:
                    solved += 1
                    if rec["verified"]:
                        verified += 1
                    # 收敛迭代: 找到第一个 bad==0 的轨迹点 *200 (记录间隔)
                    try:
                        idx = next(i for i, v in enumerate(rec["traj"]) if v == 0)
                        conv_iters.append(idx * 200)
                    except StopIteration:
                        conv_iters.append(a.iters)
                bads.append(rec["final_bad"])
            avg_bad = sum(bads) / len(bads)
            out["data"][m][name] = {
                "solved": solved, "verified": verified,
                "solve_rate": solved / a.restarts,
                "avg_final_bad": avg_bad,
                "min_final_bad": min(bads),
                "avg_conv_iters": (sum(conv_iters) / len(conv_iters)) if conv_iters else None,
            }
            print(f"m={m} {name:22s} solved={solved}/{a.restarts} "
                  f"verified={verified} avgBad={avg_bad:.1f} "
                  f"minBad={min(bads)}", flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"# DONE {time.time()-t0:.1f}s saved -> {a.out}")

if __name__ == "__main__":
    main()
