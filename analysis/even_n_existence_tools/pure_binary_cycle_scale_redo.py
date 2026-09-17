#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pure_binary_cycle_scale 修正重做（2026-07-21）。

旧版 pure_binary_cycle_scale.json 记录的是「两顶点普通有向环」（如
字面量序列 [3,0,3]，即 lit_3 -> lit_0 -> lit_3），它只是 implication 图里的
一条普通双向边，**不保证是矛盾见证**——矛盾见证要求某个变量 x 的两个文字
lit(x,0) 与 lit(x,1) 落在同一 SCC 且被一条环同时遍历。旧文件把普通有向环
当成 obstruction 尺度，是错误的。

本修正版严格按已验证口径（classify_contradiction_type.py / verify_pure_binary_reclassify.py）：
  1. 对每幅补全构建 全图（含一元） 与 纯二元图（剔除一切一元）。
  2. 分类：
       trap        : 全图 UNSAT 且 纯二元图 NOT UNSAT（矛盾依赖一元强制）
       pure_binary : 纯二元图 UNSAT（矛盾不依赖任何一元）
       sat         : 两者皆 SAT（需回退几何 oracle）
  3. 对每幅 UNSAT 补全抽取**真正的矛盾环**：找矛盾变量 p，取
       lit(p,0) -> ... -> lit(p,1) -> ... -> lit(p,0)
     的双向最短路径拼接，得到同时遍历 x 两文字的最小环（边数与变量数）。
  4. 对纯二元补全额外用精确子集枚举 exact_min_contradiction_vars(adj,W)
     给出最小矛盾变量数（k=2,3,4 全枚举，严谨上界）。

所有结论标 [COMPUTATIONAL CERTIFICATE]，不当定理。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scc_prescreen import (
    build_correct_fs, extract_unary_binary, build_implication_graph,
    tarjan_scc, bfs_shortest, lit_id, exact_min_contradiction_vars,
)

HERE = Path(__file__).resolve().parent


