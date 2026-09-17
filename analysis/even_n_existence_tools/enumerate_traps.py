#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""几何朝向陷阱枚举与真实 D4 对称归类（第一优先：几何朝向陷阱定理）。

修正记录（2026-07-21，针对用户指出的 4 个实现 bug）：
  bug1 二元对称：旧版只建 bin_by_pa[(p,a)]（第一位置），漏掉强制中心出现在二元子句
        第二位置的陷阱。本版用对称 forbid 映射（每条 ¬(x_p=a∧x_q=b) 同时登记
        (p,a)→(q,b) 与 (q,b)→(p,a)），强制中心在任一位置都能捕获。
  bug2 槽位↔cell：p,q 是 0..k-1 的自由变量槽位，旧版直接当 cell 索引访问 edges_37，
        几何错位。本版统一经 free_positions[slot] 转成真实 cell 索引。
  bug3 伪 D4：旧版 range(8) 但反射分支 `if k&8` 恒 0（k≤7），只有 C4。本版显式 8 个
        平面等距（4 旋转 + 4 反射），平移 A 到原点后取字典序最小配置作规范形。
  bug4 见证直线：旧版只用 cell 向量算直线方向。本版按赋值 (a=s,b=t) 用 build_points
        重建，定位真正共线的 3 个 C4 lift 点（实际几何见证）。

陷阱定义 T(a, b; s)（用户 2026-07-20 晚，2026-07-21 精确口径）：
  1. 一元力把中心新边 a（槽位，转 cell 后）强制为朝向 s；
  2. 给定 a=s，一条几何见证禁止 b=0；
  3. 另一几何见证禁止 b=1；
  → b 在 a=s 下无合法朝向，矛盾。
  对每个不同的有序三元组 T(a,b;s) 计一个陷阱（不要求 b 自由；b 是否一元强制不影响计数）。
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path

from reaudit_k14 import build_points, collinear
from scc_prescreen import build_correct_fs, extract_unary_binary

HERE = Path(__file__).resolve().parent

# ───────────────────────── 几何基元 ─────────────────────────

def cell_directed_point(edges_37, bits_37, free_set, cell_idx, orientation):
    """cell_idx（0..36 真实单元格索引）在给定 orientation 下的定向网格点 (x,y)。"""
    u, v = edges_37[cell_idx]
    bit = orientation if cell_idx in free_set else bits_37[cell_idx]
    return (v, u) if bit else (u, v)


def vec_shell(x, y):
    """cell 向量 (x,y) 的方向壳：由 L∞ 模粗分；SELF 即 (0,0) 环。"""
    if x == 0 and y == 0:
        return "SELF"
    m = max(abs(x), abs(y))
    if m <= 8:
        return "SHORT"
    if m <= 20:
        return "MEDIUM"
    return "LONG"


def line_orbit(p, q):
    """过 p,q 直线方向的轨道代表（斜率类型，平移不变，已含反射对称）。"""
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    if dx == 0 and dy == 0:
        return (0, 0)
    g = __import__("math").gcd(abs(dx), abs(dy)) or 1
    a, b = dy // g, dx // g
    cands = {(abs(a), abs(b)), (abs(b), abs(a)),
             (abs(a), -abs(b)), (abs(b), -abs(a))}
    return min(cands)


# ───────────────────────── 真正 D4（8 个平面等距） ─────────────────────────

D4 = [
    lambda x, y: (x, y),       # 恒等
    lambda x, y: (-y, x),      # 旋转 90°
    lambda x, y: (-x, -y),     # 旋转 180°
    lambda x, y: (y, -x),      # 旋转 270°
    lambda x, y: (x, -y),      # 反射 x 轴
    lambda x, y: (-x, y),      # 反射 y 轴
    lambda x, y: (y, x),       # 反射 对角线 y=x
    lambda x, y: (-y, -x),     # 反射 对角线 y=-x
]


