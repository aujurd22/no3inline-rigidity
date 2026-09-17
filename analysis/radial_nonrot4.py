#!/usr/bin/env python3
"""
radial_nonrot4.py -- 非 rot4 解的径向层观察（对比 rot4）

数据源: flammenkamp_cache/n{n}_{symm}（Flammenkamp 全对称类真实解）。
每个配置 = n×n 棋盘上 2n 个点（每行 2 点），decode_line 统一解码。

环定义（与 analyze_rot4.ring 一致，整数化）:
  ring_key(p) = (2*px-(n-1))^2 + (2*py-(n-1))^2   # = 4 * 到中心欧氏距离^2
  这是奇数坐标 (2px-(n-1), 2py-(n-1)) 到旋转中心的精确平方距离，整数。

三档分析:
  (A) 棋盘点级（所有对称类通用）: 每个 2n 点的 ring_key，统计
        - R = 不同环数
        - M = 任一环最多点数 (max multiplicity)
        - conc = R/(2n)  径向铺展度
        - 是否 M<=2（类比 research_M 的"每环<=2"在 board-point 级别）
  (B) rot4 专用 cell 级（C4 轨道还原）: 把 4m 点归成 m 个轨道，每轨道 ring_key 相同，
        统计 max cells per ring，直接复现 research_M 的"每环<=2 cell"律。
  (C) 跨类对比: 同 n 下各对称类的 R / M / conc 分布，看径向结构是否 C4 特有。

大数据集(iden n=17 有 25万)随机抽样 Ncap 条。
"""
import os, math, json, random
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "flammenkamp_cache")
ALPH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|"
VAL = {c: i for i, c in enumerate(ALPH)}
SYMMS = ["iden", "rot2", "dia1", "ort1", "rot4", "rct4", "dia2", "ort2", "full"]
Ncap = 3000

def decode_line(line, n):
    line = line.rstrip("\n").rstrip("\r")
    if not line:
        return None
    pre = line[0]
    body = line[1:] if pre in ".:/-ocx+*" else line
    if len(body) < 2 * n:
        return None
    cols = []
    for r in range(n):
        c1 = VAL[body[2 * r]]; c2 = VAL[body[2 * r + 1]]
        if not (0 <= c1 < n and 0 <= c2 < n):
            return None
        cols += [c1, c2]
    return cols

def points_of(cols, n):
    """2n 点: 每行 r 有 cols[2r], cols[2r+1] 两列。"""
    return [(r, cols[2 * r]) for r in range(n)] + [(r, cols[2 * r + 1]) for r in range(n)]

def ring_key(p, n):
    ctr = n - 1
    return (2 * p[0] - ctr) ** 2 + (2 * p[1] - ctr) ** 2

def rot90(p, n):
    return (p[1], (n - 1) - p[0])

def orbits(points, n):
    """C4 轨道: 每轨道 4 点(偶 n 无不动点)，返回 m 个 ring_key。"""
    S = set(points)
    rings = []
    while S:
        p = next(iter(S))
        orb = set()
        q = p
        for _ in range(4):
            orb.add(q); q = rot90(q, n)
        for q in orb:
            S.discard(q)
        # 取轨道代表 ring_key（4 点同 key）
        rings.append(ring_key(p, n))
    return rings

def analyze_config(cols, n):
    pts = points_of(cols, n)
    if len(set(pts)) != len(pts):
        return None  # 重复点，坏数据
    rk = [ring_key(p, n) for p in pts]
    cnt = Counter(rk)
    R = len(cnt)
    M = max(cnt.values())
    return {"R": R, "M": M, "conc": R / len(pts), "M_le_2": M <= 2}

def analyze_rot4_cell(cols, n):
    pts = points_of(cols, n)
    rings = orbits(pts, n)
    cnt = Counter(rings)
    # 每个 ring_key 由若干 C4 轨道共享；"cells per ring" = 共享该 key 的轨道数
    return {"m_cells": len(rings), "max_cells_per_ring": max(cnt.values()),
            "rings_used": len(cnt),
            "law_le2": max(cnt.values()) <= 2}

