#!/usr/bin/env python3
"""radial_chart.py -- 把 radial_nonrot4.json 画成对比图 (SVG)."""
import json, os
d = json.load(open("results/radial_nonrot4.json"))
bnc = d["by_n_class"]

# 线图: conc vs n, 四个主类
classes = ["iden", "rot2", "dia1", "rot4"]
colors = {"iden": "#4e9bff", "rot2": "#ffb14e", "dia1": "#5fd38a", "rot4": "#ff5f6e"}
ns = list(range(10, 21))
series = {c: [(n, bnc[str(n)][c]["conc_mean"]) for n in ns if c in bnc[str(n)]] for c in classes}

W, H = 680, 300
pad = 45
x0, y0 = pad, H - pad
x1, y1 = W - 20, 20
ymin, ymax = 0.2, 0.75
def X(n): return x0 + (n - ns[0]) / (ns[-1] - ns[0]) * (x1 - x0)
def Y(v): return y0 + (v - ymin) / (ymax - ymin) * (y1 - y0)

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">']
svg.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
svg.append(f'<text x="{W/2}" y="18" text-anchor="middle" font-size="13" fill="#222">径向铺展度 conc = 使用环数 / 总点数 (越高越均匀)</text>')
# axes
svg.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#888"/>')
svg.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#888"/>')
for v in [0.2,0.3,0.4,0.5,0.6,0.7]:
    yy = Y(v); svg.append(f'<line x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" stroke="#eee"/>')
    svg.append(f'<text x="{x0-5}" y="{yy+3}" text-anchor="end" font-size="9" fill="#666">{v:.1f}</text>')
for n in ns:
    if n % 2 == 0:
        svg.append(f'<text x="{X(n)}" y="{y0+12}" text-anchor="middle" font-size="9" fill="#666">{n}</text>')
for c in classes:
    pts = " ".join(f"{X(n):.1f},{Y(v):.1f}" for n, v in series[c])
    svg.append(f'<polyline points="{pts}" fill="none" stroke="{colors[c]}" stroke-width="2"/>')
    for n, v in series[c]:
        svg.append(f'<circle cx="{X(n):.1f}" cy="{Y(v):.1f}" r="2.5" fill="{colors[c]}"/>')
# legend
lx = x0 + 10
for i, c in enumerate(classes):
    ly = y1 + 8 + i * 14
    svg.append(f'<rect x="{lx}" y="{ly-8}" width="10" height="10" fill="{colors[c]}"/>')
    svg.append(f'<text x="{lx+14}" y="{ly}" font-size="10" fill="#222">{c}</text>')
svg.append('</svg>')

# 柱图: 跨类 conc_avg
summ = d["summary"]
order = ["iden", "dia1", "rot2", "dia2", "rot4"]
order = [c for c in order if c in summ]
BW, BH = 680, 220
bx0, by0 = 60, BH - 40
bx1 = BW - 30
maxv = max(summ[c]["conc_avg"] for c in order)
bw = (bx1 - bx0) / len(order) * 0.6
svg2 = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BW} {BH}" font-family="sans-serif">']
svg2.append(f'<rect width="{BW}" height="{BH}" fill="#ffffff"/>')
svg2.append(f'<text x="{BW/2}" y="16" text-anchor="middle" font-size="13" fill="#222">跨对称类平均径向铺展度 (n 加权)</text>')
svg2.append(f'<line x1="{bx0}" y1="{by0}" x2="{bx1}" y2="{by0}" stroke="#888"/>')
for i, c in enumerate(order):
    v = summ[c]["conc_avg"]
    x = bx0 + (bx1 - bx0) / len(order) * (i + 0.2)
    h = v / maxv * (by0 - 25)
    col = colors.get(c, "#888")
    svg2.append(f'<rect x="{x:.1f}" y="{by0-h:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{col}"/>')
    svg2.append(f'<text x="{x+bw/2:.1f}" y="{by0-h-4:.1f}" text-anchor="middle" font-size="10" fill="#222">{v:.2f}</text>')
    svg2.append(f'<text x="{x+bw/2:.1f}" y="{by0+14:.1f}" text-anchor="middle" font-size="10" fill="#222">{c}</text>')
svg2.append('</svg>')

os.makedirs("results", exist_ok=True)
with open("results/radial_nonrot4_chart.svg", "w") as f:
    f.write("\n".join(svg) + "\n" + "\n".join(svg2))
print("written results/radial_nonrot4_chart.svg")
