#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立验证「纯二元 vs 陷阱」重新分类（Task #426）。

用户指出旧 classify_contradiction_type.py 把「2-变量 SCC 矛盾」一律判为陷阱，
但存在**无一元约束**的 2-变量纯二元 UNSAT（某变量对 4 种朝向组合全被禁）。
本脚本独立复核，构建两套蕴含图：
  - 全图：含一元强制 + 一元矛盾 + 二元禁配
  - 纯二元图：仅含二元禁配（剔除一切一元）
并据此正确分类每幅补全：
  - trap       : 全图 UNSAT 且 纯二元图 NOT UNSAT（矛盾依赖一元强制）
  - pure_binary: 纯二元图 UNSAT（矛盾不依赖任何一元）
  - sat        : 两者皆 SAT（靠三元耦合，需回退几何 oracle）

输出：23 个 k=14 补全的分类分布、最短矛盾环的「蕴含边数」与「不同变量数」、
以及「某变量对 4 种组合全禁」的直接计数。所有数字标 [COMPUTATIONAL CERTIFICATE]。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from scc_prescreen import (
    build_correct_fs, extract_unary_binary, build_implication_graph,
    tarjan_scc, bfs_shortest, lit_id,
)

HERE = Path(__file__).resolve().parent
SRC = "all_completions_kernelized.json"


