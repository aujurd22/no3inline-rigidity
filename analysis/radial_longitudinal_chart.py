#!/usr/bin/env python3
"""radial_longitudinal_chart.py -- 纵向径向层对比图 (heatmap + <rho> 稳定性)"""
import json, statistics

d = json.load(open("results/radial_longitudinal.json"))
B = d["B"]
ms = d["ms"]
pm = d["per_m"]

# 选有代表性的 m 行画热图
rows = [m for m in ms if m in (4,5,6,8,10,12,14,16,18,20,22,27,28,36)]

def color(t):
    # 0 -> 深蓝, 1 -> 黄
    t = max(0.0, min(1.0, t))
    r = int(20 + t * 235)
    g = int(40 + t * 200)
    b = int(120 - t * 90)
    return f"rgb({r},{g},{b})"

W, H = 680, 560
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="11">']
svg.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

# ── Panel A: 占用率热图 (rows=m, cols=rho bins) ──
ax, ay, aw, ah = 70, 40, 540, 250
svg.append(f'<text x="{ax}" y="{ay-8}" font-size="12" font-weight="bold">各 m 解在归一半径 rho 上的占用发生率 (纵向横向对比)</text>')
cw = aw / B
chh = ah / len(rows)
for ri, m in enumerate(rows):
    occ = pm[str(m)]["occupancy_incidence"]
    y = ay + ri * chh
    for bi in range(B):
        x = ax + bi * cw
        svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw+0.5:.1f}" height="{chh+0.5:.1f}" fill="{color(occ[bi])}"/>')
    svg.append(f'<text x="{ax-6}" y="{y+chh/2+3:.1f}" text-anchor="end" font-size="10">{m}</text>')
# rho 轴刻度
for rho_tick in (0.25, 0.5, 0.57, 0.75):
    bx = ax + rho_tick * B * cw
    svg.append(f'<line x1="{bx:.1f}" y1="{ay}" x2="{bx:.1f}" y2="{ay+ah}" stroke="#888" stroke-width="0.5" stroke-dasharray="3,2"/>')
    svg.append(f'<text x="{bx:.1f}" y="{ay+ah+12:.1f}" text-anchor="middle" font-size="9">{rho_tick:.2f}</text>')
svg.append(f'<line x1="{ax+0.57*B*cw:.1f}" y1="{ay}" x2="{ax+0.57*B*cw:.1f}" y2="{ay+ah}" stroke="#d00" stroke-width="1.2"/>')
svg.append(f'<text x="{ax+0.57*B*cw+3:.1f}" y="{ay+10:.1f}" fill="#d00" font-size="9">rho*=0.57</text>')
svg.append(f'<text x="{ax+aw+4:.1f}" y="{ay+ah/2:.1f}" font-size="9" fill="#555">占用率→</text>')

# ── Panel B: <rho> vs m 稳定性 ──
bx0, by0, bw, bh = 70, 340, 540, 180
svg.append(f'<text x="{bx0}" y="{by0-8}" font-size="12" font-weight="bold">平均归一半径 &lt;rho&gt; 随 m 的稳定性 (跨所有解, 误差棒=std)</text>')
rho_min, rho_max = 0.50, 0.62
def sy(rho):
    return by0 + bh - (rho - rho_min) / (rho_max - rho_min) * bh
mx0, mx1 = min(ms), max(ms)
def sx(m):
    return bx0 + (m - mx0) / (mx1 - mx0) * bw
# y 网格
for rho in (0.52, 0.54, 0.56, 0.58, 0.60):
    yy = sy(rho)
    svg.append(f'<line x1="{bx0}" y1="{yy:.1f}" x2="{bx0+bw}" y2="{yy:.1f}" stroke="#eee"/>')
    svg.append(f'<text x="{bx0-5:.1f}" y="{yy+3:.1f}" text-anchor="end" font-size="9">{rho:.2f}</text>')
# 均值线
mean_all = statistics.mean([pm[str(m)]["mean_r_mean"] for m in ms])
svg.append(f'<line x1="{bx0}" y1="{sy(mean_all):.1f}" x2="{bx0+bw}" y2="{sy(mean_all):.1f}" stroke="#d00" stroke-width="1.2" stroke-dasharray="4,3"/>')
svg.append(f'<text x="{bx0+bw:.1f}" y="{sy(mean_all)-4:.1f}" text-anchor="end" fill="#d00" font-size="9">mean={mean_all:.3f}</text>')
# 点 + 误差棒
for m in ms:
    p = pm[str(m)]
    x = sx(m); y = sy(p["mean_r_mean"])
    err = p["mean_r_std"] * (bh / (rho_max - rho_min))
    svg.append(f'<line x1="{x:.1f}" y1="{y-err:.1f}" x2="{x:.1f}" y2="{y+err:.1f}" stroke="#2a6" stroke-width="1"/>')
    svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#2a6"/>')
svg.append(f'<line x1="{bx0}" y1="{by0+bh:.1f}" x2="{bx0+bw}" y2="{by0+bh:.1f}" stroke="#888"/>')
svg.append(f'<text x="{bx0+bw:.1f}" y="{by0+bh+14:.1f}" text-anchor="end" font-size="9">m</text>')

svg.append('</svg>')
open("results/radial_longitudinal_chart.svg", "w").write("\n".join(svg))
print("chart written, size=", len("\n".join(svg)))
