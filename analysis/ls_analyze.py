#!/usr/bin/env python3
"""
ls_analyze.py -- 把扫描结果 + 轨迹整理成一份可读的 HTML 报告(内联 SVG, 无外部依赖)。

输出: results/local_search_report.html
包含:
  1. 各配置 × 各 m 的求解率 / 平均 final_bad 汇总表
  2. 求解率柱状对比图(看哪种理论先验有用)
  3. 典型 bad-vs-迭代下降曲线(看是否陷局部极小)
  4. 先验热图 vs 最终落点(看点往哪里聚 -- 可复用规律)
"""
import json, os

SWEEP = "results/local_search_sweep.json"
TRAJ = "results/local_search_trajectory.json"
OUT = "results/local_search_report.html"

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;")

def bar_chart_svg(series, w=520, h=240):
    """series: list of (label, value 0..1). 画求解率柱状图。"""
    n = len(series)
    bw = w / (n + 1)
    maxv = 1.0
    parts = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    # 基线
    parts.append(f'<line x1="40" y1="{h-30}" x2="{w-10}" y2="{h-30}" stroke="#888"/>')
    for i, (lab, v) in enumerate(series):
        x = 40 + i * bw + bw * 0.15
        bh = (h - 40) * (v / maxv)
        y = h - 30 - bh
        col = "#2a7" if v >= 0.999 else ("#e85" if v > 0 else "#c44")
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.7:.1f}" height="{bh:.1f}" fill="{col}"/>')
        parts.append(f'<text x="{x+bw*0.35:.1f}" y="{h-16}" font-size="9" text-anchor="middle" fill="#333">{esc(lab)}</text>')
        parts.append(f'<text x="{x+bw*0.35:.1f}" y="{y-3:.1f}" font-size="9" text-anchor="middle" fill="#333">{v*100:.0f}%</text>')
    parts.append('</svg>')
    return "".join(parts)

def line_chart_svg(traj, w=520, h=240, maxbad=None):
    """traj: bad 每 200 迭代的记录。画下降曲线。"""
    if not traj:
        return "<svg viewBox='0 0 520 240'></svg>"
    n = len(traj)
    if maxbad is None:
        maxbad = max(traj) if max(traj) > 0 else 1
    parts = ["<svg viewBox='0 0 %d %d' xmlns='http://www.w3.org/2000/svg'>" % (w, h)]
    parts.append(f"<line x1='40' y1='{h-30}' x2='{w-10}' y2='{h-30}' stroke='#888'/>")
    for i, v in enumerate(traj):
        x = 40 + (w - 50) * (i / max(1, n - 1))
        y = (h - 30) - (h - 40) * (v / maxbad)
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='2' fill='#36c'/>")
        if i > 0:
            pv = traj[i-1]
            px = 40 + (w - 50) * ((i-1) / max(1, n - 1))
            py = (h - 30) - (h - 40) * (pv / maxbad)
            parts.append(f"<line x1='{px:.1f}' y1='{py:.1f}' x2='{x:.1f}' y2='{y:.1f}' stroke='#36c' stroke-width='1'/>")
    # 标注最终值
    parts.append(f"<text x='{w-10}' y='{h-34}' font-size='9' text-anchor='end' fill='#c44'>final bad={traj[-1]}</text>")
    parts.append("</svg>")
    return "".join(parts)

def heatmap_svg(m, prior, cells, w=240, h=240):
    """prior: dict 'x,y'->weight; cells: list of (x,y) 最终落点。"""
    parts = [f"<svg viewBox='0 0 {w} {h}' xmlns='http://www.w3.org/2000/svg'>"]
    cw = w / m
    mx = max(prior.values()) if prior else 1
    cellset = set(cells or [])
    for x in range(m):
        for y in range(m):
            wv = prior.get(f"{x},{y}", 0)
            inten = int(255 * (1 - wv / mx))  # 高先验 -> 深
            fill = f"rgb({inten},{inten},{255})"
            xx = y * cw; yy = x * cw  # 注意: x 行, y 列
            parts.append(f"<rect x='{xx:.1f}' y='{yy:.1f}' width='{cw:.1f}' height='{cw:.1f}' fill='{fill}' stroke='#ddd' stroke-width='0.3'/>")
            if (x, y) in cellset:
                parts.append(f"<rect x='{xx+cw*0.2:.1f}' y='{yy+cw*0.2:.1f}' width='{cw*0.6:.1f}' height='{cw*0.6:.1f}' fill='none' stroke='#c00' stroke-width='1.5'/>")
    parts.append("</svg>")
    return "".join(parts)

