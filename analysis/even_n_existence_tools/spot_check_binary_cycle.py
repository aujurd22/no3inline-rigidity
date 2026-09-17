#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抽查：对单幅补全显式抽出纯二元(无一元)矛盾环，确认纯二元 UNSAT 为真实几何 obstruction。"""
from __future__ import annotations

import json
from pathlib import Path

from scc_prescreen import (
    build_correct_fs, extract_unary_binary, build_implication_graph,
    tarjan_scc, lit_id, bfs_shortest,
)

HERE = Path(__file__).resolve().parent


def main():
    data = json.loads((HERE / "all_completions_kernelized.json").read_text())
    c = data["completions"][0]  # v20_01 mask 8929978983 comp 0
    edges_37 = [tuple(e) for e in c["edges_37"]]
    bits_37 = list(c["bits_37"])
    free_positions = list(c["free_positions"])
    W = len(free_positions)
    fs = build_correct_fs(edges_37, bits_37, free_positions)
    unary, uc, binary = extract_unary_binary(fs, set(free_positions))
    # 纯二元图
    adj, ec, cu = build_implication_graph([], False, binary, W)
    comp, _ = tarjan_scc(adj, 2 * W)
    # 找一对矛盾字面量并打印最短矛盾环
    pair = next((p, v) for p in range(W) for v in (0, 1)
                if comp[lit_id(p, v)] == comp[lit_id(p, 1 - v)])
    L = lit_id(*pair)
    NL = lit_id(pair[0], 1 - pair[1])
    pa = bfs_shortest(adj, L, NL)
    pb = bfs_shortest(adj, NL, L)
    cycle = pa + pb[1:]
    print(f"补全 bid={c['bid']} mask={c['mask']} comp={c['comp_idx']}  W={W}")
    print(f"纯二元约束数={len(binary)}  一元约束数={len(unary)}")
    print(f"矛盾变量对: x_{pair[0]} 两字面量同 SCC (comp={comp[L]})")
    print(f"显式纯二元矛盾环(字面量序列, 长度={len(cycle)}):")
    lits = [(cyc // 2, cyc % 2) for cyc in cycle]
    print("  ", lits)
    print(f"环上不同自由变量数={len({v for (v, _vv) in lits})}")
    # 打印环上每条边的约束来源(owner_set)
    for i in range(len(cycle) - 1):
        u, v = cycle[i], cycle[i + 1]
        kind, owner = ec.get((u, v), ("?", ()))
        print(f"  边 ({lits[i]}) -> ({lits[i+1]}): {kind} owner={list(owner)}")


if __name__ == "__main__":
    main()