def config_signature(points):
    """points: list[(role, (x,y))]；平移使 'A' 点到原点，对 8 个 D4 对称取字典序最小配置。
    返回不可变签名（真实 D4 几何模板标识）。"""
    a_items = [(role, p) for role, p in points if role == 'A']
    if not a_items:
        return None
    base = a_items[0][1]
    best = None
    for g in D4:
        items = []
        for role, p in points:
            rp = g(p[0] - base[0], p[1] - base[1])
            items.append((role, rp))
        items.sort()
        key = tuple(items)
        if best is None or key < best:
            best = key
    return best


# ───────────────────────── 真实共线 lift 见证 ─────────────────────────

def find_collinear_lift_points(P, cells_bits):
    """cells_bits = [(cell_index, bit), ...]（2 或 3 个胞）。返回真正共线的 3 个 lift 点，
    或 None。与 reaudit_k14.combo_bad 判定一致（3 胞：各取一个 lift；2 胞：同胞两 lift
    与他胞一 lift 共线）。"""
    n = len(cells_bits)
    pts = [P[(c, b)] for (c, b) in cells_bits]
    if n == 3:
        A, B, C = pts
        for a in A:
            for b in B:
                for c in C:
                    if collinear(a, b, c):
                        return [list(a), list(b), list(c)]
        return None
    if n == 2:
        A, B = pts
        for a1, a2 in itertools.combinations(A, 2):
            for b in B:
                if collinear(a1, a2, b):
                    return [list(a1), list(a2), list(b)]
        for b1, b2 in itertools.combinations(B, 2):
            for a in A:
                if collinear(a, b1, b2):
                    return [list(a), list(b1), list(b2)]
        return None
    # n == 1
    A = pts[0]
    for a1, a2, a3 in itertools.combinations(A, 3):
        if collinear(a1, a2, a3):
            return [list(a1), list(a2), list(a3)]
    return None


# ───────────────────────── 陷阱枚举 ─────────────────────────

