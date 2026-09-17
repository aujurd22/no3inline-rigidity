#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量化纯二元 obstruction 的最小尺度（真·简单环，修正非简单路径 artifact）。

对每幅补全：在纯二元矛盾 SCC 内，枚举边 (u,v)，BFS 求 v→u 最短路径得简单环，
取最短者报告 边数(=字面量数) 与 不同变量数。
[COMPUTATIONAL CERTIFICATE]。定理 B 保证：纯二元矛盾简单环不同变量数 ≥ 3（2-变量不可能）。
"""
from __future__ import annotations

import json
from collections import defaultdict, Counter
from pathlib import Path

from scc_prescreen import (
    build_correct_fs, extract_unary_binary, build_implication_graph,
    tarjan_scc, lit_id,
)

HERE = Path(__file__).resolve().parent


def shortest_simple_cycle(adj, comp, n_lits):
    # 找任一矛盾变量对
    target_scc = None
    for p in range(n_lits // 2):
        if comp[lit_id(p, 0)] == comp[lit_id(p, 1)] and comp[lit_id(p, 0)] != -1:
            target_scc = comp[lit_id(p, 0)]
            break
    if target_scc is None:
        return None
    scc_nodes = [v for v in range(n_lits) if comp[v] == target_scc]
    scc_set = set(scc_nodes)
    # 限制在该 SCC 内的邻接
    sub = {v: [w for w in adj[v] if w in scc_set] for v in scc_nodes}

    def bfs_path(src, dst):
        from collections import deque
        prev = {src: None}
        q = deque([src])
        while q:
            u = q.popleft()
            if u == dst:
                path = [dst]
                x = src
                while x is not None:
                    path.append(x)
                    x = prev[x]
                return list(reversed(path))
            for w in sub[u]:
                if w not in prev:
                    prev[w] = u
                    q.append(w)
        return None

    best = None
    for u in scc_nodes:
        for v in sub[u]:  # 边 u->v
            # 简单环: v -> ... -> u，再补上边 u->v
            path = bfs_path(v, u)
            if path is None:
                continue
            cycle = path + [v]  # 字面量序列（含重复的首尾 v）
            edges = len(cycle) - 1
            vars_ = len({x // 2 for x in cycle})
            if best is None or edges < best[0]:
                best = (edges, vars_, cycle)
    return best


def run(tag, fname):
    data = json.loads((HERE / fname).read_text())
    edge_lens = []
    var_counts = []
    examples = []
    for c in data["completions"]:
        edges_37 = [tuple(e) for e in c["edges_37"]]
        bits_37 = list(c["bits_37"])
        free_positions = list(c["free_positions"])
        W = len(free_positions)
        fs = build_correct_fs(edges_37, bits_37, free_positions)
        unary, uc, binary = extract_unary_binary(fs, set(free_positions))
        adj, _ec, _cu = build_implication_graph([], False, binary, W)
        comp, _ = tarjan_scc(adj, 2 * W)
        best = shortest_simple_cycle(adj, comp, 2 * W)
        if best is None:
            continue
        el, vc, cyc = best
        edge_lens.append(el)
        var_counts.append(vc)
        if len(examples) < 3:
            examples.append({"bid": c["bid"], "mask": c["mask"], "comp_idx": c["comp_idx"],
                             "edges": el, "vars": vc,
                             "cycle": [(x // 2, x % 2) for x in cyc]})
    n = len(edge_lens)
    print(f"\n===== {tag} =====")
    print(f"补全数={n}")
    print(f"最短纯二元简单矛盾环 边数(字面量): min={min(edge_lens)} max={max(edge_lens)} "
          f"中位={sorted(edge_lens)[n//2]} 均值={sum(edge_lens)/n:.2f}")
    print(f"最短纯二元简单矛盾环 不同变量数: min={min(var_counts)} max={max(var_counts)} "
          f"中位={sorted(var_counts)[n//2]} 均值={sum(var_counts)/n:.2f}")
    print(f"边数分布: {dict(sorted(Counter(edge_lens).items()))}")
    print(f"变量数分布: {dict(sorted(Counter(var_counts).items()))}")
    for e in examples:
        print(f"  例 bid={e['bid']} mask={e['mask']} comp={e['comp_idx']}: "
              f"{e['edges']}边/{e['vars']}变量 环={e['cycle']}")
    return {"tag": tag, "n": n, "min_edges": min(edge_lens), "max_edges": max(edge_lens),
            "min_vars": min(var_counts), "max_vars": max(var_counts),
            "edge_distribution": {str(k): v for k, v in sorted(Counter(edge_lens).items())},
            "var_distribution": {str(k): v for k, v in sorted(Counter(var_counts).items())},
            "examples": examples}


def main():
    out = {}
    for tag, fname in [("k14", "all_completions_kernelized.json"),
                       ("k15", "all_completions_k15_kernelized.json")]:
        out[tag] = run(tag, fname)
    (HERE / "pure_binary_cycle_scale.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n写入 pure_binary_cycle_scale.json")


if __name__ == "__main__":
    main()
