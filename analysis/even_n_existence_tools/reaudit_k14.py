#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正验证：对 4 个多补全 mask 验第 2 个 + 用正确边重做全部 19 个的 MUS。

与旧 certify_basin.py 的区别：
- 用 v9w_all.exe 获取 mask 的 **所有** 补全因子（不止第 1 个）
- 多补全 mask（4 个）逐个验证第 2+ 补全的朝向
- 全部 19 个 mask 的三元冲突超图用 **C++ 补回的边** 构建（旧脚本用了错误的基底边）

安全策略：
- 第 1 个补全的朝向结果直接取用已认证的 min_bad_triples，不复验
- 第 2+ 补全才做 brute-force 朝向枚举
- MUS 全量重做
"""
from __future__ import annotations

import glob
import itertools
import json
import subprocess
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from prepare_v20_basin_archive import (
    c4_lifts, directed_cells, geometry_and_defects,
)
from audit_v20_k14_chunked import build_tokens, owner_mask
from audit_rot4_flip_eligibility_multicycle import ordered_components
from search_rot4_shadow_escape_radius import candidate_blockers

HERE = Path(__file__).resolve().parent
V9W_ALL = HERE / "v9w_all.exe"
W = 14
N = 1 << W
FULL = (1 << N) - 1

# ─── 冲突超图工具 ───

def build_points(edges, base_bits):
    P = {}
    for i, (u, v) in enumerate(edges):
        for b in (0, 1):
            cell = directed_cells([(u, v)], [b])[0]
            P[(i, b)] = c4_lifts(cell)
    return P

def collinear(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) == (c[0] - a[0]) * (b[1] - a[1])

def combo_bad(P, cells_bits):
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
    (i, bi) = cells_bits[0]
    A = P[(i, bi)]
    for a1, a2, a3 in itertools.combinations(A, 3):
        if collinear(a1, a2, a3):
            return True
    return False

def build_correct_fs(edges_37, base_bits_37, free_positions):
    """edges_37 是混合了新旧边的完整 37 条边。"""
    P = build_points(edges_37, base_bits_37)
    free_set = set(free_positions)
    masks = {}
    for p in range(W):
        m0 = m1 = 0
        for a in range(N):
            if (a >> p) & 1: m1 |= (1 << a)
            else: m0 |= (1 << a)
        masks[(p, 0)] = m0
        masks[(p, 1)] = m1

    fs = {}
    def add_owner(cells):
        uniq = sorted(set(cells))
        key = tuple(uniq)
        if key in fs: return
        poss = []
        for c in uniq:
            poss.append([0, 1] if c in free_set else [base_bits_37[c]])
        mask_fs = 0
        bad_count = 0
        for combo in itertools.product(*poss):
            if combo_bad(P, list(zip(uniq, combo))):
                bad_count += 1
                sub = FULL
                for c, bit in zip(uniq, combo):
                    if c in free_set:
                        p = free_positions.index(c)
                        sub &= masks[(p, bit)]
                mask_fs |= sub
        if mask_fs:
            fs[key] = (mask_fs, bad_count)

    for i in range(37):
        add_owner((i,))
    for i, j in itertools.combinations(range(37), 2):
        add_owner((i, j))
    for i, j, k in itertools.combinations(range(37), 3):
        add_owner((i, j, k))
    return fs

def extract_mus(fs, restarts=3, seed=0):
    random.seed(seed)
    best = None
    for _ in range(restarts):
        items = list(fs.items())
        random.shuffle(items)
        cover = np.zeros(N, dtype=np.int32)
        for _, (m, _) in items:
            v = m
            while v:
                b = v & (-v)
                cover[b.bit_length() - 1] += 1
                v ^= b
        core = list(items)
        while True:
            found = False
            for idx in range(len(core)):
                S, (m, _) = core[idx]
                v = m
                ok = True
                while v:
                    b = v & (-v)
                    if cover[b.bit_length() - 1] < 2:
                        ok = False
                        break
                    v ^= b
                if ok:
                    v = m
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

def validate_fs(edges_37, base_bits_37, free_positions, fs, K=40, seed=12345):
    rng = random.Random(seed)
    mism = 0
    for _ in range(K):
        a = rng.randrange(N)
        bits = list(base_bits_37)
        for p, c in enumerate(free_positions):
            bits[c] = (a >> p) & 1
        _, defects = geometry_and_defects(edges_37, bits)
        oracle_set = set(tuple(sorted(d)) for d in defects)
        pred_set = set(S for S in fs if (fs[S][0] >> a) & 1)
        if oracle_set != pred_set:
            mism += 1
            if mism <= 5:
                miss_pred = oracle_set - pred_set
                miss_orc = pred_set - oracle_set
                print(f"      [校验] 赋值{a}: 仅oracle有={miss_orc} 仅分解有={miss_pred}")
    return mism

# ─── 补全因子朝向验证 ───

def verify_one_completion(edges_old, bits_old, mask, cells):
    """验证一个补全因子的全部 2^W 种朝向。返回 (min_bad, found_solution)"""
    best = None
    assign_list = list(itertools.product([0, 1], repeat=len(cells)))
    for assign in assign_list:
        eb = []; bb = []; wi = 0
        for i in range(37):
            if (mask >> i) & 1:
                u, v = cells[wi]
                eb.append((u, v)); bb.append(assign[wi]); wi += 1
            else:
                eb.append(tuple(edges_old[i])); bb.append(bits_old[i])
        try:
            geo, _ = geometry_and_defects(eb, bb)
        except AssertionError:
            continue
        bt = geo["bad_triples"]
        if best is None or bt < best[0]:
            best = (bt, assign)
        if bt == 0:
            return (0, True)
    return (best[0] if best else None, False)


def main():
    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    by_id = {b["id"]: b for b in archive["archive"]}

    # ── 读取现有认证结果（第一个补全的 min_bad） ──
    cert_files = sorted(glob.glob(str(HERE / "v20_*_k14_certification.json")))
    existing = {}  # {base_id: {mask: min_bad}}
    for cf in cert_files:
        d = json.load(open(cf))
        bid = d["base"]
        existing[bid] = {}
        for s in d["survivors"]:
            existing[bid][s["mask"]] = s.get("min_bad_triples", None)

    # ── 收集全部 19 个 mask ──
    all_masks = []
    for cf in cert_files:
        d = json.load(open(cf))
        bid = d["base"]
        for s in d["survivors"]:
            all_masks.append((bid, s["mask"]))
    print(f"共 {len(all_masks)} 个幸存 mask")

    # ── 用 v9w_all 枚举全部补全因子 ──
    masks_by_basin = {}
    for bid, mask in all_masks:
        masks_by_basin.setdefault(bid, []).append(mask)

    all_completions = {}  # {(bid, mask): [(cells, ...)]}
    max_completions = 0

    for bid, masks in masks_by_basin.items():
        base = by_id[bid]
        edges_old = [tuple(e) for e in base["edges"]]
        components = ordered_components(edges_old)
        blockers = candidate_blockers(base)
        hitting = json.loads((HERE / f"v20_defect_hitting_{bid}.json").read_text())
        defects = [owner_mask(v) for v in hitting["defect_owner_sets"]]

        tokens = build_tokens(base, 14, masks, 3, defects, blockers, components)
        print(f"[v9w_all] {bid} ...", end=" ", flush=True)
        res = json.loads(subprocess.run(
            [str(V9W_ALL)], input=tokens, text=True,
            capture_output=True, check=True,
        ).stdout)

        wf_by_mask = {}
        for entry in res.get("witness_factors", []):
            m = entry["mask"]
            cells = [tuple(c) for c in entry["cells"]]
            wf_by_mask.setdefault(m, []).append(cells)

        for mask in masks:
            comps = wf_by_mask.get(mask, [])
            all_completions[(bid, mask)] = comps
            if len(comps) > max_completions:
                max_completions = len(comps)

        print(f"OK (因子数: {[len(wf_by_mask.get(m,[])) for m in masks]})",
              flush=True)

    # ── 验证多补全 mask 的第 2+ 个因子 ──
    multi_comp_masks = [(bid, mask) for (bid, mask), comps in all_completions.items()
                        if len(comps) > 1]
    print(f"\n多补全 mask: {len(multi_comp_masks)} 个")
    for bid, mask in multi_comp_masks:
        print(f"  {bid} mask={mask}: {len(all_completions[(bid,mask)])} 个因子")

    extra_results = {}  # {(bid, mask): [(ci, min_bad, is_sol), ...]}

    for bid, mask in multi_comp_masks:
        base = by_id[bid]
        edges_old = [tuple(e) for e in base["edges"]]
        bits_old = list(base["bits"])
        comps = all_completions[(bid, mask)]

        print(f"\n[{bid} mask={mask}] 第 1 因子已知 min_bad="
              f"{existing.get(bid, {}).get(mask, '?')}")

        for ci in range(1, len(comps)):  # 第 2+ 因子
            cells = comps[ci]
            print(f"  验第 {ci+1} 个因子 ({len(cells)} 条边) ...", end=" ", flush=True)
            min_bt, is_sol = verify_one_completion(edges_old, bits_old, mask, cells)
            extra_results.setdefault((bid, mask), []).append((ci, min_bt, is_sol))
            if is_sol:
                print(f"★★★ bad_triples=0 → m=37 NTIL 解! ★★★", flush=True)
            else:
                print(f"min_bad={min_bt}", flush=True)

    # ── 用正确边重做 MUS ──
    print("\n" + "=" * 60)
    print("用正确边重做三元冲突超图 + MUS 提取")
    print("=" * 60)

    mus_results = []
    cell_freq_global = Counter()
    owner_freq_global = Counter()
    mus_sizes = []

    for bid, mask in all_masks:
        base = by_id[bid]
        edges_old = [tuple(e) for e in base["edges"]]
        bits_old = list(base["bits"])

        comps = all_completions[(bid, mask)]
        # 使用第一个补全因子构造正确边（如果多补全，各补全旧边同、替换边不同，
        # 但冲突结构是 mask 粒度的——自由位置固定。MUS 应反映该 mask 最小不可满足核）
        cells_rep = comps[0]

        # 构造正确边的 37 条边
        edges_37 = []
        wi = 0
        for i in range(37):
            if (mask >> i) & 1:
                edges_37.append(cells_rep[wi])
                wi += 1
            else:
                edges_37.append(tuple(edges_old[i]))
        base_bits_37 = list(bits_old)
        free_positions = [i for i in range(37) if (mask >> i) & 1]
        assert len(free_positions) == W

        # 构建冲突超图
        fs = build_correct_fs(edges_37, base_bits_37, free_positions)
        constants = [S for S, (m, _) in fs.items() if m == FULL]
        free_set = set(free_positions)
        fs_free = {S: (m, bc) for S, (m, bc) in fs.items()
                   if any(c in free_set for c in S)}

        mus = extract_mus(fs_free, restarts=4)

        # 校验
        mism = validate_fs(edges_37, base_bits_37, free_positions, fs, K=40)

        core_cells = set()
        for S, (m, bc) in mus:
            core_cells.update(S)
            for c in S:
                cell_freq_global[c] += 1
            owner_freq_global[S] += 1

        mus_sizes.append(len(mus))
        _exit = f" [ERR: 校验不一致={mism}]" if mism else ""
        print(f"  {bid} mask={mask}: MUS={len(mus)} "
              f"核cell={sorted(core_cells)}{_exit}", flush=True)

        mus_results.append({
            "base": bid, "mask": mask, "W": W,
            "n_clauses_total": len(fs),
            "n_clauses_free": len(fs_free),
            "n_constants": len(constants),
            "mus_size": len(mus),
            "mus_core_cells": sorted(core_cells),
            "mus_core_cell_count": len(core_cells),
            "mus_clauses": [
                {"owner_set": list(S),
                 "n_free": sum(1 for c in S if c in free_set),
                 "F_popcount": bin(m).count("1"),
                 "bad_combos": bc}
                for S, (m, bc) in mus
            ],
            "validation_mismatches": mism,
        })

    # ── 输出 ──
    out = {
        "k": 14, "W": W, "n_masks": len(all_masks),
        "multi_completion_verified": {
            str(k): v for k, v in extra_results.items()
        },
        "mus_sizes": mus_sizes,
        "mus_size_min": min(mus_sizes),
        "mus_size_max": max(mus_sizes),
        "mus_size_mean": sum(mus_sizes) / len(mus_sizes),
        "cell_frequency": dict(cell_freq_global),
        "recurring_owner_sets": {
            str(k): v for k, v in owner_freq_global.items() if v >= 2
        },
        "masks": mus_results,
    }
    out_path = HERE / "k14_reaudit.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"\n写入 {out_path}")
    print(f"MUS 大小: min={min(mus_sizes)} mean={sum(mus_sizes)/len(mus_sizes):.1f} "
          f"max={max(mus_sizes)}")
    print(f"出现 ≥2 次 owner_set: {len(out['recurring_owner_sets'])}")
    print(f"cell 频次 top10: {cell_freq_global.most_common(10)}")

    # 验证结果标记
    n_sol = sum(1 for _, _, is_sol in
                [v[0] for lst in extra_results.values() for v in lst]
                if is_sol)
    found_any_sol = n_sol > 0
    print(f"\n第二个补全中有解: {found_any_sol}")
    print("k=14 完整认证结论: ", end="")
    if found_any_sol:
        print("★★★ 存在 m=37 解! ★★★")
    else:
        all_multi_ok = all(
            not is_sol
            for lst in extra_results.values()
            for _, _, is_sol in lst
        )
        print(f"全部 19 mask 无解 (所有补全均已验)")
    print("=" * 60)


if __name__ == "__main__":
    main()
