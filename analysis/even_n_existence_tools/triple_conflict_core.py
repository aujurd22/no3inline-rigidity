# -*- coding: utf-8 -*-
"""k=14 十九个候选的"三元冲突核"分析。

方法（全程纯 Python / NumPy，低 CPU）：
1. 复用 prepare_v20_basin_archive 的 directed_cells / c4_lifts 复刻每个 cell 的 4 个 C4 提升点。
2. 对每个 cell-三元组 owner_set（含两点同 cell 的 2-cell 情形、三点同 cell 的 1-cell 情形）：
   枚举其自由 cell 的朝向组合，用整数叉积判是否存在共线三点组；
   若存在，则该组合为"坏组合"，并入该 owner_set 对应的禁配子句 F_S
   （F_S = 所有坏组合对应的赋值空间子立方体之并，位掩码表示）。
3. F_S 即"该 cell-三元组在某朝向下共线"的赋值集合；要求所有三元组都不共线即为无-3-共线。
   候选 min_bad_triples>0 ⇒ 该子句集不可满足。用"覆盖计数删除法"提取最小不可满足核(MUS)。
4. 随机抽取赋值用精确 geometry_and_defects 交叉验证分解忠实性。
"""
from __future__ import annotations

import json
import glob
import itertools
import random
from collections import Counter

import numpy as np

from prepare_v20_basin_archive import c4_lifts, directed_cells, geometry_and_defects

W = 14  # 所有19候选的自由cell数；一般化为 popcount
N = 1 << W
FULL = (1 << N) - 1


def build_points(edges, base_bits):
    """复刻 oracle：P[(cell_index, bit)] = 4 个 C4 提升点。"""
    P = {}
    for i, (u, v) in enumerate(edges):
        for b in (0, 1):
            cell = directed_cells([(u, v)], [b])[0]
            P[(i, b)] = c4_lifts(cell)
    return P


def collinear(a, b, c):
    """整数叉积判三点共线（与 oracle 的 line_key 等价）。"""
    return (b[0] - a[0]) * (c[1] - a[1]) == (c[0] - a[0]) * (b[1] - a[1])


def combo_bad(P, cells_bits):
    """cells_bits: list of (cell_index, bit)。返回这些 cell 轨道间是否存在共线三点。"""
    n = len(cells_bits)
    if n == 3:
        (i, bi), (j, bj), (k, bk) = cells_bits
        A, B, C = P[(i, bi)], P[(j, bj)], P[(k, bk)]
        for a in A:
            for b in B:
                for c in C:
                    if collinear(a, b, c):
                        return True
        return False
    if n == 2:
        (i, bi), (j, bj) = cells_bits
        A, B = P[(i, bi)], P[(j, bj)]
        for a1, a2 in itertools.combinations(A, 2):
            for b in B:
                if collinear(a1, a2, b):
                    return True
        for b1, b2 in itertools.combinations(B, 2):
            for a in A:
                if collinear(a, b1, b2):
                    return True
        return False
    # n == 1
    (i, bi) = cells_bits[0]
    A = P[(i, bi)]
    for a1, a2, a3 in itertools.combinations(A, 3):
        if collinear(a1, a2, a3):
            return True
    return False


def build_fs(edges, base_bits, free_positions):
    """枚举所有 cell-三元组，返回 {owner_set: (F_S 位掩码, 坏组合数)}。"""
    P = build_points(edges, base_bits)
    free_set = set(free_positions)
    # 预建每位置每位子掩码
    masks = {}
    for p in range(W):
        m0 = m1 = 0
        for a in range(N):
            if (a >> p) & 1:
                m1 |= (1 << a)
            else:
                m0 |= (1 << a)
        masks[(p, 0)] = m0
        masks[(p, 1)] = m1

    fs = {}  # owner_set -> [mask, bad_combo_count]

    def add_owner(cells):
        # cells: tuple of cell indices (去重前的原始下标)
        uniq = sorted(set(cells))
        key = tuple(uniq)
        if key in fs:
            return
        # 每 cell 的朝向可能值
        poss = []
        for c in uniq:
            poss.append([0, 1] if c in free_set else [base_bits[c]])
        mask = 0
        bad_count = 0
        for combo in itertools.product(*poss):
            if combo_bad(P, list(zip(uniq, combo))):
                bad_count += 1
                sub = FULL
                for c, bit in zip(uniq, combo):
                    if c in free_set:
                        p = free_positions.index(c)
                        sub &= masks[(p, bit)]
                mask |= sub
        if mask:  # 仅记非空（出现的）子句
            fs[key] = (mask, bad_count)

    # 1-cell
    for i in range(len(edges)):
        add_owner((i,))
    # 2-cell
    for i, j in itertools.combinations(range(len(edges)), 2):
        add_owner((i, j))
    # 3-cell
    for i, j, k in itertools.combinations(range(len(edges)), 3):
        add_owner((i, j, k))
    return fs


