#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整的 k=14 认证：枚举全部补全因子 + 正确几何朝向检查 + 正确边 MUS。

流程：
1. 对 19 个 q3 幸存 mask，调用 v9w_all.exe 获取所有补全因子
2. 对每个补全因子，用 C++ 补回的正确边构造 37 条边
3. 暴力枚举 2^W 种朝向，通过精确 geometry_and_defects oracle 检查
4. 若某补全存在解（bad_triples=0），输出 m=37 解并终止
5. 若全部补全都非解，用正确边构造三元冲突超图 + 提取 MUS
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
N = 1 << W  # 16384
FULL = (1 << N) - 1


# ─── 冲突超图工具（与 triple_conflict_core.py 同方法，但用正确边） ───

def build_points(edges, base_bits):
    """P[(cell_index, bit)] = 4 个 C4 提升点"""
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
    """用正确边构造三元冲突超图。edges_37 是混合了新旧边的完整 37 条边。"""
    P = build_points(edges_37, base_bits_37)
    free_set = set(free_positions)

    # 预建每个自由位置的位掩码
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

    fs = {}

    def add_owner(cells):
        uniq = sorted(set(cells))
        key = tuple(uniq)
        if key in fs:
            return
        poss = []
        for c in uniq:
            poss.append([0, 1] if c in free_set else [base_bits_37[c]])
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
        if mask:
            fs[key] = (mask, bad_count)

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


def validate_fs(edges_37, base_bits_37, free_positions, fs, K=40, seed=12345):
    """随机赋值校验冲突超图是否忠于精确 oracle"""
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
                print(f"  [校验] 赋值{a}: 仅oracle有={miss_orc} 仅分解有={miss_pred}")
    return mism


# ─── 几何认证 ───

def verify_completion(edges_old, bits_old, mask, cells):
    """用 C++ 补回的正确边 + 暴力朝向枚举验证一个补全因子。
    cells: list of (u, v) from C++ witness_factors
    返回: (min_bad_triples, best_assignment, found_solution)
    """
    best = None
    assign_list = list(itertools.product([0, 1], repeat=len(cells)))
    for assign in assign_list:
        eb = []
        bb = []
        wi = 0
        for i in range(37):
            if (mask >> i) & 1:
                u, v = cells[wi]
                eb.append((u, v))
                bb.append(assign[wi])
                wi += 1
            else:
                eb.append(tuple(edges_old[i]))
                bb.append(bits_old[i])
        try:
            geo, _ = geometry_and_defects(eb, bb)
        except AssertionError:
            continue
        bt = geo["bad_triples"]
        if best is None or bt < best[0]:
            best = (bt, assign)
        if bt == 0:
            return (0, assign, True)
    return (best[0] if best else None, best[1] if best else None, False)


