# -*- coding: utf-8 -*-
"""直接用精确 oracle 验证三元冲突核的两个关键断言：
(1) 自由常数子句：某三元组的所有自由cell朝向组合都共线（如 v20_01 的 {6,22,26}）。
(2) 非平凡子句：坏组合数与分解一致（如 v20_02 mask1 的 {2,26,31} n_free=3, bad_combos=2）。
"""
import json
import itertools

from prepare_v20_basin_archive import geometry_and_defects

arch = json.load(open("v20_basin_archive.json"))
by_id = {b["id"]: b for b in arch["archive"]}
W = 14


def check(bid, mask, cells, expect_bad_combos):
    base = by_id[bid]
    edges = [tuple(e) for e in base["edges"]]
    base_bits = list(base["bits"])
    free_positions = [i for i in range(37) if (mask >> i) & 1]
    # 枚举这些 cells 的所有 2^|cells∩free| 组合，其余自由cell固定在基朝向
    free_set = set(free_positions)
    var_cells = [c for c in cells if c in free_set]
    print(f"\n[{bid} mask={mask}] 验证三元组 {cells} (自由变量cell={var_cells})")
    bad = 0
    for combo in itertools.product([0, 1], repeat=len(var_cells)):
        bits = list(base_bits)
        for c, b in zip(var_cells, combo):
            bits[c] = b
        _, defects = geometry_and_defects(edges, bits)
        owners = set(tuple(sorted(d)) for d in defects)
        if tuple(sorted(cells)) in owners:
            bad += 1
    print(f"  精确 oracle: {bad}/{2 ** len(var_cells)} 组合共线; 分解预期={expect_bad_combos}")
    return bad == expect_bad_combos


if __name__ == "__main__":
    ok = True
    ok &= check("v20_01", 8929978983, [6, 22, 26], 8)   # 全8组合应共线
    ok &= check("v20_01", 99346809573, [6, 22, 26], 2)  # 仅1自由cell→2组合应共线
    ok &= check("v20_02", 7198212551, [2, 26, 31], 2)   # n_free=3, 2组合共线
    ok &= check("v20_02", 7198212551, [14, 28, 31], 1)  # n_free=1, 1组合共线
    print("\n全部一致:" , ok)