def enumerate_traps_for_completion(edges_37, bits_37, free_positions):
    edges_37 = [tuple(e) for e in edges_37]
    bits_37 = list(bits_37)
    free_positions = list(free_positions)
    free_set = set(free_positions)
    fs = build_correct_fs(edges_37, bits_37, free_positions)
    unary, _unary_contra, binary = extract_unary_binary(fs, free_set)

    # P：cell_index×bit → 4 个 C4 lift 点（用于重建真实共线见证）
    P = build_points(edges_37, bits_37)

    # 一元力去重：同一 (槽位, 值) 只留一次（多条见证产生重复一元力，否则陷阱重复计数）
    unary_dedup = {}
    for (p, s, o) in unary:
        unary_dedup.setdefault((p, s), o)
    unary_forced_val = {p: s for (p, s) in unary_dedup}  # 槽位 → 被强制的值

    # 对称 forbid 映射：每条二元子句 ¬(x_p=a ∧ x_q=b) 同时登记两个方向
    #   (p,a) 禁止 (q,b) 且 (q,b) 禁止 (p,a)
    forbid = defaultdict(list)  # (slot, val) -> list[(other_slot, other_val, owner_set)]
    # 同时保留反向索引以便取 owner_set 重建见证
    binary_lookup = {}  # ((p,a,q,b)) -> owner_set （两个方向都存）
    for (p, a, q, b, owner) in binary:
        forbid[(p, a)].append((q, b, owner))
        forbid[(q, b)].append((p, a, owner))
        binary_lookup[(p, a, q, b)] = owner
        binary_lookup[(q, b, p, a)] = owner

    def old_points_from_triples(owner_sets, exclude_cells):
        """从一组 cell-三元组 owner_set 中取出旧边（非自由、非排除）的定向点。"""
        pts = []
        seen_triples = set()
        for ow in owner_sets:
            key = tuple(ow)
            if key in seen_triples:
                continue
            seen_triples.add(key)
            for c in ow:
                if c in free_set or c in exclude_cells:
                    continue
                pts.append(cell_directed_point(edges_37, bits_37, free_set, c, bits_37[c]))
        return pts

    traps = []
    for (a_slot, s), uowner in unary_dedup.items():
        # a 的所有被禁止的 (其他槽位, 值)
        banned = forbid.get((a_slot, s), [])
        by_b = defaultdict(lambda: {'0': [], '1': []})  # other_slot -> {'0':[owner], '1':[owner]}
        for (b_slot, t, owner) in banned:
            by_b[b_slot][str(t)].append(tuple(owner))
        for b_slot, d in by_b.items():
            if d['0'] and d['1']:
                # 真实 cell 映射
                cell_a = free_positions[a_slot]
                cell_b = free_positions[b_slot]
                a_s = cell_directed_point(edges_37, bits_37, free_set, cell_a, s)
                b0 = cell_directed_point(edges_37, bits_37, free_set, cell_b, 0)
                b1 = cell_directed_point(edges_37, bits_37, free_set, cell_b, 1)
                a_shell = vec_shell(*a_s)
                b_shell = vec_shell(*b0)

                # 两条二元见证的旧边支撑 + 真实共线 lift 点
                W0 = old_points_from_triples(d['0'], {cell_a, cell_b})
                W1 = old_points_from_triples(d['1'], {cell_a, cell_b})
                # 一元力旧边支撑（中心 a 被强制的见证）
                F_pts = old_points_from_triples([uowner], {cell_a})

                # 重建真实共线 lift 见证
                lift0 = None
                lift1 = None
                own0 = binary_lookup.get((a_slot, s, b_slot, 0))
                own1 = binary_lookup.get((a_slot, s, b_slot, 1))
                if own0 is not None:
                    # own0 本身是单个 cell-三元组（含两自由胞 + 1 旧胞）
                    cb = []
                    for c in own0:
                        if c == cell_a:
                            cb.append((c, s))
                        elif c == cell_b:
                            cb.append((c, 0))
                        else:
                            cb.append((c, bits_37[c]))
                    lift0 = find_collinear_lift_points(P, cb)
                if own1 is not None:
                    cb = []
                    for c in own1:
                        if c == cell_a:
                            cb.append((c, s))
                        elif c == cell_b:
                            cb.append((c, 1))
                        else:
                            cb.append((c, bits_37[c]))
                    lift1 = find_collinear_lift_points(P, cb)

                witness_line = line_orbit(a_s, b0)
                force_line = line_orbit(a_s, F_pts[0]) if F_pts else (0, 0)

                # 几何配置（含 A/B0/B1/两条二元见证旧边/一元力旧边），用于 D4 分类
                pts = [('A', a_s), ('B0', b0), ('B1', b1)]
                for wp in W0:
                    pts.append(('W0', wp))
                for wp in W1:
                    pts.append(('W1', wp))
                for fp in F_pts:
                    pts.append(('F', fp))
                sig = config_signature(pts)
                # 本质签名：只含 A/B0/B1 定向点（忽略具体旧边支撑），检验 a-b 几何能否压缩
                sig_essential = config_signature([('A', a_s), ('B0', b0), ('B1', b1)])

                traps.append({
                    "a_slot": a_slot, "b_slot": b_slot, "s": s,
                    "a_cell": cell_a, "b_cell": cell_b,
                    "a_directed": list(a_s), "b_directed_0": list(b0), "b_directed_1": list(b1),
                    "a_shell": a_shell, "b_shell": b_shell,
                    "witness_line_orbit": list(witness_line),
                    "force_line_orbit": list(force_line),
                    "unary_old_support": [list(p) for p in F_pts],
                    "binary_old_support_0": [list(p) for p in W0],
                    "binary_old_support_1": [list(p) for p in W1],
                    "witness_lift_points_0": lift0,
                    "witness_lift_points_1": lift1,
                    "n_witness_old_0": len(W0),
                    "n_witness_old_1": len(W1),
                    "b_forced_val": unary_forced_val.get(b_slot),  # None=自由；否则被一元强制的朝向
                    "geo_signature": [list(x) for x in sig] if sig else None,
                    "geo_signature_essential": [list(x) for x in sig_essential] if sig_essential else None,
                })
    return traps


