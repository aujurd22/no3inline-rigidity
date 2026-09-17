#!/usr/bin/env python3
"""
cube_null_model.py -- 正确零模型: NTIL cell 角度分布 vs 同尺寸完整格点云。

关键: 格点本身角度分布非均匀(堆在有理斜率), 所以"比均匀角度多2.58x"是误导。
正确问法: NTIL 比"随便撒 m 个格点"更/不更偏好对角?
"""
import math, os, sys
from collections import defaultdict
sys.path.insert(0, ".")
from quadratic_sidon_completeness import load_known

MS = [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,36]
NB = 90

def ang_bin(X, Y):
    if abs(X) < 1e-9 and abs(Y) < 1e-9:
        return 0
    t = math.degrees(math.atan2(Y, X)) % 90.0
    return min(NB-1, int(t))

def main():
    L = []
    def log(s=""): L.append(s)
    glob_lattice = [0]*NB
    glob_nt = [0]*NB
    # 对角对比 (x=y 或 x+y=2m-1)
    diag_nt = 0; tot_nt = 0
    diag_lat = 0; tot_lat = 0

    for m in MS:
        # 完整格点云 (m^2 个 fundamental 点)
        lat = [0]*NB
        dlat = 0
        for x in range(m):
            for y in range(m):
                X, Y = x-(m-0.5), y-(m-0.5)
                b = ang_bin(X, Y)
                lat[b] += 1
                glob_lattice[b] += 1
                if abs(abs(X)-abs(Y)) < 0.6:
                    dlat += 1; diag_lat += 1
        tot_lat += m*m

        # NTIL cells
        sols = load_known(m, cap=200000)
        nt = [0]*NB
        dnt = 0
        for sol in sols:
            for (x, y) in sol:
                X, Y = x-(m-0.5), y-(m-0.5)
                b = ang_bin(X, Y)
                nt[b] += 1
                glob_nt[b] += 1
                tot_nt += 1
                if abs(abs(X)-abs(Y)) < 0.6:
                    dnt += 1; diag_nt += 1
        # 每 m 的对角占比对比
        log(f"m={m:2d}: NTIL diag={dnt/tot_nt:.4f}  lattice diag={dlat/(m*m):.4f}  "
            f"ratio={ (dnt/tot_nt)/(dlat/(m*m)) if dlat else 0:.3f}")

    # 全局: 按 m 归一化成比例后再汇总 (避免多解聚合污染分母)
    log("")
    log("## 全局角度分布比 (NTIL比例 / 完整格点比例, 按 m 聚合)")
    # 重新逐 m 累计比例
    agg_num = [0.0]*NB   # sum over m of nt_frac[i]
    agg_den = [0.0]*NB   # sum over m of lat_frac[i]
    for m in MS:
        lat = [0]*NB
        for x in range(m):
            for y in range(m):
                X, Y = x-(m-0.5), y-(m-0.5)
                lat[ang_bin(X, Y)] += 1
        sols = load_known(m, cap=200000)
        nt = [0]*NB
        nc = 0
        for sol in sols:
            for (x, y) in sol:
                X, Y = x-(m-0.5), y-(m-0.5)
                nt[ang_bin(X, Y)] += 1
                nc += 1
        if m*m > 0 and nc > 0:
            for i in range(NB):
                agg_num[i] += nt[i]/nc
                agg_den[i] += lat[i]/(m*m)
    ratio_per_bin = []
    for i in range(NB):
        if agg_den[i] > 1e-9:
            ratio_per_bin.append((i, agg_num[i]/agg_den[i]))
    mean_r = sum(r for _, r in ratio_per_bin)/len(ratio_per_bin)
    log(f"- 每桶比均值(应≈1若NTIL角度=随机格点): {mean_r:.4f}")
    log(f"- NTIL 最偏好的角(top5, 比>1=过代表):")
    for i, r in sorted(ratio_per_bin, key=lambda t: -t[1])[:5]:
        log(f"    {i}°: ratio={r:.3f}")
    log(f"- NTIL 最回避的角(top5, 比<1=欠代表):")
    for i, r in sorted(ratio_per_bin, key=lambda t: t[1])[:5]:
        log(f"    {i}°: ratio={r:.3f}")

    log("")
    log(f"## 对角总体: NTIL={diag_nt/tot_nt:.4f}  lattice={diag_lat/tot_lat:.4f}  "
        f"ratio={diag_nt/tot_nt/(diag_lat/tot_lat):.3f}")
    log("  (ratio<1 => NTIL 实际比随便撒格点更回避对角; >1 => 真正偏好)")

    os.makedirs("results", exist_ok=True)
    with open("results/cube_null_model.md", "w") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))

if __name__ == "__main__":
    main()
