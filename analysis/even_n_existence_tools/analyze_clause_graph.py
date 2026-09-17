#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""二元子句图结构性实证（攻关 L3：长环不可能性）。

对每幅补全：
  (1) 纯二元 2-SAT（去掉所有一元约束）是否 UNSAT？=> 若出现则存在"长环/纯二元矛盾"，
      直接反驳猜想 G 的强形式（某些 UNSAT 非陷阱）。
  (2) 二元子句的无向图（节点=自由格，边=存在二元禁配的自由格对）：
      节点数、边数、连通分量、是否含环、最大度、三角形数。
  (3) 完整(一元+二元)矛盾 SCC 的变量集合，及其是否含一元强制变量（应含 => 是陷阱）。

所有结论标 [COMPUTATIONAL CERTIFICATE]，不当定理。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from scc_prescreen import (
    build_correct_fs, extract_unary_binary, build_implication_graph,
    tarjan_scc, lit_id,
)

HERE = Path(__file__).resolve().parent


def lit(p, v):
    return 2 * p + v


def analyze(c):
    edges_37 = [tuple(e) for e in c["edges_37"]]
    bits_37 = list(c["bits_37"])
    free_positions = list(c["free_positions"])
    W = len(free_positions)
    free_set = set(free_positions)

    fs = build_correct_fs(edges_37, bits_37, free_positions)
    unary, unary_contra, binary = extract_unary_binary(fs, free_set)

    unary_forced = {p for (p, a, _o) in unary}
    unary_forced_map = {p: a for (p, a, _o) in unary}

    # ── (1) 纯二元 2-SAT ──
    adj_b, _ec, _cu = build_implication_graph([], False, binary, W)
    n_lits = 2 * W
    comp_b, _ = tarjan_scc(adj_b, n_lits)
    pure_binary_unsat = False
    for p in range(W):
        if comp_b[lit(p, 0)] == comp_b[lit(p, 1)] and comp_b[lit(p, 0)] != -1:
            pure_binary_unsat = True
            break

    # ── (2) 二元无向图结构 ──
    nodes = set()
    undir_edges = set()
    for (p, a, q, b, _o) in binary:
        pp, qq = (p, q) if p < q else (q, p)
        undir_edges.add((pp, qq))
        nodes.add(p)
        nodes.add(q)
    # 连通分量 + 环检测（DFS 后边）
    adj_u = defaultdict(set)
    for (u, v) in undir_edges:
        adj_u[u].add(v)
        adj_u[v].add(u)
    visited = set()
    n_components = 0
    has_cycle = False
    comp_sizes = []
    for start in nodes:
        if start in visited:
            continue
        n_components += 1
        stack = [(start, None)]
        comp_nodes = set()
        while stack:
            u, parent = stack.pop()
            if u in visited:
                continue
            visited.add(u)
            comp_nodes.add(u)
            for w in adj_u[u]:
                if w == parent:
                    continue
                if w in visited:
                    has_cycle = True
                else:
                    stack.append((w, u))
        comp_sizes.append(len(comp_nodes))
    max_degree = max((len(adj_u[n]) for n in nodes), default=0)
    # 三角形数
    triangles = 0
    for (u, v) in undir_edges:
        common = adj_u[u] & adj_u[v]
        triangles += len(common)
    triangles //= 3

    # ── (3) 完整矛盾 SCC ──
    adj_f, _ec2, _cu2 = build_implication_graph(unary, unary_contra, binary, W)
    comp_f, _ = tarjan_scc(adj_f, n_lits)
    contra_vars = set()
    contra_has_unary = False
    for p in range(W):
        if comp_f[lit(p, 0)] == comp_f[lit(p, 1)] and comp_f[lit(p, 0)] != -1:
            contra_vars.add(p)
            if p in unary_forced:
                contra_has_unary = True
    full_unsat = bool(contra_vars)

    return {
        "bid": c["bid"], "mask": c["mask"], "comp_idx": c["comp_idx"],
        "W": W,
        "n_unary": len(unary), "n_binary": len(binary),
        "unary_forced_vars": sorted(unary_forced),
        "pure_binary_unsat": pure_binary_unsat,
        "binary_graph_nodes": len(nodes),
        "binary_graph_edges": len(undir_edges),
        "binary_graph_components": n_components,
        "binary_graph_has_cycle": has_cycle,
        "binary_graph_max_degree": max_degree,
        "binary_graph_triangles": triangles,
        "full_unsat": full_unsat,
        "contra_vars": sorted(contra_vars),
        "contra_has_unary": contra_has_unary,
    }


def run(tag, fname):
    data = json.loads((HERE / fname).read_text())
    rows = [analyze(c) for c in data["completions"]]
    n = len(rows)
    n_pbu = sum(1 for r in rows if r["pure_binary_unsat"])
    n_full = sum(1 for r in rows if r["full_unsat"])
    n_hascycle = sum(1 for r in rows if r["binary_graph_has_cycle"])
    n_tri = sum(1 for r in rows if r["binary_graph_triangles"] > 0)
    n_contrano_unary = sum(1 for r in rows if r["full_unsat"] and not r["contra_has_unary"])

    print(f"\n===== {tag} =====")
    print(f"补全数={n}")
    print(f"全(一元+二元) UNSAT={n_full}")
    print(f"纯二元 UNSAT={n_pbu}   <-- 若>0 即存在长环/纯二元矛盾(反驳强G)")
    print(f"二元图含环的补全数={n_hascycle}  二元图含三角形的补全数={n_tri}")
    print(f"矛盾 SCC 不含一元强制变量的补全数={n_contrano_unary}  <-- 应为0(否则非陷阱矛盾)")

    # 二元图边数 / 最大度分布
    edge_dist = Counter(r["binary_graph_edges"] for r in rows)
    deg_dist = Counter(r["binary_graph_max_degree"] for r in rows)
    print(f"二元图边数分布: {dict(sorted(edge_dist.items()))}")
    print(f"二元图最大度分布: {dict(sorted(deg_dist.items()))}")

    # 纯二元 UNSAT 或 矛盾无一元 的反例（应无）
    bad = [r for r in rows if r["pure_binary_unsat"] or (r["full_unsat"] and not r["contra_has_unary"])]
    if bad:
        print(f"⚠ 发现 {len(bad)} 个反例:")
        for r in bad[:10]:
            print(f"   bid={r['bid']} mask={r['mask']} comp={r['comp_idx']} "
                  f"pure_binary_unsat={r['pure_binary_unsat']} "
                  f"contra_has_unary={r['contra_has_unary']} "
                  f"contra_vars={r['contra_vars']}")
    else:
        print("✓ 无反例：纯二元均 SAT，且所有矛盾 SCC 均含一元强制变量(即均为陷阱)")

    return {
        "tag": tag, "n": n,
        "n_full_unsat": n_full, "n_pure_binary_unsat": n_pbu,
        "n_binary_graph_has_cycle": n_hascycle, "n_binary_graph_has_triangle": n_tri,
        "n_contra_no_unary": n_contrano_unary,
        "binary_edge_distribution": {str(k): v for k, v in sorted(edge_dist.items())},
        "binary_max_degree_distribution": {str(k): v for k, v in sorted(deg_dist.items())},
        "rows": rows,
    }


def main():
    out = {}
    for tag, fname in [("k14", "all_completions_kernelized.json"),
                       ("k15", "all_completions_k15_kernelized.json")]:
        out[tag] = run(tag, fname)
    (HERE / "clause_graph_analysis.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n写入 clause_graph_analysis.json")


if __name__ == "__main__":
    main()
