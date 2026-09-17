#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盆地间「热力学 bulk」2-边开关游走探针（2026-07-21）。

动机（补强穷尽性 [CONJECTURE]）：
  - 随机均匀采样（results_round1）：查「远离盆地的远区」→ 550 全 UNSAT。
  - 一步邻域探针（switch_walk）：查「近盆地低缺陷区」→ 120 全 UNSAT。
  - 二者之间仍有一大块「盆地可达的中等缺陷大空间」未被覆盖。
  本脚本用 Metropolis 2-边开关游走从各盆地出发，带升温接受劣态，
  在坏三元组能量面上做随机游动，对途经的（去重）状态送子问题判定，
  检验可达大空间是否也存在 SAT 解。

所有结论标 [COMPUTATIONAL CERTIFICATE]，m=37 存在性仍 OPEN。
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

from scan_new_basins import compute_defects  # noqa: E402
from benders_subproblem import solve_subproblem  # noqa: E402

EDGES_JSON = HERE.parent / "v20_basin_archive.json"


def load_basin_edges():
    arch = json.loads(EDGES_JSON.read_text())
    return [(b["id"], [tuple(e) for e in b["edges"]]) for b in arch["archive"]]


def to_set(edges):
    return frozenset((min(u, v), max(u, v)) for u, v in edges)


def random_switch(eset, rng, attempts=40):
    """在 2-正则图上做一次随机 2-边开关，返回新 frozenset 或 None。"""
    el = list(eset)
    n = len(el)
    for _ in range(attempts):
        i, j = rng.sample(range(n), 2)
        a, b = el[i]
        c, d = el[j]
        if len({a, b, c, d}) != 4:
            continue
        # 两种重组
        if rng.random() < 0.5:
            n1, n2 = (a, c), (b, d)
        else:
            n1, n2 = (a, d), (b, c)
        n1 = (min(n1), max(n1))
        n2 = (min(n2), max(n2))
        if n1 in eset or n2 in eset:
            continue
        if n1[0] == n1[1] or n2[0] == n2[1]:
            continue
        new = set(eset)
        new.discard((a, b)); new.discard((c, d))
        new.add(n1); new.add(n2)
        # 2-正则校验
        deg = {}
        for u, v in new:
            deg[u] = deg.get(u, 0) + 1
            deg[v] = deg.get(v, 0) + 1
        if len(new) != 37 or any(d2 != 2 for d2 in deg.values()):
            continue
        return frozenset(new)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=400, help="每盆地游走步数")
    ap.add_argument("--judge-every", type=int, default=2, help="每 N 步送子问题一次")
    ap.add_argument("--T0", type=float, default=40.0, help="初始温度（坏三元组单位）")
    ap.add_argument("--T1", type=float, default=5.0, help="末温度")
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--max-judge", type=int, default=120, help="每盆地最多送判次数")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    basins = load_basin_edges()
    print(f"[Bulk Walk] 盆地={len(basins)} steps={args.steps} judge_every={args.judge_every} "
          f"T0={args.T0} T1={args.T1} max_judge={args.max_judge} seed={args.seed}")

    t0 = time.time()
    all_verdicts = []
    walk_summary = {}
    breakthrough = False

    for bid, edges in basins:
        cur = to_set(edges)
        cur_bad, cur_orb = compute_defects(sorted(cur))
        best_bad = cur_bad
        visited = set([cur])
        judged_keys = set()
        local_verdicts = []
        judge_count = 0

        for step in range(1, args.steps + 1):
            T = args.T0 + (args.T1 - args.T0) * (step - 1) / max(1, args.steps - 1)
            nxt = random_switch(cur, rng)
            if nxt is None:
                continue
            nb_bad, nb_orb = compute_defects(sorted(nxt))
            dE = nb_bad - cur_bad
            if dE <= 0 or rng.random() < math.exp(-dE / max(T, 1e-6)):
                cur, cur_bad, cur_orb = nxt, nb_bad, nb_orb
                visited.add(cur)
                if nb_bad < best_bad:
                    best_bad = nb_bad

            if step % args.judge_every == 0 and judge_count < args.max_judge:
                if cur not in judged_keys:
                    judged_keys.add(cur)
                    r = solve_subproblem(sorted(cur))
                    v = r["verdict"]
                    local_verdicts.append({
                        "from_basin": bid, "step": step,
                        "bad_triples": cur_bad, "defect_orbits": cur_orb,
                        "verdict": v, "n_clauses": r.get("n_clauses"),
                    })
                    judge_count += 1
                    if v == "sat_solution":
                        print(f"  ★★★ 突破！盆地 {bid} 游走发现 rot4-NTIL 解")
                        breakthrough = True
                        break

        walk_summary[bid] = {
            "start_bad": compute_defects(edges)[0],
            "steps": args.steps,
            "reachable_states": len(visited),
            "judged": len(local_verdicts),
            "best_bad_reached": best_bad,
        }
        print(f"  盆地 {bid}: 可达状态={len(visited)} 送判={len(local_verdicts)} "
              f"最低坏三元组={best_bad}")
        all_verdicts.extend(local_verdicts)
        if breakthrough:
            break

    out = {
        "params": vars(args),
        "elapsed_seconds": time.time() - t0,
        "walk_summary": walk_summary,
        "subproblem_verdicts": all_verdicts,
        "breakthrough": breakthrough,
    }
    (HERE / "bulk_walk_results.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n写入 bulk_walk_results.json  耗时 {out['elapsed_seconds']:.0f}s")
    vc = {}
    for vd in all_verdicts:
        vc[vd["verdict"]] = vc.get(vd["verdict"], 0) + 1
    print(f"送判总计 {len(all_verdicts)}：{vc}")
    print("突破" if breakthrough else "未找到解：盆地可达 bulk 空间全 UNSAT（穷尽性补强）")


if __name__ == "__main__":
    main()
