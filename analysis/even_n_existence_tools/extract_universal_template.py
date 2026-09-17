#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用奇数环模板普查：对每幅补全抽取最小纯二元矛盾环，记录几何结构。

目的：检验是否存在跨补全/跨盆地的不变几何模板（特定自由格集合 + 固定旧点），
该模板在 C4 对称下被强制出现 → 通向 G′ 的部分证明。

方法：
- 对每补全构造纯二元蕴含图（忽略一元），Tarjan SCC 找矛盾字面量对，
  取其最短环作为最小纯二元矛盾见证。
- 记录环上每条二元边的 owner_set（3 胞：2 自由 + 1 固定）与固定旧点身份。
- 按「自由格集合（basin 内 cell 索引）」与「固定旧点集合」聚合，统计复现频率。

[COMPUTATIONAL CERTIFICATE]，产物 universal_template_census.json。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from scc_prescreen import (
    build_correct_fs, extract_unary_binary, build_implication_graph,
    tarjan_scc, lit_id, bfs_shortest,
)

HERE = Path(__file__).resolve().parent


def minimal_pure_binary_cycle(edges_37, bits_37, free_positions):
    W = len(free_positions)
    free_set = set(free_positions)
    fs = build_correct_fs(edges_37, bits_37, free_positions)
    unary, _uc, binary = extract_unary_binary(fs, free_set)
    # 纯二元：丢弃 unary
    adj, edge_constraints, _cu = build_implication_graph([], False, binary, W)
    n_lits = 2 * W
    comp, _ = tarjan_scc(adj, n_lits)
    contradictory = []
    for p in range(W):
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
        if pa and pb:
            cyc = pa + pb[1:]
            if best is None or len(cyc) < len(best):
                best = cyc
    if best is None:
        return None
    # 解析环上边 → owner_set
    edges_info = []
    for i in range(len(best) - 1):
        u, v = best[i], best[i + 1]
        kind, owner = edge_constraints.get((u, v), ("?", ()))
        edges_info.append({
            "edge": [u // 2, u % 2, v // 2, v % 2],
            "owner_set": list(owner),
        })
    free_in_cycle = sorted({e["edge"][0] for e in edges_info} | {e["edge"][2] for e in edges_info})
    fixed_old = sorted({c for e in edges_info for c in e["owner_set"] if c not in free_set})
    return {
        "cycle_len": len(best),
        "free_cells": free_in_cycle,
        "fixed_old_cells": fixed_old,
        "edges": edges_info,
    }


def main():
    data = json.loads((HERE / "all_completions_kernelized.json").read_text())
    data15 = json.loads((HERE / "all_completions_k15_kernelized.json").read_text())
    out = {"k14": [], "k15": []}
    template_counter = Counter()
    for tag, d in (("k14", data), ("k15", data15)):
        for c in d["completions"]:
            edges_37 = [tuple(e) for e in c["edges_37"]]
            bits_37 = list(c["bits_37"])
            free_positions = list(c["free_positions"])
            res = minimal_pure_binary_cycle(edges_37, bits_37, free_positions)
            if res is None:
                out[tag].append({"bid": c["bid"], "mask": c["mask"],
                                  "comp_idx": c["comp_idx"], "pure_binary_cycle": None})
                continue
            rec = {"bid": c["bid"], "mask": c["mask"], "comp_idx": c["comp_idx"],
                   "W": len(free_positions), "pure_binary_cycle": res}
            out[tag].append(rec)
            # 模板键：自由格集合 + 固定旧点集合（basin 内绝对索引）
            key = (tuple(res["free_cells"]), tuple(res["fixed_old_cells"]))
            template_counter[key] += 1
    summary = {
        "n_k14": len(out["k14"]),
        "n_k15": len(out["k15"]),
        "n_k14_with_cycle": sum(1 for r in out["k14"] if r.get("pure_binary_cycle")),
        "n_k15_with_cycle": sum(1 for r in out["k15"] if r.get("pure_binary_cycle")),
        "distinct_templates": len(template_counter),
        "top_templates": [
            {"free_cells": list(k[0]), "fixed_old_cells": list(k[1]), "count": v}
            for k, v in template_counter.most_common(15)
        ],
    }
    (HERE / "universal_template_census.json").write_text(
        json.dumps({"summary": summary, "detail": out}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
