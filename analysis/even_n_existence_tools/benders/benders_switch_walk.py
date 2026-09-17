#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盆地一步 2-边开关邻域穷尽性探针（2026-07-21）。

动机（Benders 框架笔记 §5 下一步 #2）：六 V20 盆地是 2-因子空间极低缺陷区的谷底
（5 轨道 vs 随机 min 84 轨道）。若盆地本身 UNSAT（已证），其**低缺陷邻域**是否也全
UNSAT，是 m=37 障碍"局部穷尽性"的关键测试——若存在某低缺陷邻域 2-因子 SAT，可能
是解的藏身处。

方法：
  1. 对每盆地枚举所有合法「一步 2-边开关」邻域（2-正则性保持，禁重边/自环/2-圈）。
  2. 用 compute_defects 的 bad_triples 作廉价代理，对邻域按缺陷排序。
  3. 取缺陷 ≤ 起点+margin 的邻域候选（"近盆地低缺陷区"）送 solve_subproblem
     （三互异-cell 3-CNF 可靠松弛）判定，看是否出现 SAT（突破）或全 UNSAT。
  4. 若某邻域 SAT，进一步用完整几何 oracle 确认（solve_subproblem 内部已做）。

所有结论标 [COMPUTATIONAL CERTIFICATE]，不当定理。m=37 存在性仍 OPEN。
"""
from __future__ import annotations

import argparse
import json
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


def enumerate_neighbors(edges):
    """枚举所有合法一步 2-边开关邻域，返回去重后的边集列表。"""
    eset = set((min(u, v), max(u, v)) for u, v in edges)
    verts = sorted({u for e in edges for u in e})
    out = []
    seen = set()
    edges_list = sorted(eset)
    n = len(edges_list)
    for i in range(n):
        a, b = edges_list[i]
        for j in range(i + 1, n):
            c, d = edges_list[j]
            if len({a, b, c, d}) != 4:
                continue
            # 候选新边
            n1 = (min(a, c), max(a, c))
            n2 = (min(b, d), max(b, d))
            if n1 in eset or n2 in eset:
                continue
            if a == c or b == d:
                continue
            new_set = set(eset)
            new_set.discard((a, b))
            new_set.discard((c, d))
            new_set.add(n1)
            new_set.add(n2)
            # 校验 2-正则、无 2-圈
            deg = {}
            ok = True
            for u, v in new_set:
                deg[u] = deg.get(u, 0) + 1
                deg[v] = deg.get(v, 0) + 1
            if len(new_set) != 37 or any(d2 != 2 for d2 in deg.values()):
                continue
            key = frozenset(new_set)
            if key in seen:
                continue
            seen.add(key)
            out.append(sorted(new_set))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--margin", type=int, default=20,
                    help="邻域缺陷上限 = 起点bad_triples + margin")
    ap.add_argument("--topk", type=int, default=20,
                    help="每盆地送子问题的最低缺陷邻域数")
    ap.add_argument("--no-subproblem", action="store_true",
                    help="只枚举+统计，不送子问题（快速探针）")
    args = ap.parse_args()

    basins = load_basin_edges()
    print(f"[邻域探针] 盆地数={len(basins)}  margin={args.margin}  "
          f"topk={args.topk}  subproblem={'关' if args.no_subproblem else '开'}")

    t0 = time.time()
    walk_summary = {}
    low_candidates = []   # (bad, orb, bid, edges)
    for bid, edges in basins:
        start_bad, start_orb = compute_defects(edges)
        nbrs = enumerate_neighbors(edges)
        scored = []
        for ne in nbrs:
            bad, orb = compute_defects(ne)
            if bad is None:
                continue
            scored.append((bad, orb, ne))
        scored.sort(key=lambda t: (t[0], t[1]))
        n_within = [s for s in scored if s[0] <= start_bad + args.margin]
        walk_summary[bid] = {
            "start_bad": start_bad, "start_orb": start_orb,
            "n_neighbors": len(nbrs),
            "n_within_margin": len(n_within),
            "min_neighbor_bad": scored[0][0] if scored else None,
            "min_neighbor_orb": scored[0][1] if scored else None,
        }
        print(f"  盆地 {bid}: 起点缺陷({start_bad},{start_orb})  邻域数={len(nbrs)}  "
              f"≤起点+{args.margin} 的邻域={len(n_within)}  "
              f"邻域最低缺陷({scored[0][0]},{scored[0][1]})")
        for s in n_within[:args.topk]:
            low_candidates.append((s[0], s[1], bid, s[2]))

    if args.no_subproblem:
        out = {"mode": "no-subproblem", "elapsed_seconds": time.time() - t0,
               "walk_summary": walk_summary}
        (HERE / "switch_walk_results.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n写入 switch_walk_results.json [快速探针] 耗时 {out['elapsed_seconds']:.1f}s")
        return

    print(f"\n=== 子问题判定 {len(low_candidates)} 个近盆地低缺陷邻域 ===")
    verdicts = []
    for bad, orb, bid, edges in sorted(low_candidates, key=lambda t: (t[0], t[1])):
        r = solve_subproblem(edges)
        v = r["verdict"]
        verdicts.append({"from_basin": bid, "bad_triples": bad,
                         "defect_orbits": orb, "verdict": v,
                         "n_clauses": r.get("n_clauses")})
        print(f"  来自 {bid} 缺陷({bad},{orb}): {v}  clauses={r.get('n_clauses')}")
        if v == "sat_solution":
            print(f"  ★★★ 突破！发现 rot4-NTIL 解，来自盆地 {bid} 邻域")
            break

    out = {
        "params": {"margin": args.margin, "topk": args.topk},
        "elapsed_seconds": time.time() - t0,
        "walk_summary": walk_summary,
        "subproblem_verdicts": verdicts,
        "breakthrough": any(vd["verdict"] == "sat_solution" for vd in verdicts),
    }
    (HERE / "switch_walk_results.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n写入 switch_walk_results.json  耗时 {out['elapsed_seconds']:.0f}s")
    print("突破" if out["breakthrough"] else "未找到解：近盆地低缺陷邻域全 UNSAT（局部穷尽性证据）")


if __name__ == "__main__":
    main()
