# -*- coding: utf-8 -*-
"""三元冲突核后处理：区分继承(基骨架) vs 新产生(替换耦合)，统计跨盆地反复核与方向壳。"""
import json
import itertools
from collections import Counter, defaultdict

from prepare_v20_basin_archive import geometry_and_defects

arch = json.load(open("v20_basin_archive.json"))
by_id = {b["id"]: b for b in arch["archive"]}
core = json.load(open("triple_conflict_core.json"))

# 1) 每个盆地的基坏三点集（全基朝向）
base_defects = {}
for bid, b in by_id.items():
    edges = [tuple(e) for e in b["edges"]]
    bits = list(b["bits"])
    _, defects = geometry_and_defects(edges, bits)
    base_defects[bid] = set(tuple(sorted(d)) for d in defects)
    print(f"{bid}: 基坏三点数={len(base_defects[bid])}")

# 2) 区分继承 vs 新产生
print("\n=== 每候选 MUS 来源（继承=基已有坏三点 / 新=替换产生耦合）===")
inherited_total = 0
new_total = 0
for r in core["candidates"]:
    bid = r["base"]
    inh = []; new = []
    for c in r["mus_clauses"]:
        os = tuple(c["owner_set"])
        if os in base_defects[bid]:
            inh.append(os)
        else:
            new.append(os)
    inherited_total += len(inh); new_total += len(new)
    tag = "继承" if not new else ("混合" if inh else "新产生")
    print(f"{bid} {r['mask']}: MUS={r['mus_size']} [{tag}] "
          f"继承={inh} 新={new}")

print(f"\n汇总: 继承子句={inherited_total} 新产生子句={new_total}")

# 3) 反复出现的 owner_set（跨候选）
print("\n=== 出现≥2次的 owner_set（跨候选反复核）===")
owner_basin = defaultdict(list)
for r in core["candidates"]:
    for c in r["mus_clauses"]:
        owner_basin[tuple(c["owner_set"])].append(r["base"])
for os, basins in sorted(owner_basin.items(), key=lambda x: -len(x[1])):
    if len(basins) >= 2:
        print(f"  {os}: 出现 {len(basins)} 次, 盆地={basins}")

# 4) 方向壳 cell 频率（MUS 核内）
print("\n=== MUS 核内 cell 出现频率 ===")
print(core["cell_frequency"])

# 5) 每盆地 MUS 大小分布
print("\n=== 每盆地 MUS 大小 ===")
by_basin = defaultdict(list)
for r in core["candidates"]:
    by_basin[r["base"]].append(r["mus_size"])
for bid in sorted(by_basin):
    print(f"  {bid}: sizes={sorted(by_basin[bid])} mean={sum(by_basin[bid])/len(by_basin[bid]):.2f}")
