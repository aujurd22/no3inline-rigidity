#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Benders 主问题：在全局无向 2-因子空间生成候选，并管理割约束。

主问题职责：
  - 生成候选 2-因子（复用 scan_new_basins.random_2factor：37 顶点 2-正则图，
    每条边是 (u,v)∈{0..36}²，正是 rot4 多重图模型所需的 cell 表示）。
  - 计算候选到六 V20 盆地的「边集对称差距离」，优先选取远离已知盆地的候选
    （用户 2026-07-21 指令：把重心从局部盆地移到全局无向 2-因子空间）。
  - 维护割集（已判定 UNSAT 的 2-因子边集），避免重复判定。

注意：本主问题当前用随机 2-因子生成器作第一版候选源；系统性候选源
（如 rot4_multigraph_factor_multicycle_exhaustive*.exe 的结构化枚举、或
2-边开关在已知盆地上的有偏游走）为后续增强，不改变本模块的接口。

[COMPUTATIONAL CERTIFICATE / 框架]，非定理。m=37 存在性仍 OPEN。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys_path = HERE
import sys
sys.path.insert(0, str(HERE))

from scan_new_basins import random_2factor, compute_defects  # noqa: E402


def load_basins(archive_path=None):
    """返回 [(id, frozenset_of_edges)]，edges 为无序对 tuple。"""
    if archive_path is None:
        archive_path = HERE / "v20_basin_archive.json"
    arch = json.loads(Path(archive_path).read_text())
    out = []
    for b in arch["archive"]:
        es = frozenset((min(u, v), max(u, v)) for u, v in b["edges"])
        out.append((b["id"], es))
    return out


def candidate_edge_set(edges):
    return frozenset((min(u, v), max(u, v)) for u, v in edges)


def candidate_distance(edges, basins):
    """到六盆地的最小边集对称差大小（越小越接近某盆地）。"""
    es = candidate_edge_set(edges)
    return min(len(es ^ bset) for _bid, bset in basins)


def generate_candidates(n, rng, basins, cut_set, min_distance=0,
                        max_invalid_skip=2000):
    """生成至多 n 个「合法 + 不在割集 + 距离≥min_distance」的候选 2-因子。

    返回 list[(edges, distance)]。max_invalid_skip 限制为找合法候选而跳过的非法尝试上限。
    """
    out = []
    seen = set()
    invalid_skipped = 0
    attempts = 0
    while len(out) < n and invalid_skipped < max_invalid_skip:
        attempts += 1
        edges = random_2factor(rng)
        key = candidate_edge_set(edges)
        if key in seen or key in cut_set:
            continue
        # 合法性：须产生 148 互异提升点（由子问题 is_valid_rot4_factor 严格判定，
        # 此处用轻量预筛：边集本身合法即可，严格性交给子问题）。
        dist = candidate_distance(edges, basins)
        if dist < min_distance:
            continue
        seen.add(key)
        out.append((edges, dist))
    return out, attempts, invalid_skipped


def enumerate_2factor_switches(edges):
    """枚举一幅 2-因子所有合法「一步 2-边开关」邻域（保持 2-正则，禁重边/自环/2-圈）。

    开关：移除两条边 (a,b),(c,d)（a,b,c,d 互异），加 (a,c),(b,d)；须不产生重边/自环。
    返回去重后的边集列表（每条为排序后的无序对 list）。
    """
    eset = set((min(u, v), max(u, v)) for u, v in edges)
    edges_list = sorted(eset)
    n = len(edges_list)
    out = []
    seen = set()
    for i in range(n):
        a, b = edges_list[i]
        for j in range(i + 1, n):
            c, d = edges_list[j]
            if len({a, b, c, d}) != 4:
                continue
            n1 = (min(a, c), max(a, c))
            n2 = (min(b, d), max(b, d))
            if n1 in eset or n2 in eset:
                continue
            if a == c or b == d:
                continue
            new_set = set(eset)
            new_set.discard((a, b))
            new_set.discard((c, d))
            new_set.add(n1)
            new_set.add(n2)
            deg = {}
            ok = True
            for u, v in new_set:
                deg[u] = deg.get(u, 0) + 1
                deg[v] = deg.get(v, 0) + 1
            if len(new_set) != len(eset) or any(d2 != 2 for d2 in deg.values()):
                continue
            key = frozenset(new_set)
            if key in seen:
                continue
            seen.add(key)
            out.append(sorted(new_set))
    return out


def generate_switch_neighbors(basins, cut_set, margin=25, max_per_basin=200,
                              rng=None, min_distance=0):
    """结构化候选源：枚举六盆地的一步 2-边开关邻域（近盆地低缺陷区）。

    仅保留 defect(bad_triples) ≤ 起点+margin 的邻域，并剔除已在割集者。
    distance 取该邻域到六盆地的最小对称差（近盆地故小，用于记录，不用于过滤）。
    返回 list[(edges, distance)]。
    """
    out = []
    for _bid, bset in basins:
        edges = sorted(bset)
        start_bad, _ = compute_defects(edges)
        nbrs = enumerate_2factor_switches(edges)
        scored = []
        for ne in nbrs:
            key = candidate_edge_set(ne)
            if key in cut_set:
                continue
            bad, _orb = compute_defects(ne)
            if bad is None:
                continue
            if bad <= start_bad + margin:
                scored.append((bad, ne))
        scored.sort(key=lambda t: t[0])
        for bad, ne in scored[:max_per_basin]:
            out.append((ne, candidate_distance(ne, basins)))
    return out


if __name__ == "__main__":
    basins = load_basins()
    print(f"已载入 {len(basins)} 个 V20 盆地边集")
    rng = random.Random(20260721)
    cands, att, inv = generate_candidates(5, rng, basins, set(), min_distance=0)
    for edges, d in cands:
        print(f"  候选: 边数={len(edges)} 到盆地最小距离={d}")
    print(f"（生成尝试 {att} 次）")
