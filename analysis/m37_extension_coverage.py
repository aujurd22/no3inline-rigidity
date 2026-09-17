# -*- coding: utf-8 -*-
"""
m37_extension_coverage.py — 直接检验 README 第 468 行的开放问题：
  "m=37 新增的第 37 对，引入 +560 条新 forbidden lines，是否正好覆盖
   +73 个新网格位置，使整个系统仍有解？"

做法（纯 NumPy 向量化，低 CPU）：
  1. [方法验证] 在 m=36 框架下，对 m=36 已知解的某个 pair，固定其余 35 对，
     测其 effective forbidden coverage —— 应等于 36²−1 = 1295（完全确定原理）。
     这复现 measure_forbidden_lines.py 的结论，确认本脚本方法正确。
  2. [扩展测试] 在 m=37 框架下，把 36 个已知解 cell 固定，枚举第 37 对的所有
     37²=1369 个候选位置，测哪些位置被 16×C(36,2) 个 forbidden lines 排除。
     - coverage = 1369（safe=0）→ 第 37 对无处可放 → 该 m=36 解无法扩展，指向 impossible。
     - coverage = 1368（safe=1）→ 与 m=5..36 模式一致，系统零维但留 1 候选位，不能证否。
     - coverage 显著更低 → 系统远未压死。

注意：这是"固定其他 36 对"的必要条件测试（第 37 对取某位会与固定对共线则不可）。
它直接量化 m=37 的 over-determined 程度，是方向2（不可能性/通用性）的一个具体数值探针。
"""
import os, sys, itertools, json
import numpy as np

ANALYSIS = r'D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3inline-rigidity\analysis'
sys.path.insert(0, ANALYSIS)
import rot4_loader as rot4

def rotation_coords(cx, cy, r, N):
    if r == 0:
        return (cx, cy)
    elif r == 1:
        return (N - 1 - cy, cx)
    elif r == 2:
        return (N - 1 - cx, N - 1 - cy)
    elif r == 3:
        return (cy, N - 1 - cx)

def rotation_linear(r, m, N):
    # P1 = rotation_coords(m-alpha, m-beta, r, N) 展开为 (c0 + ca*alpha + cb*beta, d0 + da*alpha + db*beta)
    if r == 0:
        return (m, -1, 0, m, 0, -1)        # (m-alpha, m-beta)
    elif r == 1:
        return (m - 1, 0, 1, m, -1, 0)     # (m-1+beta, m-alpha)
    elif r == 2:
        return (m - 1, 1, 0, m - 1, 1, 0)  # (m-1+alpha, m-1+beta)
    elif r == 3:
        return (m, 0, -1, m - 1, 1, 0)     # (m-beta, m-1+alpha)

CANONICAL_ROTS = [(r1, r2, r3) for r1 in range(4) for r2 in range(4) for r3 in range(4)]

def _forbidden_set(cells_fixed, m, target_is_fixed_pair=True, target_idx=None):
    """返回被禁止的 (alpha,beta) 位置集合（1..m 网格）。
    target_is_fixed_pair=True：target 是 cells_fixed[target_idx]，跳过它自身（测其他对对该对的约束）。
    target_is_fixed_pair=False：target 是第 37 个自由候选，枚举全网格。
    """
    N = 2 * m
    alpha = np.arange(1, m + 1, dtype=np.int64)
    beta = np.arange(1, m + 1, dtype=np.int64)
    AV, BV = np.meshgrid(alpha, beta, indexing='ij')
    forbidden = set()
    if target_is_fixed_pair:
        other = [i for i in range(len(cells_fixed)) if i != target_idx]
    else:
        other = list(range(len(cells_fixed)))
    for j, k in itertools.combinations(other, 2):
        cj, ck = cells_fixed[j], cells_fixed[k]
        for r1, r2, r3 in CANONICAL_ROTS:
            P2 = rotation_coords(cj[0], cj[1], r2, N)
            P3 = rotation_coords(ck[0], ck[1], r3, N)
            px0, pxa, pxb, py0, pya, pyb = rotation_linear(r1, m, N)
            P1x = px0 + pxa * AV + pxb * BV
            P1y = py0 + pya * AV + pyb * BV
            det = (P2[0] - P1x) * (P3[1] - P1y) - (P3[0] - P1x) * (P2[1] - P1y)
            az, bz = np.where(det == 0)
            for a, b in zip(az.tolist(), bz.tolist()):
                forbidden.add((a + 1, b + 1))
    return forbidden

