#!/usr/bin/env python3
"""
向量角度观察【已知真解】(bad=0) 的几何结构，寻找跨 m 可推广到 m=37 的规律。

对每个已知解 (m=5..19, 36):
  1. C4 提升: m 个基本域 cell -> 4m 个格点 (ground-truth 旋转公式)
  2. 斜率多重集: 每条方向线上最多几点 (验证 R8-G per-line at-most-2)
  3. 方向向量 (dx,dy) 归一化后的分布 (向量方向多样性)
  4. 刚性余量: 所有三点组的最小 |叉积行列式| (真解离共线有多近)
  5. (S)/(X) 潜在冲突: 斜率±1 方向 vs 其它方向的最近共线距离
  6. 基本域奇坐标 a-b Sidon 检验 (SIRH Part I)
  7. 跨 m 标度: 各量随 m 变化, 外推 m=37

所有解都是 bad=0, 所以不会有真共线; 观察的是"接近共线"的几何刚性与方向统计。
"""
import json, os, math, itertools
from collections import Counter, defaultdict

SOLDIR = os.path.join(os.path.dirname(__file__), "solutions")

def lift_c4(cells, n):
    """m 个 cell -> 4m 个点 (C4 旋转), N=n=2m"""
    N = n
    pts = []
    for (x, y) in cells:
        pts.append((x, y))
        pts.append((N-1-y, x))
        pts.append((N-1-x, N-1-y))
        pts.append((y, N-1-x))
    return pts

def norm_dir(dx, dy):
    """方向向量归一 (约分 + 规范符号), 返回 (dx',dy')"""
    g = math.gcd(abs(dx), abs(dy))
    if g == 0:
        return (0, 0)
    dx //= g; dy //= g
    # 规范: 让第一个非零分量为正
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return (dx, dy)

def analyze(m, n, cells):
    pts = lift_c4(cells, n)
    P = len(pts)  # = 4m
    assert P == 4*m, f"m={m}: {P}!=4m"

    # --- 去重检查 ---
    if len(set(pts)) != P:
        dup = P - len(set(pts))
        # C4 对称解在中心附近可能自重合; 记录
    else:
        dup = 0

    # --- 斜率多重集: 每条极大共线线上点数 ---
    # 对每对点求归一方向 + 一个"线标识" (过点+方向)
    # 简化: 统计每个方向出现次数 (方向多样性), 以及每条线上点数
    dir_counter = Counter()
    for i in range(P):
        for j in range(i+1, P):
            dx = pts[j][0]-pts[i][0]; dy = pts[j][1]-pts[i][1]
            dir_counter[norm_dir(dx, dy)] += 1

    # 每条线上最大点数: 用 (方向, 截距) 分组
    line_pts = defaultdict(set)
    for i in range(P):
        for j in range(i+1, P):
            dx = pts[j][0]-pts[i][0]; dy = pts[j][1]-pts[i][1]
            d = norm_dir(dx, dy)
            # 线标识: 方向 d=(a,b), 过点 pts[i]; 截距 = a*y - b*x (整数不变量)
            c = d[0]*pts[i][1] - d[1]*pts[i][0]
            line_pts[(d, c)].add(i); line_pts[(d, c)].add(j)
    max_on_line = max(len(s) for s in line_pts.values())
    # 有多少条线上恰好 2 点 (安全), 是否有 >=3 (违规)
    lines_ge3 = sum(1 for s in line_pts.values() if len(s) >= 3)

    # --- 刚性余量: 所有三点组最小 |叉积| (>0 因 bad=0) ---
    # 并统计 det==1 幺模三点组的数量及其方向类型 (是否斜率±1)
    min_det = None
    n_unimod = 0          # |det|==1 的三点组数
    n_unimod_S = 0        # 其中含斜率±1 边的
    det_hist = Counter()  # 小 det 的分布
    for a, b, c in itertools.combinations(range(P), 3):
        d1x = pts[b][0]-pts[a][0]; d1y = pts[b][1]-pts[a][1]
        d2x = pts[c][0]-pts[a][0]; d2y = pts[c][1]-pts[a][1]
        det = abs(d1x*d2y - d1y*d2x)
        if det == 0:
            min_det = 0
        if min_det is None or det < min_det:
            min_det = det
        if det <= 5:
            det_hist[det] += 1
        if det == 1:
            n_unimod += 1
            # 三条边是否有斜率±1
            edges = [(d1x, d1y), (d2x, d2y), (d2x-d1x, d2y-d1y)]
            if any(abs(ex) == abs(ey) and ex != 0 for ex, ey in edges):
                n_unimod_S += 1

    # --- 方向向量多样性 ---
    ndir = len(dir_counter)
    # 斜率±1 方向的对数 (S 型潜在)
    s_pairs = sum(v for k, v in dir_counter.items() if abs(k[0]) == abs(k[1]) and k[0] != 0)
    total_pairs = sum(dir_counter.values())

    # --- a-b Sidon 检验 (SIRH Part I: 1D 投影 a-b 与 a+b) ---
    # Part I: G 保 slope±1 => 投影 u=x-y 的差集 Sidon (斜率+1 线); v=x+y (斜率-1 线)
    u = [x - y for (x, y) in cells]
    v = [x + y for (x, y) in cells]
    def sidon_viol_1d(vals):
        dc = Counter()
        for i in range(len(vals)):
            for j in range(len(vals)):
                if i == j: continue
                dc[vals[i]-vals[j]] += 1
        return sum(1 for c in dc.values() if c > 1)
    sidon_viol_u = sidon_viol_1d(u)
    sidon_viol_v = sidon_viol_1d(v)
    sidon_viol = sidon_viol_u + sidon_viol_v

    return {
        "m": m, "n": n, "points": P, "dup": dup,
        "max_on_line": max_on_line, "lines_ge3": lines_ge3,
        "min_det": min_det,
        "n_unimod": n_unimod, "n_unimod_S": n_unimod_S,
        "det_hist": {str(k): det_hist[k] for k in sorted(det_hist)},
        "n_directions": ndir, "s_pair_frac": round(s_pairs/total_pairs, 4),
        "sidon_viol_u": sidon_viol_u, "sidon_viol_v": sidon_viol_v,
        "sidon_viol_pairs": sidon_viol,
        "distinct_slopes_per_point": round(ndir / P, 3),
    }

