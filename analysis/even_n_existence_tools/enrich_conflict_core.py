# -*- coding: utf-8 -*-
"""固化三元冲突核 enriched 数据：继承/新产生标注 + 新三元组的具体禁配 nogood。"""
import json
import itertools
from collections import defaultdict

from prepare_v20_basin_archive import geometry_and_defects
from triple_conflict_core import build_points, combo_bad

arch = json.load(open("v20_basin_archive.json"))
by_id = {b["id"]: b for b in arch["archive"]}
core = json.load(open("triple_conflict_core.json"))

base_defects = {}
for bid, b in by_id.items():
    edges = [tuple(e) for e in b["edges"]]
    bits = list(b["bits"])
    _, defects = geometry_and_defects(edges, bits)
    base_defects[bid] = set(tuple(sorted(d)) for d in defects)


def forbidden_combos(edges, base_bits, free_positions, owner_set):
    """返回该 owner_set 的具体禁配组合（自由cell位置->bit）。"""
    P = build_points(edges, base_bits)
    free_set = set(free_positions)
    uniq = list(owner_set)
    var = [c for c in uniq if c in free_set]
    poss = [[0, 1] if c in free_set else [base_bits[c]] for c in uniq]
    out = []
    for combo in itertools.product(*poss):
        if combo_bad(P, list(zip(uniq, combo))):
            out.append({str(c): int(b) for c, b in zip(var, [combo[uniq.index(c)] for c in var])})
    return out


enriched = []
for r in core["candidates"]:
    bid = r["base"]
    base = by_id[bid]
    edges = [tuple(e) for e in base["edges"]]
    base_bits = list(base["bits"])
    free_positions = [i for i in range(37) if (r["mask"] >> i) & 1]
    inh = []; new = []
    for c in r["mus_clauses"]:
        os = tuple(c["owner_set"])
        entry = dict(c)
        if os in base_defects[bid]:
            entry["source"] = "inherited"
            inh.append(entry)
        else:
            entry["source"] = "new"
            # 提取具体禁配 nogood
            entry["forbidden_combos"] = forbidden_combos(
                edges, base_bits, free_positions, os)
            new.append(entry)
    enriched.append({
        "base": bid, "mask": r["mask"], "certified_min_bad": r["certified_min_bad"],
        "mus_size": r["mus_size"], "mus_core_cells": r["mus_core_cells"],
        "inherited_clauses": inh, "new_clauses": new,
    })

# 跨候选反复核（仅新产生）
recurring_new = defaultdict(list)
for e in enriched:
    for c in e["new_clauses"]:
        recurring_new[tuple(c["owner_set"])].append(e["base"])

out = {
    "summary": {
        "n_candidates": len(enriched),
        "inherited_clause_total": sum(len(e["inherited_clauses"]) for e in enriched),
        "new_clause_total": sum(len(e["new_clauses"]) for e in enriched),
        "per_basin_mus": {e["base"]: e["mus_size"] for e in enriched},
    },
    "candidates": enriched,
    "recurring_new_owner_sets": {str(k): v for k, v in recurring_new.items() if len(v) >= 2},
}
json.dump(out, open("triple_conflict_core_enriched.json", "w"), indent=1, ensure_ascii=False)
print("已写入 triple_conflict_core_enriched.json")
print(f"继承子句={out['summary']['inherited_clause_total']} 新产生子句={out['summary']['new_clause_total']}")
# 打印 v20_02 的新三元组 nogood 示例
for e in enriched:
    if e["base"] == "v20_02" and e["new_clauses"]:
        print(f"\n{e['base']} {e['mask']} 新三元组 nogood 示例:")
        for c in e["new_clauses"]:
            print(f"  {c['owner_set']} n_free={c['n_free']} 禁配={c.get('forbidden_combos')}")