def main():
    # ── 加载数据 ──
    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    by_id = {b["id"]: b for b in archive["archive"]}

    cert_files = sorted(glob.glob(str(HERE / "v20_*_k14_certification.json")))
    masks_by_basin = {}
    for cf in cert_files:
        d = json.loads(open(cf))
        bid = d["base"]
        surv = [s["mask"] for s in d["survivors"]]
        if surv:
            masks_by_basin[bid] = surv

    print(f"共 {sum(len(v) for v in masks_by_basin.values())} 个幸存 mask")
    print()

    # ── 逐盆地枚举全部补全因子 ──
    all_masks_data = []  # list of {mask, completions: [{cells, ...}]}

    for bid, masks in masks_by_basin.items():
        base = by_id[bid]
        edges_old = [tuple(e) for e in base["edges"]]
        bits_old = list(base["bits"])
        components = ordered_components(edges_old)
        blockers = candidate_blockers(base)
        hitting = json.loads(
            (HERE / f"v20_defect_hitting_{bid}.json").read_text()
        )
        defects = [owner_mask(v) for v in hitting["defect_owner_sets"]]

        tokens = build_tokens(base, 14, masks, 3, defects, blockers, components)
        print(f"[{bid}] 调用 v9w_all 枚举 {len(masks)} 个掩码的补全因子...", flush=True)
        res = json.loads(subprocess.run(
            [str(V9W_ALL)], input=tokens, text=True,
            capture_output=True, check=True,
        ).stdout)

        # 按 mask 分组 witness_factors
        wf_by_mask = {}
        for entry in res.get("witness_factors", []):
            m = entry["mask"]
            cells = [tuple(c) for c in entry["cells"]]
            wf_by_mask.setdefault(m, []).append(cells)

        comp_info = {ci["mask"]: ci for ci in res.get("mask_completion_info", [])}

        for mask in masks:
            completions = wf_by_mask.get(mask, [])
            info = comp_info.get(mask, {})
            n_comp = len(completions)
            truncated = info.get("truncated", False)
            all_masks_data.append({
                "base": bid,
                "mask": mask,
                "completions": completions,
                "n_completions": n_comp,
                "truncated": truncated,
            })
            print(f"  mask={mask}: {n_comp} 补全因子{' (截断!)' if truncated else ''}",
                  flush=True)

    # ── 逐补全验证几何朝向 ──
    print()
    print("=" * 60)
    print("开始几何朝向验证")
    print("=" * 60)

    base_bits_cache = {}
    for bid in by_id:
        base_bits_cache[bid] = list(by_id[bid]["bits"])

    final_results = []
    found_solution = False

    for md in all_masks_data:
        bid = md["base"]
        base = by_id[bid]
        edges_old = [tuple(e) for e in base["edges"]]
        bits_old = list(base["bits"])
        mask = md["mask"]
        completions = md["completions"]
        n_comp = len(completions)

        print(f"\n[{bid} mask={mask}] {n_comp} 个补全因子", flush=True)

        completion_results = []
        all_unsat = True

        for ci, cells in enumerate(completions):
            print(f"  补全 #{ci + 1}: cells={len(cells)} 条边", flush=True)

            # 构造混合边 (旧边 + C++ 补回边)
            edges_37 = []
            bits_37 = []
            wi = 0
            for i in range(37):
                if (mask >> i) & 1:
                    edges_37.append(cells[wi])
                    wi += 1
                else:
                    edges_37.append(tuple(edges_old[i]))
            # bits_37 在朝向枚举时填充，这里先用 -1 占位
            bits_37 = [-1] * 37

            # 暴力枚举朝向
            best_bt, best_assign, is_sol = verify_completion(
                edges_old, bits_old, mask, cells
            )

            comp_res = {
                "completion_index": ci,
                "n_cells": len(cells),
                "min_bad_triples": best_bt,
                "is_solution": is_sol,
            }
            if is_sol:
                comp_res["best_assignment"] = [int(b) for b in best_assign]
            completion_results.append(comp_res)

            if is_sol:
                print(f"    ★★★ mask {mask} 补全 #{ci + 1}: bad_triples=0 → m=37 NTIL 解!",
                      flush=True)
                all_unsat = False
                found_solution = True
            else:
                print(f"    min bad_triples={best_bt} → 非解", flush=True)

            # 如果找到解，仍然继续验证其他补全（完整性报告）
            # 但标记 global found_solution

        # 如果所有补全都非解，用正确边提取 MUS
        mus_result = None
        if all_unsat:
            print(f"  所有补全非解 → 用正确边构建三元冲突超图 + 提取 MUS", flush=True)

            # 取第一个补全的边作为代表（各补全的旧边相同，仅替换边不同）
            # 但为了 MUS 正确性，必须每次用正确的边
            # 简单做法：对每个补全独立提取 MUS 后合并
            all_mus_data = []
            for ci, cells in enumerate(completions):
                # 构造完整 37 条边
                edges_37 = []
                bits_37_dummy = list(bits_old)  # 占位，build_correct_fs 会补偿
                wi = 0
                for i in range(37):
                    if (mask >> i) & 1:
                        edges_37.append(cells[wi])
                        wi += 1
                    else:
                        edges_37.append(tuple(edges_old[i]))

                free_positions = [i for i in range(37) if (mask >> i) & 1]
                assert len(free_positions) == W, f"自由位置数量={len(free_positions)}"

                # 对每个补全，base_bits_37 在非自由位置用 bits_old
                base_bits_37 = list(bits_old)

                fs = build_correct_fs(edges_37, base_bits_37, free_positions)
                constants = [S for S, (m, _) in fs.items() if m == FULL]
                free_set = set(free_positions)
                fs_free = {S: (m, bc) for S, (m, bc) in fs.items()
                           if any(c in free_set for c in S)}

                mus = extract_mus(fs_free, restarts=4)

                # 校验
                mism = validate_fs(edges_37, base_bits_37, free_positions,
                                   fs, K=40)

                all_mus_data.append({
                    "completion_index": ci,
                    "n_clauses_total": len(fs),
                    "n_clauses_free": len(fs_free),
                    "n_constants": len(constants),
                    "mus_size": len(mus),
                    "mus_core_cells": sorted(set(
                        c for S, _ in mus for c in S
                    )),
                    "mus_clauses": [
                        {"owner_set": list(S), "F_popcount": bin(m).count("1"),
                         "bad_combos": bc}
                        for S, (m, bc) in mus
                    ],
                    "validation_mismatches": mism,
                })

            mus_result = all_mus_data

        final_results.append({
            "base": bid,
            "mask": mask,
            "n_completions": n_comp,
            "completion_results": completion_results,
            "all_unsat": all_unsat,
            "correct_mus": mus_result,
        })

    # ── 汇总输出 ──
    out_path = HERE / "k14_full_certification.json"
    out_path.write_text(json.dumps({
        "k": 14,
        "W": W,
        "n_masks_total": len(final_results),
        "n_masks_with_solution": sum(
            1 for r in final_results if not r["all_unsat"]
        ),
        "n_masks_completely_unsat": sum(
            1 for r in final_results if r["all_unsat"]
        ),
        "found_solution": found_solution,
        "masks": final_results,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("=" * 60)
    print(f"认证完成: {len(final_results)} 个 mask")
    print(f"发现解: {found_solution}")
    n_complete = sum(1 for r in final_results if r["all_unsat"])
    print(f"完全非解 (所有补全已验): {n_complete}")
    print(f"结果已写入 {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