def coverage_fixed_base_rotation(cells_fixed, m):
    """固定 36 个基 cell 的真实旋转（r2=r3=0，即基位置本身），
    只让第 37 对的位置 (alpha,beta) 与旋转 r1 自由。
    返回被禁止的 (alpha,beta,r1) 集合——这等价于在真实解的旋转框架下，
    测第 37 对能否找到一个不共线的放置（R8-CSP 一阶必要条件）。
    若 safe>0，则该 m=36 基底可扩展（一阶），不能证否；若 safe=0，则该基底压死。
    """
    N = 2 * m
    alpha = np.arange(1, m + 1, dtype=np.int64)
    beta = np.arange(1, m + 1, dtype=np.int64)
    AV, BV = np.meshgrid(alpha, beta, indexing='ij')
    forbidden = set()
    for j, k in itertools.combinations(range(len(cells_fixed)), 2):
        cj, ck = cells_fixed[j], cells_fixed[k]
        # 固定 r2=r3=0
        P2 = rotation_coords(cj[0], cj[1], 0, N)
        P3 = rotation_coords(ck[0], ck[1], 0, N)
        for r1 in range(4):
            px0, pxa, pxb, py0, pya, pyb = rotation_linear(r1, m, N)
            P1x = px0 + pxa * AV + pxb * BV
            P1y = py0 + pya * AV + pyb * BV
            det = (P2[0] - P1x) * (P3[1] - P1y) - (P3[0] - P1x) * (P2[1] - P1y)
            az, bz = np.where(det == 0)
            for a, b in zip(az.tolist(), bz.tolist()):
                forbidden.add((a + 1, b + 1, r1))
    return forbidden

def main():
    m0 = 36
    sols, ext = rot4.load_rot4(2 * m0)
    print(f"m=36 解可用数: {len(sols)} (格式 {ext})")
    pts = sols[0]
    pairs = [(2 * (m0 - x) - 1, 2 * (m0 - y) - 1) for (x, y) in pts if x < m0 and y < m0]
    assert len(pairs) == m0, f"pair 数 {len(pairs)} != {m0}"
    cells_36 = [(m0 - (a + 1) // 2, m0 - (b + 1) // 2) for (a, b) in pairs]
    print(f"提取 cells_36 数: {len(cells_36)}")

    # ---- [1] 方法验证：m=36 框架下 pair0 的 coverage 应 = 1295 ----
    cov36 = _forbidden_set(cells_36, m0, target_is_fixed_pair=True, target_idx=0)
    print(f"[验证] m=36 pair0 coverage = {len(cov36)} / {m0*m0} (期望 {m0*m0-1})")

    # ---- [2] 扩展测试：m=37 框架下第 37 对的 coverage（固定位置、枚举全部 64 旋转）----
    m = 37
    cov37 = _forbidden_set(cells_36, m, target_is_fixed_pair=False)
    grid = m * m
    safe = grid - len(cov37)
    print(f"[扩展·全旋转] m=37 第37对 coverage = {len(cov37)} / {grid} (与 m=36 的 {m0*m0} 全禁同构，无区分力)")

    # ---- [3] 正确扩展测试：固定 36 对真实旋转(r=0)，第 37 对位置+旋转自由 ----
    cov37_fixed = coverage_fixed_base_rotation(cells_36, m)
    total_candidates = grid * 4  # 37² 位置 × 4 旋转
    safe_fixed = total_candidates - len(cov37_fixed)
    print(f"[扩展·固定基旋转] m=37 第37对候选 (位置×旋转) = {total_candidates}")
    print(f"[扩展·固定基旋转] 被禁候选数 = {len(cov37_fixed)}")
    print(f"[扩展·固定基旋转] 安全候选数 (safe) = {safe_fixed}")

    result = {
        "m_target": m,
        "base": "m=36 known solution (n72_rot4.few, Heule 2026-06-25)",
        "method_check_m36_pair0_coverage_incl_actual": len(cov36),
        "method_check_m36_pair0_coverage_excl_actual": len(cov36) - 1,
        "method_check_expect_excl_actual": m0 * m0 - 1,
        "m37_37th_pair_coverage_all_rot_incl_self": len(cov37),
        "m37_grid_positions": grid,
        "m37_coverage_all_rot_note": "与m=36全禁同构(含候选自身被禁)，无区分力，不能据此外推压死",
        "m37_fixed_base_rotation_total_candidates": total_candidates,
        "m37_fixed_base_rotation_forbidden": len(cov37_fixed),
        "m37_fixed_base_rotation_safe": safe_fixed,
        "interpretation": (
            "固定36对真实旋转(r=0)后，第37对仍有 safe 个(位置×旋转)候选不共线=>该m=36基底可一阶扩展，不能证否m=37；"
            "若 safe=0=>该基底压死，指向impossible。此测试仅单一基底、必要非充分。"
        ),
    }
    out = os.path.join(ANALYSIS, 'results', 'm37_extension_coverage.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {out}")

if __name__ == '__main__':
    main()
