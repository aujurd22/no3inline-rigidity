#!/usr/bin/env python3
"""ls_trajectory.py -- 捕获一条典型下降轨迹 + 最终落点 vs 先验热图, 用于可视化找规律。"""
import json, os, random
from local_search_fix import (run_once, build_prior_table, prior_weight,
                              count_bad, brute_collinear)

def main():
    m = 7
    rng = random.Random(123)
    tbl, tot = build_prior_table(m)
    T0, T1 = max(2.0, float(m)), 0.2
    # 典型 SA + 高概率初始化
    rec = run_once(m, rng, "sa", "highprob", 0.0, 6000, T0, T1, False, tbl, tot)
    # 先验热图 & 落点统计
    prior = {}
    for x in range(m):
        for y in range(m):
            prior[f"{x},{y}"] = round(prior_weight(x, y, m), 4)
    out = {
        "m": m,
        "traj_bad": rec["traj"],
        "final_bad": rec["final_bad"],
        "solved": rec["solved"],
        "verified": rec["verified"],
        "best_cells": rec["best_cells"],
        "prior": prior,
    }
    os.makedirs("results", exist_ok=True)
    with open("results/local_search_trajectory.json", "w") as f:
        json.dump(out, f, indent=2)
    print("traj len", len(rec["traj"]), "final_bad", rec["final_bad"],
          "solved", rec["solved"], "verified", rec["verified"])

if __name__ == "__main__":
    main()
