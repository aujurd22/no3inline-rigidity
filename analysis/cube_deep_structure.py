#!/usr/bin/env python3
"""
cube_deep_structure.py -- 深层结构分析: 投影图 (Y,Z) 里到底藏了什么。

不再只数"每层几个点", 而是挖:
  1. 角度分布: 每个 fundamental cell 到中心的极角 theta (mod 90°),
     看 cells 是否偏好某些角度 (=> 投影里出现"射线/条纹")
  2. 半径壳层: 哪些半径 R 被占据, 有无空隙
  3. 包络: 对每个 R, Y 覆盖 [-R,R] 的比例 (满三角 vs 角聚集)
  4. 跨解一致性: 同一 m 的不同解, 是否共享同一套 (R,theta) 壳层
  5. 对角偏好: 落在对角线(theta≈45°)的 cell 比例, 与 z=0 可见=2 的关系

输出: results/cube_deep_structure.md / .json + 两张可视化 SVG
"""
import json, math, os, sys
from collections import defaultdict, Counter
sys.path.insert(0, ".")
from quadratic_sidon_completeness import load_known
from cube_lens import embed, lift

MS = [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,36]

def centered_cell_xy(x, y, m):
    return (x - (m - 0.5), y - (m - 0.5))

def main():
    report = {}
    L = []
    def log(s=""): L.append(s)

    # ---- 全局角分布 (mod 90°, 1° bins) ----
    NB = 90
    glob_ang = [0]*NB
    glob_rad = []          # 所有 fundamental cell 的半径 (归一化)
    diag_frac_by_m = {}
    ncell_total = 0
    diag_total = 0

    # 跨解壳层一致性
    shells_by_m = defaultdict(list)   # m -> list of Counter (每解是 {shell_key:1})

    for m in MS:
        sols = load_known(m, cap=200000)
        ang_bins = [0]*NB
        rads = []
        diag = 0
        nc = 0
        sol_shells = []
        for sol in sols:
            sc = Counter()
            for (x, y) in sol:
                X, Y = centered_cell_xy(x, y, m)
                R = math.hypot(X, Y)
                if R < 1e-9:
                    continue
                theta = math.degrees(math.atan2(Y, X)) % 90.0
                b = min(NB-1, int(theta))
                ang_bins[b] += 1
                glob_ang[b] += 1
                rads.append(R)
                glob_rad.append(R / (m*math.sqrt(2)))
                nc += 1; ncell_total += 1
                # 对角: |X|≈|Y|
                if abs(abs(X) - abs(Y)) < 0.6:
                    diag += 1; diag_total += 1
                # 壳层 key: 量化 (R_norm, theta_deg)
                rk = round(R / (m*math.sqrt(2)), 2)
                tk = round(theta, 1)
                sc[(rk, tk)] += 1
            sol_shells.append(sc)
        diag_frac_by_m[m] = (diag, nc, diag/nc if nc else 0)
        shells_by_m[m] = sol_shells

        # 每 m 的角分布峰值
        peak = max(range(NB), key=lambda i: ang_bins[i])
        log(f"  m={m:2d} nsol={len(sols):3d} cells={nc:4d} diag_frac={diag/nc:.3f} "
            f"peak_angle={peak}°({ang_bins[peak]})")

    # ---- 角分布统计分析 ----
    total_ang = sum(glob_ang)
    mean_ang = total_ang / NB
    # 均匀期望 = 每 bin mean_ang; 计算 chi-sq 风格偏差
    max_dev = max(abs(glob_ang[i]-mean_ang) for i in range(NB))
    # 45°(对角) 桶 与 均匀期望 对比 (注: 居中坐标是半整数, 无 cell 精确落在坐标轴,
    # 故 theta 永不为 0/90, bin0/bin89 恒为 0 -> 改用对角 vs 均匀期望)
    diag_bin = glob_ang[45]
    axis_win = (sum(glob_ang[1:4]) + sum(glob_ang[86:89])) / 6.0
    log("")
    log("## 1. 极角分布 (mod 90°) -- 全局")
    log(f"- 总 cell 采样: {total_ang}")
    log(f"- 均匀期望/桶: {mean_ang:.1f}")
    log(f"- 最大桶偏差: {max_dev:.1f} ({max_dev/mean_ang*100:.1f}% of mean)")
    log(f"- theta=45°(对角)桶: {diag_bin}  vs 均匀期望: {mean_ang:.1f}  -> 比 = {diag_bin/mean_ang:.3f}")
    log(f"- 近轴窗口(1-3°,86-88°)均/桶: {axis_win:.1f}  -> 对角/近轴 = {diag_bin/axis_win:.3f}")
    # 找 top-5 角度峰
    order = sorted(range(NB), key=lambda i: -glob_ang[i])[:5]
    log(f"- Top-5 角度峰: " + ", ".join(f"{i}°({glob_ang[i]})" for i in order))

    # ---- 半径壳层占据 ----
    log("")
    log("## 2. 半径壳层 (归一化 R/(m√2))")
    rbins = 20
    hist = [0]*rbins
    for r in glob_rad:
        b = min(rbins-1, int(r*rbins))
        hist[b] += 1
    nonempty = sum(1 for h in hist if h>0)
    log(f"- 归一化半径分 {rbins} 桶, 非空桶: {nonempty}/{rbins}")
    log(f"- 半径分布(每桶占比): " + " ".join(f"{h/len(glob_rad)*100:.0f}" for h in hist))
    # 空隙: 连续为 0 的桶
    gaps = []
    i = 0
    while i < rbins:
        if hist[i] == 0:
            j = i
            while j < rbins and hist[j] == 0:
                j += 1
            gaps.append((i/rbins, j/rbins))
            i = j
        else:
            i += 1
    log(f"- 半径空隙区间(归一化): {gaps if gaps else '无'}")

    # ---- 包络: 每 R 的 Y 覆盖 ----
    log("")
    log("## 3. 包络形状 (|Y|≤R 三角是否被填满)")
    # 用 m=16 代表解看细结构
    sols16 = load_known(16, cap=200000)
    rep = sols16[0]
    P, zs, layers, uniq = embed(rep, 16)
    covs = []
    for z in sorted(layers):
        xy = layers[z]
        rs = [math.hypot(x,y) for (x,y) in xy]
        Rz = max(rs) if rs else 0
        ys = [y for (x,y) in xy]
        if Rz > 1e-9:
            ycov = (max(ys)-min(ys)) / (2*Rz)   # 理想满三角=1
            covs.append(ycov)
    log(f"- m=16 代表解: 平均每层 Y 覆盖 [-R,R] 比例 = {sum(covs)/len(covs):.3f}")
    log(f"  (1.0=满三角/角均匀; 越小=角聚集越严重)")

    # ---- 跨解壳层一致性 ----
    log("")
    log("## 4. 跨解壳层一致性 (同一 m 不同解是否共享 (R,theta) 壳)")
    for m in [8, 12, 16, 19]:
        ss = shells_by_m[m]
        if not ss: continue
        nsol = len(ss)
        # 合并所有 shell key, 统计出现解数
        keycount = Counter()
        for sc in ss:
            for k in sc:
                keycount[k] += 1
        universal = [k for k,c in keycount.items() if c == nsol]
        majority = [k for k,c in keycount.items() if c >= nsol*0.8]
        log(f"- m={m}: nsol={nsol}, 总壳数={len(keycount)}, "
            f"全解共有壳={len(universal)}, ≥80%解共有壳={len(majority)}")
        if universal:
            sample = sorted(universal, key=lambda k: k[0])[:6]
            log(f"    全解共有壳样本: {sample}")

    # ---- 对角偏好 vs z=0 可见 ----
    log("")
    log("## 5. 对角 cell 偏好 (theta≈45°)")
    for m in [5,6,12,16,19,36]:
        d, nc, f = diag_frac_by_m[m]
        log(f"- m={m}: diag_frac={f:.3f} ({d}/{nc})")

    # ===== 写 json =====
    out = {
        "global_angle_hist": glob_ang,
        "angle_mean": mean_ang,
        "angle_max_dev_frac": max_dev/mean_ang,
        "diag_vs_mean": diag_bin/mean_ang,
        "diag_vs_axiswin": diag_bin/axis_win,
        "radius_hist": hist,
        "radius_gaps": gaps,
        "m16_y_coverage": sum(covs)/len(covs),
        "diag_frac_by_m": {str(m): list(diag_frac_by_m[m]) for m in diag_frac_by_m},
    }
    os.makedirs("results", exist_ok=True)
    with open("results/cube_deep_structure.json", "w") as f:
        json.dump(out, f, indent=2)

    md = "\n".join(L)
    with open("results/cube_deep_structure.md", "w") as f:
        f.write(md + "\n")

    # ===== 可视化 1: 角分布柱状图 =====
    W, H = 680, 300
    bw = W / NB
    mx = max(glob_ang)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">']
    svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>')
    for i in range(NB):
        h = glob_ang[i]/mx*(H-40)
        x = i*bw
        svg.append(f'<rect x="{x:.1f}" y="{H-20-h:.1f}" width="{bw-0.5:.1f}" height="{h:.1f}" fill="#3b6ea5"/>')
    # 标 0/45/90
    for deg, lab in [(0,"0°"),(45,"45°(对角)"),(89,"90°")]:
        x = deg*bw
        svg.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{H-20}" stroke="#c33" stroke-width="1" stroke-dasharray="3,2"/>')
        svg.append(f'<text x="{x+2:.1f}" y="12" fill="#c33" font-size="11">{lab}</text>')
    svg.append(f'<text x="10" y="{H-4}" fill="#333" font-size="11">极角分布 mod 90° (全 {total_ang} cells, 蓝=计数, 红虚线=轴/对角)</text>')
    svg.append('</svg>')
    with open("results/cube_angle_hist.svg", "w") as f:
        f.write("\n".join(svg))

    # ===== 可视化 2: m=16 代表解 (Y, R) 原始散点 =====
    P, zs, layers, uniq = embed(rep, 16)
    W2, H2 = 400, 400
    svg2 = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W2} {H2}" font-family="sans-serif">']
    svg2.append(f'<rect x="0" y="0" width="{W2}" height="{H2}" fill="#fff"/>')
    # 包络三角 |Y|<=R
    Rmax = max(math.hypot(x,y) for (x,y) in P)
    def sx(Y): return W2/2 + Y/Rmax*(W2/2-15)
    def sy(R): return H2 - 10 - R/Rmax*(H2-20)
    svg2.append(f'<polygon points="{sx(-Rmax):.1f},{sy(Rmax):.1f} {sx(0):.1f},{sy(0):.1f} {sx(Rmax):.1f},{sy(Rmax):.1f}" fill="none" stroke="#ccc" stroke-dasharray="3,2"/>')
    for (x,y) in P:
        R = math.hypot(x,y)
        cx = sx(y); cy = sy(R)
        svg2.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="#3b6ea5" stroke="#223" stroke-width="0.5"/>')
    svg2.append(f'<text x="8" y="14" fill="#333" font-size="11">m=16 代表解: (Y, R) 原始散点, 虚线=|Y|≤R 包络</text>')
    svg2.append('</svg>')
    with open("results/cube_yR_scatter.svg", "w") as f:
        f.write("\n".join(svg2))

    print(md)
    print("\n[wrote] results/cube_deep_structure.md/.json, results/cube_angle_hist.svg, results/cube_yR_scatter.svg")

if __name__ == "__main__":
    main()
