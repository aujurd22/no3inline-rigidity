#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Benders 主/子问题迭代循环（rot4 m=37 全局 2-因子搜索）。

流程：
  主问题生成候选 2-因子（远离六 V20 盆地）→ 子问题判定取向 SAT：
    - invalid     : 非合法 rot4 2-因子 → 割除（加入割集）
    - unsat       : 3-CNF UNSAT ⇒ 该 2-因子无 rot4-NTIL 补全（sound 排除）→ 割除
    - sat_blocked : 3-CNF SAT 但几何 oracle 仍坏（2+1 型共线）→ 记录，不 sound 排除
    - sat_solution: ★ 发现 rot4-NTIL 解（突破）→ 停止
  割集回注主问题，避免重复判定。

所有结论标 [COMPUTATIONAL CERTIFICATE]，不当定理。m=37 存在性仍 OPEN。
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from benders_master import (load_basins, generate_candidates, candidate_edge_set,
                             generate_switch_neighbors)  # noqa: E402
from benders_subproblem import solve_subproblem  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60, help="目标有效候选数")
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--min-distance", type=int, default=10,
                    help="候选到六盆地的最小边集对称差（越大越远离已知盆地）")
    ap.add_argument("--source", choices=["random", "switch"], default="random",
                    help="候选源：random=纯随机 2-因子；"
                         "switch=六盆地一步 2-边开关邻域（近盆地低缺陷区）")
    ap.add_argument("--margin", type=int, default=25,
                    help="switch 源：邻域缺陷上限 = 起点bad+margin")
    ap.add_argument("--out", default=str(HERE / "results_round.json"))
    args = ap.parse_args()

    basins = load_basins()
    basin_keys = {es for _bid, es in basins}
    cut_set = set(basin_keys)  # 六盆地已知 UNSAT，先入割集

    rng = random.Random(args.seed)
    results = []
    t0 = time.time()
    solved = 0
    breakthrough = None

    print(f"[Benders] 目标有效候选={args.n}  候选源={args.source}  "
          f"min_distance={args.min_distance}  seed={args.seed}")

    while solved < args.n:
        if args.source == "switch":
            # 结构化候选源：重枚举盆地邻域（每轮重算以纳入新割集）
            batch = generate_switch_neighbors(
                basins, cut_set, margin=args.margin, max_per_basin=200)
            att = inv = 0
        else:
            # 主问题：生成一批候选（含无效/割集/近距离过滤）
            batch, att, inv = generate_candidates(
                50, rng, basins, cut_set, min_distance=args.min_distance)
        if not batch:
            print("  候选源枯竭（达到 max_invalid_skip），停止。")
            break
        for edges, dist in batch:
            key = candidate_edge_set(edges)
            if key in cut_set:
                continue
            r = solve_subproblem(edges)
            v = r["verdict"]
            rec = {"distance_to_basin": dist, "verdict": v,
                   "edges": edges, "info": {k: r[k] for k in r if k != "edges"}}
            if v == "sat_solution":
                rec["model"] = r.get("model")
                breakthrough = rec
            results.append(rec)
            if v in ("invalid", "unsat"):
                cut_set.add(key)        # sound 排除 → 割除
            solved += 1
            if solved % 10 == 0:
                print(f"  [{solved}/{args.n}] 耗时 {time.time()-t0:.0f}s  "
                      f"割集大小={len(cut_set)}  最近判定={v}")
            if breakthrough is not None:
                break
        if breakthrough is not None:
            break

    verdict_dist = Counter(r["verdict"] for r in results)
    summary = {
        "seed": args.seed,
        "min_distance": args.min_distance,
        "n_results": len(results),
        "verdict_distribution": dict(verdict_dist),
        "elapsed_seconds": time.time() - t0,
        "cut_set_size": len(cut_set),
        "breakthrough": breakthrough is not None,
    }
    out = {"summary": summary, "results": results,
           "breakthrough_record": breakthrough}
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    print(f"\n===== Benders 第一轮汇总 =====")
    print(f"有效判定={len(results)}  判定分布={dict(verdict_dist)}")
    print(f"割集大小={len(cut_set)}  耗时={summary['elapsed_seconds']:.0f}s")
    if breakthrough:
        print(f"★★★ 突破：发现 rot4-NTIL 解！edges 见 results_round.json ★★★")
    else:
        print("本轮未找到解（符合 m=37 的难度预期）。已 sound 排除 "
              f"{verdict_dist.get('unsat',0)} 幅 UNSAT 2-因子 + "
              f"{verdict_dist.get('invalid',0)} 幅非法 2-因子。")
    print(f"写入 {args.out}")


if __name__ == "__main__":
    main()