def extract_mus(fs, restarts=3, seed=0):
    """覆盖计数删除法提取最小不可满足核（按包含最小）。逐个删除、每次重算，避免批量过度删除。"""
    random.seed(seed)
    best = None
    for _ in range(restarts):
        items = list(fs.items())
        random.shuffle(items)
        cover = np.zeros(N, dtype=np.int32)
        for _, (mask, _) in items:
            v = mask
            while v:
                b = v & (-v)
                cover[b.bit_length() - 1] += 1
                v ^= b
        core = list(items)
        while True:
            found = False
            for idx in range(len(core)):
                S, (mask, _) = core[idx]
                v = mask
                ok = True
                while v:
                    b = v & (-v)
                    if cover[b.bit_length() - 1] < 2:
                        ok = False
                        break
                    v ^= b
                if ok:
                    # 逐个删除并立即更新覆盖，再重算
                    v = mask
                    while v:
                        b = v & (-v)
                        cover[b.bit_length() - 1] -= 1
                        v ^= b
                    del core[idx]
                    found = True
                    break
            if not found:
                break
        if best is None or len(core) < len(best):
            best = list(core)
    return best


def validate(edges, base_bits, free_positions, fs, K=40, seed=12345):
    """抽 K 个随机赋值，用精确 oracle 比对 owner_set 集合是否一致。"""
    rng = random.Random(seed)
    free_set = set(free_positions)
    mism = 0
    for _ in range(K):
        a = rng.randrange(N)
        bits = list(base_bits)
        for p, c in enumerate(free_positions):
            bits[c] = (a >> p) & 1
        _, defects = geometry_and_defects(edges, bits)
        oracle_set = set(tuple(sorted(d)) for d in defects)
        pred_set = set(S for S in fs if (fs[S][0] >> a) & 1)
        if oracle_set != pred_set:
            mism += 1
            if mism <= 3:
                miss_pred = oracle_set - pred_set
                miss_orc = pred_set - oracle_set
                print(f"  [校验] 赋值{a}: 不一致 仅oracle有={miss_orc} 仅分解有={miss_pred}")
    return mism


def main():
    arch = json.load(open("v20_basin_archive.json"))
    by_id = {b["id"]: b for b in arch["archive"]}
    cert_files = sorted(glob.glob("v20_*_k14_certification.json"))
    all_results = []
    cell_freq = Counter()
    owner_freq = Counter()
    mus_sizes = []

    for cf in cert_files:
        d = json.load(open(cf))
        bid = d["base"]
        base = by_id[bid]
        edges = [tuple(e) for e in base["edges"]]
        base_bits = list(base["bits"])
        for s in d["survivors"]:
            mask = s["mask"]
            free_positions = [i for i in range(37) if (mask >> i) & 1]
            assert len(free_positions) == W, f"{bid} 自由数={len(free_positions)}"
            free_set = set(free_positions)
            fs = build_fs(edges, base_bits, free_positions)
            # 常数子句（F_S==FULL，即基骨架继承的恒定坏三点）单独统计
            constants = [S for S, (m, _) in fs.items() if m == FULL]
            # 仅保留"至少涉及1个自由cell"的子句 = 关于14个朝向变量的冲突超图
            fs_free = {S: (m, bc) for S, (m, bc) in fs.items()
                       if any(c in free_set for c in S)}
            mus = extract_mus(fs_free, restarts=4)
            # 校验（用完整 fs，确认分解忠实）
            mism = validate(edges, base_bits, free_positions, fs, K=40)
            # 统计（基于自由变量 MUS）
            core_cells = set()
            core_owner = []
            for S, (m, bc) in mus:
                core_cells.update(S)
                core_owner.append((S, sum(1 for c in S if c in free_set),
                                   bin(m).count("1"), bc))
                for c in S:
                    cell_freq[c] += 1
                owner_freq[S] += 1
            mus_sizes.append(len(mus))
            all_results.append({
                "base": bid, "mask": mask, "W": W,
                "certified_min_bad": s["min_bad_triples"],
                "n_clauses_total": len(fs),
                "n_clauses_free": len(fs_free),
                "n_constants": len(constants),
                "mus_size": len(mus),
                "mus_core_cells": sorted(core_cells),
                "mus_core_cell_count": len(core_cells),
                "mus_clauses": [
                    {"owner_set": list(S), "n_free": nf, "F_popcount": fp, "bad_combos": bc}
                    for S, nf, fp, bc in core_owner
                ],
                "validation_mismatches": mism,
            })
            print(f"{bid} mask={mask}: 子句总数={len(fs)} (自由={len(fs_free)}) "
                  f"常数={len(constants)} MUS(自由)大小={len(mus)} "
                  f"核cell数={len(core_cells)} 校验不一致={mism}")

    out = {
        "W": W, "N_assignments": N,
        "n_candidates": len(all_results),
        "mus_sizes": mus_sizes,
        "mus_size_min": min(mus_sizes), "mus_size_max": max(mus_sizes),
        "mus_size_mean": sum(mus_sizes) / len(mus_sizes),
        "cell_frequency": dict(cell_freq),
        "recurring_owner_sets": {str(k): v for k, v in owner_freq.items() if v >= 2},
        "candidates": all_results,
    }
    json.dump(out, open("triple_conflict_core.json", "w"), indent=1, ensure_ascii=False)
    print("\n=== 汇总 ===")
    print(f"候选数={len(all_results)}  MUS大小 min/mean/max="
          f"{min(mus_sizes)}/{sum(mus_sizes)/len(mus_sizes):.1f}/{max(mus_sizes)}")
    print(f"出现≥2次的 owner_set 数={len(out['recurring_owner_sets'])}")
    print("cell 出现频率 top10:", cell_freq.most_common(10))
    print("已写入 triple_conflict_core.json")


if __name__ == "__main__":
    main()