def main():
    sweep = json.load(open(SWEEP))
    data = sweep["data"]
    ms = sweep["meta"]["ms"]
    configs = list(data[str(ms[0])].keys()) if ms else []
    # 汇总表
    rows = []
    for c in configs:
        cells_html = ""
        for m in ms:
            d = data[str(m)][c]
            sr = d["solve_rate"]
            mark = "✓" if sr >= 0.999 else ("·" if sr > 0 else "✗")
            cells_html += (f"<td style='text-align:center'>{mark} {sr*100:.0f}%<br>"
                           f"<span style='color:#888;font-size:11px'>bad={d['avg_final_bad']:.1f}</span></td>")
        rows.append(f"<tr><td>{esc(c)}</td>{cells_html}</tr>")
    header = "".join(f"<th>m={m}</th>" for m in ms)

    # 对最后一个 m 画求解率柱状图(直观看哪种配置最好)
    last_m = ms[-1]
    bars = [(c, data[str(last_m)][c]["solve_rate"]) for c in configs]
    bar_svg = bar_chart_svg(bars)

    # 轨迹曲线
    traj_svg = ""
    traj_info = ""
    if os.path.exists(TRAJ):
        t = json.load(open(TRAJ))
        traj_svg = line_chart_svg(t.get("traj_bad", []))
        traj_info = (f"m={t['m']} 初始化=sa/highprob, 最终 bad={t['final_bad']} "
                     f"(solved={t['solved']}, verified={t['verified']})")
        # 先验热图 + 落点
        heat = heatmap_svg(t["m"], t["prior"], t.get("best_cells", []))
    else:
        heat = ""

    html = f"""<html><head><meta charset="utf-8"><title>局部搜索规律报告</title>
<style>body{{font-family:-apple-system,Segoe UI,sans-serif;margin:24px;color:#222}}
table{{border-collapse:collapse;margin:12px 0}} th,td{{border:1px solid #ccc;padding:6px 10px}}
th{{background:#f0f4f8}} .card{{border:1px solid #ddd;border-radius:8px;padding:12px;margin:12px 0}}
.caption{{color:#666;font-size:12px;margin:4px 0 10px}}</style></head><body>
<h1>带理论先验的局部搜索 — 小 m 规律扫描</h1>
<p class="caption">方法: 固定锚点 + 高概率区/理论初始化 + 单点移动 + 贪心/模拟退火下降 bad(共线三元组数).
bad==0 即经验可验证 rot4-NTIL 解. 坐标约定与 solve_m37_r9b 一致.</p>

<div class="card"><h3>1. 求解率汇总 (✓=全解 ·=部分 ✗=全卡)</h3>
<table><tr><th>config</th>{header}</tr>{''.join(rows)}</table>
<p class="caption">config: C1 贪心/随机; C2 SA/随机; C3 SA/高概率; C4 SA/高概率+40%锚点; C5 SA/Sidon过滤(理论固定). 每格显示 求解率% 与 平均 final_bad.</p></div>

<div class="card"><h3>2. m={last_m} 各配置求解率对比</h3>{bar_svg}
<p class="caption">直观看哪一种"理论先验"真正提升了收敛率.</p></div>

<div class="card"><h3>3. 典型下降曲线 (bad vs 迭代)</h3>{traj_svg}
<p class="caption">{esc(traj_info)}</p>
<p class="caption">曲线快速下降后<strong>平台化</strong>即陷入局部极小 — 这是单点移动法的核心瓶颈.</p></div>

<div class="card"><h3>4. 先验热图(蓝深=高概率区) vs 最终落点(红框)</h3>{heat}
<p class="caption">观察点是否收敛到中环/避开对角线 — 可提炼为构造性规则.</p></div>
</body></html>"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