def shortest_contradiction_cycle(adj, n_vars):
    """返回 (edges, vars, literal_cycle) 或 None。

    literal_cycle 是同时遍历某矛盾变量两个文字的最短有向环（字面量下标序列，
    首位重复以闭合）。与旧版「任意两顶点有向环」不同，此环必含一对
    (lit(p,0), lit(p,1)) 于同一 SCC 且被同一条环连通，是真正的矛盾见证。
    """
    comp, _ = tarjan_scc(adj, 2 * n_vars)
    contradictory = [p for p in range(n_vars)
                     if comp[lit_id(p, 0)] == comp[lit_id(p, 1)] and comp[lit_id(p, 0)] != -1]
    if not contradictory:
        return None
    best = None
    for p in contradictory:
        L, NL = lit_id(p, 0), lit_id(p, 1)
        pa = bfs_shortest(adj, L, NL)
        pb = bfs_shortest(adj, NL, L)
        if pa is None or pb is None:
            continue
        cycle = pa + pb[1:]          # L ... NL ... L，首位 L 重复闭合
        vars_here = {c // 2 for c in cycle}
        # 闭环首尾重复同一文字，故边数 = 字面量数 - 1（旧版误用 len(cycle)）
        cand = (len(cycle) - 1, len(vars_here), cycle)
        if best is None or (cand[0], cand[1]) < (best[0], best[1]):
            best = cand
    if best is None:
        return None
    return best


def analyze_completion(c):
    edges_37 = [tuple(e) for e in c["edges_37"]]
    bits_37 = list(c["bits_37"])
    free_positions = list(c["free_positions"])
    W = len(free_positions)
    free_set = set(free_positions)

    fs = build_correct_fs(edges_37, bits_37, free_positions)
    unary, unary_contradiction, binary = extract_unary_binary(fs, free_set)

    adj_full, _, _ = build_implication_graph(unary, unary_contradiction, binary, W)
    adj_pure, _, _ = build_implication_graph([], False, binary, W)

    full = shortest_contradiction_cycle(adj_full, W)
    pure = shortest_contradiction_cycle(adj_pure, W)
    pure_exact_vars = exact_min_contradiction_vars(adj_pure, W)

    full_unsat = full is not None
    pure_unsat = pure is not None

    if full_unsat and not pure_unsat:
        typ = "trap"
    elif pure_unsat:
        typ = "pure_binary"
    else:
        typ = "sat"

    def pack(cyc):
        if cyc is None:
            return None
        edges, vars_, lit_cycle = cyc
        return {"edges": edges, "vars": vars_,
                "cycle": [(x // 2, x % 2) for x in lit_cycle]}

    return {
        "bid": c["bid"], "mask": c["mask"], "comp_idx": c["comp_idx"],
        "W": W, "n_unary": len(unary), "n_binary": len(binary),
        "type": typ,
        "full_unsat": full_unsat, "pure_unsat": pure_unsat,
        "full_cycle": pack(full),
        "pure_cycle": pack(pure),
        "pure_exact_vars": pure_exact_vars,
    }


def run(tag, fname):
    data = json.loads((HERE / fname).read_text())
    rows = [analyze_completion(c) for c in data["completions"]]
    n = len(rows)
    type_dist = Counter(r["type"] for r in rows)
    n_trap = type_dist.get("trap", 0)
    n_pure = type_dist.get("pure_binary", 0)
    n_sat = type_dist.get("sat", 0)

    print(f"\n===== {tag} =====")
    print(f"补全总数={n}  类型: trap={n_trap} pure_binary={n_pure} sat={n_sat}")

    # 纯二元矛盾环尺度分布（真正矛盾环：含某变量两文字）
    if n_pure:
        pe = Counter(r["pure_cycle"]["edges"] for r in rows if r["type"] == "pure_binary")
        pv = Counter(r["pure_cycle"]["vars"] for r in rows if r["type"] == "pure_binary")
        exv = Counter(r["pure_exact_vars"] for r in rows if r["type"] == "pure_binary")
        print(f"  纯二元 最短矛盾环 边数(字面量)分布: {dict(sorted(pe.items()))}")
        print(f"  纯二元 最短矛盾环 变量数分布:       {dict(sorted(pv.items()))}")
        print(f"  纯二元 精确最小矛盾变量数(子集枚举)分布: {dict(sorted(exv.items()))}")
        # 抽查一个例子，证明环确实含某变量两文字
        ex = next(r for r in rows if r["type"] == "pure_binary")
        print(f"  抽查 bid={ex['bid']} mask={ex['mask']}: 矛盾环={ex['pure_cycle']['cycle']} "
              f"(变量={ex['pure_cycle']['vars']})")

    # 陷阱矛盾环尺度（来自全图，含一元强制）
    if n_trap:
        te = Counter(r["full_cycle"]["edges"] for r in rows if r["type"] == "trap")
        tv = Counter(r["full_cycle"]["vars"] for r in rows if r["type"] == "trap")
        print(f"  陷阱 最短矛盾环 边数分布: {dict(sorted(te.items()))}")
        print(f"  陷阱 最短矛盾环 变量数分布: {dict(sorted(tv.items()))}")

    return {
        "tag": tag, "n_completions": n,
        "type_distribution": dict(type_dist),
        "n_trap": n_trap, "n_pure_binary": n_pure, "n_sat": n_sat,
        "pure_cycle_edge_dist": (dict(sorted(Counter(
            r["pure_cycle"]["edges"] for r in rows if r["type"] == "pure_binary").items()))
            if n_pure else {}),
        "pure_cycle_var_dist": (dict(sorted(Counter(
            r["pure_cycle"]["vars"] for r in rows if r["type"] == "pure_binary").items()))
            if n_pure else {}),
        "pure_exact_vars_dist": (dict(sorted(Counter(
            r["pure_exact_vars"] for r in rows if r["type"] == "pure_binary").items()))
            if n_pure else {}),
        "trap_cycle_edge_dist": (dict(sorted(Counter(
            r["full_cycle"]["edges"] for r in rows if r["type"] == "trap").items()))
            if n_trap else {}),
        "trap_cycle_var_dist": (dict(sorted(Counter(
            r["full_cycle"]["vars"] for r in rows if r["type"] == "trap").items()))
            if n_trap else {}),
        "rows": rows,
    }


def main():
    results = {}
    for tag, fname in [("k14", "all_completions_kernelized.json"),
                       ("k15", "all_completions_k15_kernelized.json")]:
        results[tag] = run(tag, fname)
    (HERE / "pure_binary_cycle_scale_corrected.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n写入 pure_binary_cycle_scale_corrected.json [COMPUTATIONAL CERTIFICATE]")


if __name__ == "__main__":
    main()