def main():
    rng = random.Random(20260715)
    report = {"meta": {"Ncap": Ncap, "symms": SYMMS}, "by_n_class": {},
              "rot4_cell_law": {}, "summary": {}}
    # 选择有数据的 n 范围
    ns = list(range(8, 24))
    for n in ns:
        report["by_n_class"][n] = {}
        for cls in SYMMS:
            p = os.path.join(CACHE, f"n{n}_{cls}")
            if not os.path.exists(p):
                continue
            with open(p) as f:
                lines = [l for l in f if l.strip()]
            if not lines:
                continue
            # 抽样
            if len(lines) > Ncap:
                lines = rng.sample(lines, Ncap)
            recs = []; cell_recs = []
            for line in lines:
                cols = decode_line(line, n)
                if cols is None:
                    continue
                a = analyze_config(cols, n)
                if a is None:
                    continue
                recs.append(a)
                if cls == "rot4":
                    cell_recs.append(analyze_rot4_cell(cols, n))
            if not recs:
                continue
            Rmean = sum(r["R"] for r in recs) / len(recs)
            Mmean = sum(r["M"] for r in recs) / len(recs)
            Mmax = max(r["M"] for r in recs)
            conc = sum(r["conc"] for r in recs) / len(recs)
            fle2 = sum(1 for r in recs if r["M_le_2"]) / len(recs)
            rep = {"nsol": len(recs), "R_mean": round(Rmean, 2),
                   "M_mean": round(Mmean, 2), "M_max": Mmax,
                   "conc_mean": round(conc, 3), "frac_M_le2": round(fle2, 3)}
            # M 分布
            mc = Counter(r["M"] for r in recs)
            rep["M_dist"] = dict(sorted(mc.items()))
            report["by_n_class"][n][cls] = rep
            # rot4 cell 级律
            if cls == "rot4" and cell_recs:
                cr = cell_recs
                report["rot4_cell_law"][n] = {
                    "nsol": len(cr),
                    "max_cells_per_ring_mean": round(sum(c["max_cells_per_ring"] for c in cr) / len(cr), 3),
                    "max_cells_per_ring_max": max(c["max_cells_per_ring"] for c in cr),
                    "rings_used_mean": round(sum(c["rings_used"] for c in cr) / len(cr), 2),
                    "frac_law_le2": round(sum(1 for c in cr if c["law_le2"]) / len(cr), 3),
                    "m_cells_mean": round(sum(c["m_cells"] for c in cr) / len(cr), 1),
                }
            print(f"n={n} {cls}: nsol={len(recs)} R={Rmean:.1f} M={Mmean:.2f}(max{Mmax}) conc={conc:.3f} frac_Mle2={fle2:.2f}", flush=True)

    # 汇总: 各对称类跨 n 平均（仅统计有 >=3 解的格）
    summ = {}
    for cls in SYMMS:
        Rs = []; Ms = []; cons = []; fle2s = []
        for n in report["by_n_class"]:
            d = report["by_n_class"][n].get(cls)
            if d and d["nsol"] >= 3:
                Rs.append(d["R_mean"]); Ms.append(d["M_mean"])
                cons.append(d["conc_mean"]); fle2s.append(d["frac_M_le2"])
        if Rs:
            summ[cls] = {"n_cases": len(Rs),
                         "R_mean_avg": round(sum(Rs) / len(Rs), 2),
                         "M_mean_avg": round(sum(Ms) / len(Ms), 2),
                         "conc_avg": round(sum(cons) / len(cons), 3),
                         "frac_M_le2_avg": round(sum(fle2s) / len(fle2s), 3)}
    report["summary"] = summ
    os.makedirs("results", exist_ok=True)
    with open("results/radial_nonrot4.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n=== CROSS-CLASS SUMMARY (avg over n with >=3 sols) ===")
    for cls in SYMMS:
        if cls in summ:
            s = summ[cls]
            print(f"{cls:<6} cases={s['n_cases']:>2} R={s['R_mean_avg']:.1f} M={s['M_mean_avg']:.2f} conc={s['conc_avg']:.3f} frac_Mle2={s['frac_M_le2_avg']:.2f}")

if __name__ == "__main__":
    main()