def main():
    rows = []
    for f in sorted(os.listdir(SOLDIR)):
        if not f.endswith(".json"): continue
        d = json.load(open(os.path.join(SOLDIR, f)))
        r = analyze(d["m"], d["n"], d["cells"])
        rows.append(r)
        print(f"m={r['m']:2d} pts={r['points']:3d} maxline={r['max_on_line']} "
              f"min|det|={r['min_det']} unimod={r['n_unimod']:3d}(S={r['n_unimod_S']:3d}) "
              f"ndir={r['n_directions']:4d} S%={r['s_pair_frac']:.3f} "
              f"sidon(u={r['sidon_viol_u']},v={r['sidon_viol_v']})")

    # 保存
    out = os.path.join(os.path.dirname(__file__), "known_solutions_vectors.json")
    json.dump(rows, open(out, "w"), indent=1)
    print(f"\n[saved] {out}")

    # 跨 m 标度分析
    print("\n=== 跨 m 标度 ===")
    ms = [r["m"] for r in rows]
    print("min|det| 序列:", [r["min_det"] for r in rows])
    print("ndir/point 序列:", [r["distinct_slopes_per_point"] for r in rows])
    print("S%  序列:", [r["s_pair_frac"] for r in rows])
    # 检验关键定理: 是否所有解都 max_on_line==2 且 sidon_viol==0
    all_2 = all(r["max_on_line"] == 2 for r in rows)
    all_sidon = all(r["sidon_viol_pairs"] == 0 for r in rows)
    all_unimod = all(r["min_det"] == 1 for r in rows)
    print(f"\n[定理验证] 全部 max_on_line==2 (R8-G per-line<=2): {all_2}")
    print(f"[定理验证] 全部 sidon(u,v)==0 (Part I 1D 投影 Sidon): {all_sidon}")
    print(f"[新不变量] 全部 min|det|==1 (幺模刚性边界): {all_unimod}")
    print("unimod 三点组数序列:", [r["n_unimod"] for r in rows])
    print("其中含斜率±1 边:", [r["n_unimod_S"] for r in rows])

if __name__ == "__main__":
    main()
