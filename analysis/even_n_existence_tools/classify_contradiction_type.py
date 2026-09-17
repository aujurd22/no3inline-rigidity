#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""矛盾类型分类（修正版，2026-07-21 复核）。

旧版把「极小矛盾环恰含 2 变量」一律判为陷阱，忽略了**无一元约束的纯二元 2-变量矛盾**
（某变量对 4 种朝向组合全被禁），这是真实数学错误（见 trap_rigorous_theory.md §4 定理 B 修正版）。

本版构建两套蕴含图：
  - 全图：含一元强制 + 一元矛盾 + 二元禁配
  - 纯二元图：仅含二元禁配（剔除一切一元）
并据下式正确分类：
  - trap       : 全图 UNSAT 且 纯二元图 NOT UNSAT（矛盾依赖一元强制）
  - pure_binary: 纯二元图 UNSAT（矛盾不依赖任何一元）
  - sat        : 两者皆 SAT（靠三元耦合，需回退几何 oracle）

所有结论标 [COMPUTATIONAL CERTIFICATE]，不当定理。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from scc_prescreen import (
    build_correct_fs, extract_unary_binary, build_implication_graph,
    tarjan_scc, bfs_shortest, lit_id, exact_min_contradiction_vars,
)

HERE = Path(__file__).resolve().parent


def shortest_contradiction(adj, n_vars):
    """返回 (num_implication_edges, distinct_vars) 或 None（无矛盾）。"""
    comp, _ = tarjan_scc(adj, 2 * n_vars)
    contradictory = []
    for p in range(n_vars):
        l0, l1 = lit_id(p, 0), lit_id(p, 1)
        if comp[l0] == comp[l1] and comp[l0] != -1:
            contradictory.append((p, 0))
    if not contradictory:
        return None
    best = None
    for p, v0 in contradictory:
        L, NL = lit_id(p, v0), lit_id(p, 1 - v0)
        pa = bfs_shortest(adj, L, NL)
        pb = bfs_shortest(adj, NL, L)
        if pa is None or pb is None:
            continue
        cycle = pa + pb[1:]
        vars_here = {c // 2 for c in cycle}
        cand = (len(cycle), len(vars_here))
        if best is None or cand < best[:2]:
            best = cand
    if best is None:
        return None
    return best[0], best[1]


def classify_completion(c):
    edges_37 = [tuple(e) for e in c["edges_37"]]
    bits_37 = list(c["bits_37"])
    free_positions = list(c["free_positions"])
    W = len(free_positions)
    free_set = set(free_positions)

    fs = build_correct_fs(edges_37, bits_37, free_positions)
    unary, unary_contradiction, binary = extract_unary_binary(fs, free_set)

    adj_full, _, _ = build_implication_graph(unary, unary_contradiction, binary, W)
    adj_pure, _, _ = build_implication_graph([], False, binary, W)

    full = shortest_contradiction(adj_full, W)
    pure = shortest_contradiction(adj_pure, W)
    pure_exact_vars = exact_min_contradiction_vars(adj_pure, W)

    full_unsat = full is not None
    pure_unsat = pure is not None

    if full_unsat and not pure_unsat:
        typ = "trap"
    elif pure_unsat:
        typ = "pure_binary"
    else:
        typ = "sat"

    return {
        "bid": c["bid"], "mask": c["mask"], "comp_idx": c["comp_idx"],
        "W": W, "n_unary": len(unary), "n_binary": len(binary),
        "unary_contradiction": unary_contradiction,
        "full_unsat": full_unsat, "pure_unsat": pure_unsat,
        "type": typ,
        "full_edges": full[0] if full else None,
        "full_vars": full[1] if full else None,
        "pure_edges": pure[0] if pure else None,
        "pure_vars": pure[1] if pure else None,
        "pure_exact_vars": pure_exact_vars,
    }


def run(tag, fname):
    data = json.loads((HERE / fname).read_text())
    completions = data["completions"]
    rows = [classify_completion(c) for c in completions]
    n = len(rows)
    n_unsat = sum(1 for r in rows if r["full_unsat"])
    type_dist = Counter(r["type"] for r in rows)
    n_trap = type_dist.get("trap", 0)
    n_pure = type_dist.get("pure_binary", 0)
    n_sat = type_dist.get("sat", 0)

    print(f"\n===== {tag} =====")
    print(f"补全总数={n}  全图UNSAT={n_unsat}  SAT/无环={n_sat}")
    print(f"类型分布: trap(依赖一元)={n_trap}  pure_binary(无一元)={n_pure}  sat={n_sat}")
    if n_pure:
        pv = Counter(r["pure_exact_vars"] for r in rows if r["type"] == "pure_binary")
        pe = Counter(r["pure_edges"] for r in rows if r["type"] == "pure_binary")
        print(f"  纯二元 最短矛盾环 最少变量数(精确子集枚举) 分布: {dict(sorted(pv.items()))}")
        print(f"  纯二元 最短矛盾环 蕴含边数 分布: {dict(sorted(pe.items()))}")

    out = {
        "tag": tag, "n_completions": n, "n_unsat": n_unsat,
        "type_distribution": dict(type_dist),
        "n_trap": n_trap, "n_pure_binary": n_pure, "n_sat": n_sat,
        "rows": rows,
    }
    return out


def main():
    results = {}
    for tag, fname in [("k14", "all_completions_kernelized.json"),
                       ("k15", "all_completions_k15_kernelized.json")]:
        results[tag] = run(tag, fname)
    (HERE / "contradiction_classification.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n写入 contradiction_classification.json [COMPUTATIONAL CERTIFICATE]")

    for tag, res in results.items():
        td = res["type_distribution"]
        print(f"[证书] {tag}: 补全={res['n_completions']} UNSAT={res['n_unsat']} "
              f"trap={td.get('trap',0)} pure_binary={td.get('pure_binary',0)} sat={td.get('sat',0)}")


if __name__ == "__main__":
    main()
