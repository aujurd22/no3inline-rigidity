# -*- coding: utf-8 -*-
"""6 盆地 MUS 胞的真实 (u,v) 几何签名分析（通用障碍定理线索）。

cell 索引 i ↔ edges_37[i] 的 (u,v) 基向（fast_build_3cnf 约定）。
映射 MUS 胞索引 -> (u,v)，分析其 C4 提升点是否共线与几何集中。
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from prepare_v20_basin_archive import c4_lifts, directed_cells, N  # noqa: E402
from fast_3cnf import fast_build_3cnf  # noqa: E402
from extract_mus_3sat import extract_mus  # noqa: E402

arch = json.load(open(HERE.parent / "v20_basin_archive.json", encoding="utf-8"))
edge_sets = {b["id"]: [tuple(e) for e in b["edges"]] for b in arch["archive"]}

# 网格对角线 / 边界等几何参考
DIAG = {(i, i) for i in range(N)}
ANTIDIAG = {(i, N - 1 - i) for i in range(N)}


def cell_lift_points(u, v):
    return c4_lifts((u, v))


report = {}
for bid, edges in edge_sets.items():
    clauses, nvars = fast_build_3cnf(edges)
    mus = extract_mus(clauses, nvars, node_budget=40_000_000)
    cells = set()
    for cl in mus:
        for lit in cl:
            cells.add(lit // 2)
    # 映射为 (u,v)
    uv_cells = [edges[c] for c in cells]
    # 几何特征
    on_diag = sum(1 for (u, v) in uv_cells if (u, v) in DIAG or (u, v) in ANTIDIAG)
    coords = []
    all_lift = []
    for (u, v) in uv_cells:
        coords.append((u, v))
        all_lift.extend(cell_lift_points(u, v))
    us = [u for u, v in uv_cells]
    vs = [v for u, v in uv_cells]
    report[bid] = {
        "mus_cells": len(cells),
        "uv_cells": uv_cells,
        "on_diag_or_antidiag": on_diag,
        "u_range": [min(us), max(us)],
        "v_range": [min(vs), max(vs)],
        "n_lift_points": len(all_lift),
    }

print("=== 6 盆地 MUS 胞真实 (u,v) 几何签名 ===")
for bid, info in report.items():
    print(f"\n{bid}: MUS胞数={info['mus_cells']}  对角/反对角上={info['on_diag_or_antidiag']}")
    print(f"  u范围={info['u_range']}  v范围={info['v_range']}")
    print(f"  MUS胞(u,v): {info['uv_cells']}")

# 跨盆地：哪些 (u,v) 出现在多个盆地的 MUS（真实坐标，非索引）
cnt = Counter()
for bid, info in report.items():
    for uv in info["uv_cells"]:
        cnt[uv] += 1
print("\n=== 跨盆地高频 MUS 胞 (u,v)（共 6 盆地）===")
for uv, f in sorted(cnt.items(), key=lambda x: -x[1]):
    if f >= 3:
        print(f"  {uv}: {f}/6")

Path(HERE / "basin_geom_obstruction.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n写入 basin_geom_obstruction.json")
