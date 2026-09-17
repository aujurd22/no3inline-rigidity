# -*- coding: utf-8 -*-
"""MUS 核大小 vs 2-因子基态缺陷 相关性分析（结构性定理线索）。

对每个 2-因子：compute_defects(edges) 得基态坏三元组数（全零取向）；
fast_build_3cnf + extract_mus 得最小 UNSAT 核的 cell 数/子句数。
检验：低缺陷 -> 局部小核？高缺陷 -> 全局大核？（结构性定理方向）
"""
import json
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from scan_new_basins import random_2factor, compute_defects  # noqa: E402
from fast_3cnf import fast_build_3cnf  # noqa: E402
from extract_mus_3sat import extract_mus  # noqa: E402

rng = random.Random(20260731)
N_SAMPLES = 120
rows = []

# 随机 2-因子
for i in range(N_SAMPLES):
    edges = random_2factor(rng)
    bt, orb = compute_defects(edges)
    clauses, nvars = fast_build_3cnf(edges)
    mus = extract_mus(clauses, nvars, node_budget=20_000_000)
    cells = set()
    for cl in mus:
        for lit in cl:
            cells.add(lit // 2)
    rows.append({"kind": "random", "idx": i, "base_bad_triples": bt,
                 "defect_orbits": orb, "mus_cells": len(cells),
                 "mus_clauses": len(mus), "n_clauses_total": len(clauses)})
    if (i + 1) % 20 == 0:
        print(f"  随机 [{i+1}/{N_SAMPLES}] base_bt={bt} mus_cells={len(cells)}")

# 6 盆地
arch = json.load(open(HERE.parent / "v20_basin_archive.json", encoding="utf-8"))
for b in arch["archive"]:
    edges = [tuple(e) for e in b["edges"]]
    bt, orb = compute_defects(edges)
    clauses, nvars = fast_build_3cnf(edges)
    mus = extract_mus(clauses, nvars, node_budget=40_000_000)
    cells = set()
    for cl in mus:
        for lit in cl:
            cells.add(lit // 2)
    rows.append({"kind": "basin", "idx": b["id"], "base_bad_triples": bt,
                 "defect_orbits": orb, "mus_cells": len(cells),
                 "mus_clauses": len(mus), "n_clauses_total": len(clauses)})
    print(f"  盆地 {b['id']}: base_bt={bt} mus_cells={len(cells)}")

Path(HERE / "core_defect_correlation.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

# 相关性分析
ran = [r for r in rows if r["kind"] == "random"]
xs = [r["base_bad_triples"] for r in ran]
ys = [r["mus_cells"] for r in ran]
n = len(xs)
mx, my = statistics.mean(xs), statistics.mean(ys)
cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
sx = statistics.pstdev(xs)
sy = statistics.pstdev(ys)
corr = cov / (sx * sy) if sx and sy else 0
print(f"\n=== 随机 {n} 样本：base_bad_triples vs mus_cells ===")
print(f"  base_bt: min={min(xs)} max={max(xs)} mean={mx:.1f}")
print(f"  mus_cells: min={min(ys)} max={max(ys)} mean={my:.1f}")
print(f"  皮尔逊相关系数 r = {corr:.3f}")

# 分箱：低/中/高缺陷的 mus_cells 中位
import collections
def bucket(bt):
    if bt < 50: return "低(<50)"
    if bt < 150: return "中(50-149)"
    return "高(>=150)"
bk = collections.defaultdict(list)
for r in ran:
    bk[bucket(r["base_bad_triples"])].append(r["mus_cells"])
print("  各缺陷档 mus_cells 中位:")
for k in ["低(<50)", "中(50-149)", "高(>=150)"]:
    v = bk.get(k, [])
    if v:
        print(f"    {k}: n={len(v)} 中位={sorted(v)[len(v)//2]} min={min(v)} max={max(v)}")
print("\n写入 core_defect_correlation.json")