def main():
    for tag, fname in [("k14", "all_completions_kernelized.json"),
                       ("k15", "all_completions_k15_kernelized.json")]:
        data = json.loads((HERE / fname).read_text())
        completions = data["completions"]
        all_traps = []
        per_comp_counts = []
        for c in completions:
            tr = enumerate_traps_for_completion(c["edges_37"], c["bits_37"], c["free_positions"])
            per_comp_counts.append(len(tr))
            for t in tr:
                t["bid"] = c["bid"]
                t["mask"] = c["mask"]
                t["comp_idx"] = c["comp_idx"]
            all_traps.extend(tr)

        # 细粒度真实 D4 几何模板（含定向点坐标 + 角色）
        templates = defaultdict(list)
        for t in all_traps:
            key = tuple(map(tuple, t["geo_signature"])) if t["geo_signature"] else ("__NONE__",)
            templates[key].append(t)
        # 本质 D4 几何模板（只含 A/B0/B1 定向点，忽略旧边支撑）
        templates_ess = defaultdict(list)
        for t in all_traps:
            key = tuple(map(tuple, t["geo_signature_essential"])) if t["geo_signature_essential"] else ("__NONE__",)
            templates_ess[key].append(t)
        # 粗粒度结构模板（仅壳 + 直线轨道 + 支撑数）
        coarse = defaultdict(list)
        for t in all_traps:
            key = (t["a_shell"], t["b_shell"], tuple(t["witness_line_orbit"]),
                   tuple(t["force_line_orbit"]), len(t["binary_old_support_0"]) + len(t["binary_old_support_1"]),
                   len(t["unary_old_support"]))
            coarse[key].append(t)
        # 真实共线 lift 见证点空值计数（应全非 None）
        null_witness = sum(1 for t in all_traps
                           if t["witness_lift_points_0"] is None or t["witness_lift_points_1"] is None)

        n = len(per_comp_counts)
        total = len(all_traps)
        mean = total / n if n else 0
        print(f"\n===== {tag} =====")
        print(f"补全数={n}  陷阱总数={total}  (每补全均值={mean:.4f})")
        print(f"每补全陷阱数: {per_comp_counts}")
        print(f"min={min(per_comp_counts)} max={max(per_comp_counts)} mean={total/n:.4f} "
              f"中位={sorted(per_comp_counts)[n//2]}")
        print(f"真实 D4 几何模板数(细,含定向点+旧边支撑)={len(templates)}")
        print(f"真实 D4 几何模板数(本质,仅 A/B0/B1 定向)={len(templates_ess)}")
        print(f"粗结构模板数(壳+线轨+支撑数)={len(coarse)}")
        print(f"真实共线 lift 见证点为空的陷阱数={null_witness} (应=0)")
        for i, (sig, members) in enumerate(sorted(templates.items(), key=lambda kv: -len(kv[1]))[:8]):
            m0 = members[0]
            print(f"  细模板#{i+1} (成员={len(members)}): a壳={m0['a_shell']} b壳={m0['b_shell']} "
                  f"见证线轨={m0['witness_line_orbit']} 力线轨={m0['force_line_orbit']} "
                  f"| 例 a_slot={m0['a_slot']}(cell{m0['a_cell']}) b_slot={m0['b_slot']}(cell{m0['b_cell']}) "
                  f"s={m0['s']} bid={m0['bid']}")
        out = {"tag": tag, "n_completions": n, "n_traps": total,
               "per_completion_counts": per_comp_counts,
               "n_templates_fine": len(templates),
               "n_templates_essential": len(templates_ess),
               "n_templates_coarse": len(coarse),
               "null_witness_count": null_witness,
               "traps": all_traps}
        (HERE / f"traps_{tag}.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"写入 traps_{tag}.json")
        # 验证 k=14 总数应为 134
        if tag == "k14":
            ok = (total == 134)
            print(f"[校验] k=14 陷阱总数 = {total}  {'✓=134' if ok else '✗≠134（期望134）'}")


if __name__ == "__main__":
    main()
