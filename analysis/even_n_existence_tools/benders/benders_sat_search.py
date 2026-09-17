#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""m=37 rot4-NTIL 解的直击搜索（2026-07-21）。

目标：找到一幅 **SAT** 的 2-因子（即存在 rot4 取向使 296 点无三点共线）→
真正的 rot4-NTIL 构造 = 重磅突破，直接否定"m=37 不存在"。

策略：从随机 2-因子出发做 Metropolis 退火，**最小化缺陷轨道数**（defect_orbits，
解的必要性代理：盆地已知在 59–84，随机 min 84，故解若存在必在低缺陷区）。
每当巡游到一个**新的**低缺陷状态（defect_orbits ≤ 阈值），送子问题判定；
一旦 SAT（solve_subproblem 内部已用完整几何 oracle 复核）即记录为突破并停止。

所有判定用 sound 松弛 + 几何 oracle：SAT 即真解；UNSAT 即真障碍。
绝不断言"不存在"，只积累证据。m=37 OPEN，直到找到解或证毕。
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from scan_new_basins import compute_defects, random_2factor  # noqa: E402
from benders_subproblem import solve_subproblem  # noqa: E402
from benders_bulk_walk import random_switch  # noqa: E402

EDGES_JSON = HERE.parent / "v20_basin_archive.json"


def to_set(edges):
    return frozenset((min(u, v), max(u, v)) for u, v in edges)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restarts", type=int, default=30, help="随机起手次数")
    ap.add_argument("--steps", type=int, default=1500, help="每次起手退火步数")
    ap.add_argument("--T0", type=float, default=150.0)
    ap.add_argument("--T1", type=float, default=1.0)
    ap.add_argument("--test-thr", type=int, default=80,
                    help="defect_orbits ≤ 此值的新状态才送子问题")
    ap.add_argument("--max-tests", type=int, default=3000, help="全局最多送判次数")
    ap.add_argument("--seed", type=int, default=20260721)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    print(f"[SAT 搜索] restarts={args.restarts} steps={args.steps} T0={args.T0} T1={args.T1} "
          f"test_thr={args.test_thr} max_tests={args.max_tests} seed={args.seed}")

    t0 = time.time()
    tested = set()
    tests = 0
    best_orb = 10**9
    best_state = None
    breakthroughs = []
    restart_log = []

    for restart_idx in range(args.restarts):
        edges = random_2factor(rng)
        cur = to_set(edges)
        cur_bad, cur_orb = compute_defects(edges)
        r_best_orb = cur_orb
        for step in range(1, args.steps + 1):
            T = args.T0 + (args.T1 - args.T0) * (step - 1) / max(1, args.steps - 1)
            nxt = random_switch(cur, rng)
            if nxt is None:
                continue
            nb_bad, nb_orb = compute_defects(sorted(nxt))
            if nb_bad is None:
                continue
            dE = nb_orb - cur_orb
            if dE <= 0 or rng.random() < math.exp(-dE / max(T, 1e-6)):
                cur, cur_bad, cur_orb = nxt, nb_bad, nb_orb
                if nb_orb < r_best_orb:
                    r_best_orb = nb_orb
                if nb_orb < best_orb:
                    best_orb, best_state = nb_orb, cur
            # 送判：低缺陷 + 新状态
            if cur_orb <= args.test_thr and cur not in tested and tests < args.max_tests:
                tested.add(cur)
                res = solve_subproblem(sorted(cur))
                v = res["verdict"]
                tests += 1
                if v == "sat_solution":
                    print(f"\n  ★★★ 突破！restart {restart_idx} step {step} 发现 rot4-NTIL 解")
                    sol = {"restart": restart_idx, "step": step, "edges": sorted(cur),
                           "defect_orbits": cur_orb, "n_clauses": res.get("n_clauses")}
                    breakthroughs.append(sol)
                    (HERE / "sat_solution_found.json").write_text(
                        json.dumps(sol, ensure_ascii=False, indent=2), encoding="utf-8")
                    print("写入 sat_solution_found.json")
                    break
        restart_log.append({"restart": restart_idx, "best_orb": r_best_orb})
        print(f"  restart {restart_idx}: 本起手最低 defect_orbits={r_best_orb}  累计送判={tests}")
        if breakthroughs:
            break

    out = {
        "params": vars(args),
        "elapsed_seconds": time.time() - t0,
        "tests": tests,
        "best_orb_reached": best_orb,
        "best_state_edges": sorted(best_state) if best_state else None,
        "breakthrough": bool(breakthroughs),
        "n_breakthroughs": len(breakthroughs),
        "restart_log": restart_log,
    }
    (HERE / "sat_search_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n写入 sat_search_results.json  耗时 {out['elapsed_seconds']:.0f}s  送判={tests}")
    if breakthroughs:
        print(f"★★★ 找到 {len(breakthroughs)} 个 rot4-NTIL 解（重磅突破）")
    else:
        print(f"未找到解：{tests} 个低缺陷 2-因子全 UNSAT；全局最低 defect_orbits 达 {best_orb}")


if __name__ == "__main__":
    main()
