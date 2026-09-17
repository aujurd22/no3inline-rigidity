#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""等价快速 3-CNF 构建器（2026-07-21）。

与 exact_rot4_3sat.build_full_3cnf **严格等价**（子句集相同，仅去重）：
原版对 37³×8≈1.15M 个 (cell,bit) 三元组逐个调 combo_bad；
本版先建全部 296 个提升点（每 cell × 2 bit × 4 旋转），用 O(296²)
点共线（line_key）找共线三点组，反推 (cell,bit) 三元组加子句。
combo_bad(P,[(p,a),(q,b),(k,c)])=True ⟺ 存在一点组 (∈P[(p,a)]×P[(q,b)]×P[(k,c)])
共线 ⟺ 本版点共线法命中同一三元组。故子句集完全等价。

提速约 100×，用于高通量扫描。
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from prepare_v20_basin_archive import c4_lifts, directed_cells, line_key  # noqa: E402
import exact_rot4_3sat as _E  # 仅在快速路径遇重合点异常时回退（保证 sound）


def fast_build_3cnf(edges_37):
    """返回 (clauses, nvars)，clauses 为 list[list[int]]，与 build_full_3cnf 等价。"""
    n = len(edges_37)
    # 建全部 296 个提升点，打 (cell, bit) 标签
    all_pts = []          # 点坐标
    tags = []             # (cell, bit)
    for i, (u, v) in enumerate(edges_37):
        for b in (0, 1):
            cell_dir = directed_cells([(u, v)], [b])[0]
            for pt in c4_lifts(cell_dir):
                all_pts.append(pt)
                tags.append((i, b))
    # O(points^2) 点共线
    line_members = {}
    np_ = len(all_pts)
    try:
        for i in range(np_):
            for j in range(i + 1, np_):
                key = line_key(all_pts[i], all_pts[j])
                if key is None:
                    continue
                line_members.setdefault(key, []).append(i)
                line_members[key].append(j)
    except ValueError:
        # 重合点（如盆地特例）：回退到 sound 原式，保证不丢子句
        return _E.build_full_3cnf(edges_37)
    clause_set = set()
    for members in line_members.values():
        if len(members) < 3:
            continue
        for i, j, k in itertools.combinations(members, 3):
            ci, ai = tags[i]
            cj, aj = tags[j]
            ck, ak = tags[k]
            if ci == cj or ci == ck or cj == ck:
                continue  # 仅编码 3 互异 cell
            lits = frozenset([(2 * ci + ai) ^ 1,
                              (2 * cj + aj) ^ 1,
                              (2 * ck + ak) ^ 1])
            clause_set.add(lits)
    clauses = [list(c) for c in clause_set]
    return clauses, n


def verify_equivalence(edges_37, build_full_3cnf):
    """验证 fast 与原始构建器子句集一致（忽略重复子句与顺序）。"""
    fc, fn = fast_build_3cnf(edges_37)
    oc, on = build_full_3cnf(edges_37)
    fset = set(frozenset(c) for c in fc)
    oset = set(frozenset(c) for c in oc)
    ok = (fset == oset) and (fn == on)
    return ok, len(fc), len(oc), len(fset), len(oset)


if __name__ == "__main__":
    import random
    import time
    from scan_new_basins import random_2factor
    import exact_rot4_3sat as E

    rng = random.Random(123)
    print("=== 等价性验证（20 个随机 2-因子）===")
    all_ok = True
    for t in range(20):
        e = random_2factor(rng)
        ok, lf, lo, sf, so = verify_equivalence(e, E.build_full_3cnf)
        if not ok:
            all_ok = False
            print(f"  ✗ 第{t}个不一致: fast={lf}(去重{sf}) orig={lo}(去重{so})")
        else:
            print(f"  ✓ 第{t}个: fast={lf}(去重{sf}) orig={lo}(去重{so})")
    print("等价性:", "全部一致" if all_ok else "存在不一致！")

    print("\n=== 速度对比（同 20 个）===")
    tt = []; tf = []
    for t in range(20):
        e = random_2factor(rng)
        t0 = time.time(); E.build_full_3cnf(e); tt.append(time.time() - t0)
        t0 = time.time(); fast_build_3cnf(e); tf.append(time.time() - t0)
    print(f"原始 build 均值={sum(tt)/20:.4f}s")
    print(f"快速 build 均值={sum(tf)/20:.4f}s  提速={sum(tt)/20/ (sum(tf)/20):.1f}x")