def shortest_contradiction(adj, n_vars):
    """返回 (num_implication_edges, distinct_vars, cycle_lits) 或 None（无矛盾）。"""
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
        cycle = pa + pb[1:]          # 字面量环（含返回，len = 蕴含边数）
        vars_here = {c // 2 for c in cycle}
        cand = (len(cycle), len(vars_here), cycle)
        if best is None or (cand[0], cand[1]) < (best[0], best[1]):
            best = cand
    if best is None:
        return None
    return best[0], best[1], best[2]


def direct_four_forbidden(binary, n_vars):
    """直接检查是否存在某变量对 (p,q) 其 4 种 (a,b) 组合全部被禁。"""
    pairs = defaultdict(set)
    for (p, a, q, b, _owner) in binary:
        pairs[(p, q)].add((a, b))
    for (p, q), s in pairs.items():
        if len(s) == 4 and {(0, 0), (0, 1), (1, 0), (1, 1)} <= s:
            return True, (p, q)
    return False, None


def exact_min_contradiction_vars(adj, n_vars):
    """精确求纯二元图中最短矛盾环所涉变量数的最小值。

    对 k=2,3,4 枚举所有 k-子集 S，限制在 S 的字面量子图上跑 Tarjan，
    若存在某 p∈S 使 lit(p,0),lit(p,1) 同 SCC ⇒ 用 k 个变量即可矛盾。
    返回最小可达的 k（取首个成立的 k）。
    """
    from itertools import combinations
    for k in (2, 3, 4):
        for S in combinations(range(n_vars), k):
            S = set(S)
            sub = defaultdict(list)
            for u in range(2 * n_vars):
                if (u // 2) in S:
                    for w in adj[u]:
                        if (w // 2) in S:
                            sub[u].append(w)
            comp, _ = tarjan_scc(sub, 2 * n_vars)
            for p in S:
                if comp[lit_id(p, 0)] == comp[lit_id(p, 1)] and comp[lit_id(p, 0)] != -1:
                    return k, sorted(S)
    return None, None


def analyze(c):
    edges_37 = [tuple(e) for e in c["edges_37"]]
    bits_37 = list(c["bits_37"])
    free_positions = list(c["free_positions"])
    W = len(free_positions)
    free_set = set(free_positions)

    fs = build_correct_fs(edges_37, bits_37, free_positions)
    unary, unary_contradiction, binary = extract_unary_binary(fs, free_set)

    # 全图
    adj_full, _, contra_full = build_implication_graph(
        unary, unary_contradiction, binary, W)
    # 纯二元图（剔除一元）
    adj_pure, _, contra_pure = build_implication_graph(
        [], False, binary, W)

    full = shortest_contradiction(adj_full, W)
    pure = shortest_contradiction(adj_pure, W)

    full_unsat = full is not None
    pure_unsat = pure is not None
    has_unary = bool(unary) or unary_contradiction

    if full_unsat and not pure_unsat:
        typ = "trap"                      # 矛盾依赖一元强制
    elif pure_unsat:
        typ = "pure_binary"               # 矛盾无一元即成立
    else:
        typ = "sat"                       # 需三元耦合 oracle

    four, four_pair = direct_four_forbidden(binary, W)

    # 精确最小矛盾变量数（子集枚举，k=2,3,4）
    exact_k, exact_S = exact_min_contradiction_vars(adj_pure, W)

    return {
        "bid": c["bid"], "mask": c["mask"], "comp_idx": c["comp_idx"],
        "W": W, "n_unary": len(unary), "n_binary": len(binary),
        "unary_contradiction": unary_contradiction,
        "has_unary": has_unary,
        "full_unsat": full_unsat, "pure_unsat": pure_unsat,
        "type": typ,
        "full_edges": full[0] if full else None,
        "full_vars": full[1] if full else None,
        "pure_edges": pure[0] if pure else None,
        "pure_vars": pure[1] if pure else None,
        "exact_min_vars": exact_k,
        "four_forbidden_pair": four,
        "four_pair": list(four_pair) if four_pair else None,
    }


def main():
    data = json.loads((HERE / SRC).read_text())
    rows = [analyze(c) for c in data["completions"]]

    n = len(rows)
    type_dist = Counter(r["type"] for r in rows)
    n_four = sum(1 for r in rows if r["four_forbidden_pair"])

    print(f"===== k=14 纯二元重新分类验证 ({SRC}) =====")
    print(f"补全总数={n}")
    print(f"类型分布: {dict(type_dist)}")
    print(f"「某变量对4组合全禁」直接计数 = {n_four}/{n}")

    # 最短矛盾环统计（分别报全图与纯二元图）
    edge_full = Counter(r["full_edges"] for r in rows if r["full_unsat"])
    var_full = Counter(r["full_vars"] for r in rows if r["full_unsat"])
    edge_pure = Counter(r["pure_edges"] for r in rows if r["pure_unsat"])
    var_pure = Counter(r["pure_vars"] for r in rows if r["pure_unsat"])
    exact_var = Counter(r["exact_min_vars"] for r in rows if r["pure_unsat"])
    print(f"[全图] 最短矛盾环 蕴含边数 分布: {dict(sorted(edge_full.items()))}")
    print(f"[全图] 最短矛盾环 不同变量数 分布: {dict(sorted(var_full.items()))}")
    print(f"[纯二元图] 最短矛盾环 蕴含边数 分布: {dict(sorted(edge_pure.items()))}")
    print(f"[纯二元图] 最短矛盾环 不同变量数(BFS) 分布: {dict(sorted(var_pure.items()))}")
    print(f"[纯二元图] 最短矛盾环 不同变量数(精确子集枚举) 分布: {dict(sorted(exact_var.items()))}")

    # 逐行明细（纯二元图）
    print("\n----- 逐补全 纯二元图 最短矛盾环 -----")
    for r in rows:
        print(f"  {r['bid']} mask={r['mask']} comp={r['comp_idx']}: "
              f"type={r['type']} has_unary={r['has_unary']} "
              f"pure_edges={r['pure_edges']} pure_vars={r['pure_vars']} "
              f"four={r['four_forbidden_pair']}")

    # 纯二元 2-变量 明细
    pb2 = [r for r in rows if r["type"] == "pure_binary" and (r["pure_vars"] == 2)]
    print(f"\n纯二元且恰 2 变量 的补全数 = {len(pb2)}")
    for r in pb2:
        print(f"   bid={r['bid']} mask={r['mask']} comp={r['comp_idx']} "
              f"pure_edges={r['pure_edges']} pure_vars={r['pure_vars']} "
              f"four_pair={r['four_pair']}")

    # trap 明细
    traps = [r for r in rows if r["type"] == "trap"]
    print(f"\n陷阱(trap) 补全数 = {len(traps)}")
    for r in traps:
        print(f"   bid={r['bid']} mask={r['mask']} comp={r['comp_idx']} "
              f"n_unary={r['n_unary']} full_edges={r['full_edges']} full_vars={r['full_vars']}")

    out = {
        "source": SRC, "n_completions": n,
        "type_distribution": dict(type_dist),
        "four_forbidden_pair_count": n_four,
        "full_shortest_edges_distribution": {str(k): v for k, v in sorted(edge_full.items())},
        "full_shortest_vars_distribution": {str(k): v for k, v in sorted(var_full.items())},
        "pure_shortest_edges_distribution": {str(k): v for k, v in sorted(edge_pure.items())},
        "pure_shortest_vars_bfs_distribution": {str(k): v for k, v in sorted(var_pure.items())},
        "pure_shortest_vars_exact_distribution": {str(k): v for k, v in sorted(exact_var.items())},
        "rows": rows,
    }
    (HERE / "verify_pure_binary_reclassify.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n写入 verify_pure_binary_reclassify.json")

    # 严谨断言（供文档引用，标证书）
    print("\n----- [COMPUTATIONAL CERTIFICATE] 摘要 -----")
    print(f"k=14 23 个补全：全图 2-SAT UNSAT={sum(1 for r in rows if r['full_unsat'])}/{n}")
    print(f"  其中 trap(依赖一元)={type_dist.get('trap',0)}  pure_binary(无一元)={type_dist.get('pure_binary',0)}  sat={type_dist.get('sat',0)}")
    print(f"  直接「4组合全禁」对计数={n_four}")


if __name__ == "__main__":
    main()
