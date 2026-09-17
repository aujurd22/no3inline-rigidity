#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证二元过约束是否内禀于盆地几何：把每盆地 37 个 cell 全当自由，查其二元图是否 UNSAT。

若 6 个盆地全 UNSAT，说明 obstruction 是盆地 37-cell 几何的固有属性
（非"选哪些格自由"的人为 artifact），有力支撑猜想 G′（二元过约束普适）。
[COMPUTATIONAL CERTIFICATE]。
"""
from __future__ import annotations

import json
from pathlib import Path

from scc_prescreen import (
    build_correct_fs, extract_unary_binary, build_implication_graph,
    tarjan_scc, lit_id,
)

HERE = Path(__file__).resolve().parent


def main():
    arch = json.loads((HERE / "v20_basin_archive.json").read_text())
    rows = []
    for b in arch["archive"]:
        edges = [tuple(e) for e in b["edges"]]
        bits = list(b["bits"])
        W = 37
        free = list(range(W))
        fs = build_correct_fs(edges, bits, free)
        unary, uc, binary = extract_unary_binary(fs, set(free))
        adj, _ec, _cu = build_implication_graph([], False, binary, W)
        comp, _ = tarjan_scc(adj, 2 * W)
        unsat = any(comp[lit_id(p, 0)] == comp[lit_id(p, 1)] and comp[lit_id(p, 0)] != -1
                    for p in range(W))
        # 二元图（无向）边数
        undir = set()
        for (p, a, q, b, _o) in binary:
            undir.add((min(p, q), max(p, q)))
        rows.append({"id": b["id"], "n_unary": len(unary), "n_binary": len(binary),
                     "binary_graph_edges": len(undir), "pure_binary_unsat": unsat})
        print(f"{b['id']}: 一元={len(unary)} 二元={len(binary)} 二元图边={len(undir)} "
              f"纯二元UNSAT={unsat}")
    n = len(rows)
    nu = sum(1 for r in rows if r["pure_binary_unsat"])
    print(f"\n6 盆地全自由二元图 UNSAT: {nu}/{n}")
    if nu == n:
        print("✓ obstruction 内禀于盆地几何（与选哪些格自由无关）")
    else:
        print("⚠ 存在盆地其全自由二元图 SAT（需进一步分析）")
    (HERE / "basin_binary_overconstraint.json").write_text(
        json.dumps({"rows": rows, "n_unsat": nu, "n": n}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print("写入 basin_binary_overconstraint.json")


if __name__ == "__main__":
    main()
