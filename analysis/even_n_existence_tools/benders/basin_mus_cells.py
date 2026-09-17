#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 6 个 V20 盆地抽 MUS 并保存具体 cell 组合（universal obstruction 对照）。
2026-07-21，与随机低约束 2-因子的 MUS 对比，寻找公共障碍结构。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from prepare_v20_basin_archive import c4_lifts, directed_cells  # noqa: E402
from fast_3cnf import fast_build_3cnf  # noqa: E402
from extract_mus_3sat import extract_mus  # noqa: E402

arch = json.load(open(HERE.parent / "v20_basin_archive.json", encoding="utf-8"))

out = {}
for b in arch["archive"]:
    bid = b["id"]
    edges = [tuple(e) for e in b["edges"]]
    clauses, nvars = fast_build_3cnf(edges)
    mus = extract_mus(clauses, nvars, node_budget=20_000_000)
    cells = set()
    for cl in mus:
        for lit in cl:
            cells.add(lit // 2)
    out[bid] = {
        "n_clauses_total": len(clauses),
        "mus_clauses": len(mus),
        "mus_cells": len(cells),
        "mus_cells_list": sorted(cells),
        "mus_clauses_list": [list(cl) for cl in mus],
    }
    print(f"  {bid}: 总子句={len(clauses)} MUS子句={len(mus)} "
          f"cell={len(cells)}/{nvars}  列表={sorted(cells)}")

Path(HERE / "basin_mus_cells.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n写入 basin_mus_cells.json（{len(out)} 盆地）")
