#!/usr/bin/env python3
"""
cube_proj_allm.py -- 所有 m (5..19, 36) 的所有 rot4 解 的 3D 嵌入投影分层分析。

对每一个解的每一个 z 层（到缺失中心欧氏距离排位, z=0 最内）：
  - 实际 3D 点数 = 4 * 该层 fundamental cell 数（必为 4 的倍数: 4/8/12）
  - 左视 (Y,Z) 可见点数 = 该层 4k 点里 distinct Y 的个数
  - 右视 (-Y,Z) 可见点数 = distinct (-Y) = 与左视完全相同（镜像）

聚合（跨所有解、跨所有 m）：
  - 每 m 底层 z=0 可见点数的分布（是否恒为 2？）
  - 按归一化层位 (0=最内,1=最外) 分箱的可见点数均值热图
  - 输出：网格投影图 (每个 m 一张左视) + 热图 + 报告

注：load_known 返回奇数坐标 (1..2m-1)，需转回 fundamental (0..m-1) 才能和
cube_lens.embed 一致（load_ref 直接给 fundamental）。
"""
import json, math, os, sys
from collections import defaultdict, Counter
sys.path.insert(0, "analysis")
from cube_lens import embed, load_ref
from quadratic_sidon_completeness import load_known

MS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 36]


def odd_to_fund(pairs, m):
    """奇数坐标 (1..2m-1) -> fundamental (0..m-1)."""
    return [(m - (a + 1) // 2, m - (b + 1) // 2) for (a, b) in pairs]


def layer_stats(cells, m):
    """返回 (nlay, [(z, actual3d, visible_left, innermost_on_diag_bool), ...])。

    layers[z] 存的是 embed 返回的 4m 个居中 3D 点坐标；len(xy) 即该层 3D 点数
    （必为 4 的倍数: 4/8/12… = 4 × fundamental cell 数）。
    """
    P, zs, layers, uniq = embed(cells, m)
    nlay = len(layers)
    rows = []
    for z in range(nlay):
        xy = layers[z]
        actual3d = len(xy)                     # 3D points in this layer
        n_cells = actual3d // 4                # fundamental cells in layer
        ys = set(y for (x, y) in xy)
        visible = len(ys)
        on_diag = any(abs(x - y) < 1e-9 for (x, y) in xy)
        rows.append((z, actual3d, visible, on_diag))
    return nlay, rows


def main():
    all_m = {}
    grid_panels = {}        # m -> (P, zs) representative solution for drawing
    bottom_dist = {}        # m -> Counter of visible_left at z=0
    norm_bins = defaultdict(lambda: defaultdict(list))   # m -> bin -> [visible]
    NB = 21
    total_sol = 0

    for m in MS:
        sols = load_known(m, cap=1000000)
        if not sols:
            print(f"m={m}: NO solutions from load_known, skip")
            continue
        # representative = load_ref if available (matches screenshot convention)
        try:
            rep = load_ref(m)
        except Exception:
            rep = odd_to_fund(sols[0], m)
        grid_panels[m] = embed(rep, m)[:2]   # (P, zs)

        per_m_rows = []
        bdist = Counter()
        for pairs in sols:
            cells = odd_to_fund(pairs, m)
            nlay, rows = layer_stats(cells, m)
            per_m_rows.append(rows)
            # bottom layer z=0
            if rows:
                bdist[rows[0][2]] += 1
            # normalized bins
            for (z, a3d, vis, diag) in rows:
                np = 0.0 if nlay == 1 else z / (nlay - 1)
                b = min(NB - 1, int(round(np * (NB - 1))))
                norm_bins[m][b].append(vis)
            total_sol += 1
        all_m[m] = per_m_rows
        bottom_dist[m] = bdist

    # ── 1) per-m 报告表（用代表性解展示每层实际/可见）─────────────────
    rep_report = {}
    for m in MS:
        if m not in grid_panels:
            continue
        P, zs = grid_panels[m]
        cells_rep = [(int(round(P[i][0] + (m - 0.5))), int(round(P[i][1] + (m - 0.5))))
                     for i in range(len(P))
                     if 0 <= P[i][0] + (m - 0.5) < m and 0 <= P[i][1] + (m - 0.5) < m]
        nlay, rows = layer_stats(cells_rep, m)
        rep_report[m] = rows

    # ── 2) 写报告 md ────────────────────────────────────────────────
    lines = []
    L = lines.append
    L("# 所有 m 的 rot4 解：3D 投影分层分析\n")
    L(f"**覆盖**: m∈{{5..19,36}}；**解总数** ≈ {total_sol}（来自 Flammenkamp 缓存 load_known）。\n")
    L("**约定**: z 层 = 到缺失中心欧氏距离排位 (z=0 最内/最底)。左视 (Y,Z) 与右视 (-Y,Z) "
      "每层可见点数**相等**（C4 轨道 Y={y,x,-y,-x}，取负不改变 distinct 个数，仅镜像）。\n")
    L("**每层两种计数**:\n")
    L("- 实际 3D 点数 = 该层 3D 点数 = 4 × fundamental cell 数（∈ {4,8,12}，C4 轨道恒 4 点）")
    L("- 投影可见点数 = 该层 4k 点里 distinct Y 的个数（∈ {2,4,8}，对角线 cell 塌成 2）\n")

    L("## 一、底层 (z=0) 可见点数分布（跨所有解）")
    L("  这回答“最下面是不是总是 2 个点”。\n")
    L("  m | nsol | vis=2 | vis=4 | vis=8 | vis=2 占比")
    L("  --|------|-------|-------|-------|----------")
    for m in MS:
        if m not in bottom_dist:
            continue
        b = bottom_dist[m]
        ns = sum(b.values())
        v2 = b.get(2, 0); v4 = b.get(4, 0); v8 = b.get(8, 0)
        L(f"  {m:2d} | {ns:4d} | {v2:5d} | {v4:5d} | {v8:5d} | {v2/ns*100:5.1f}%")

    L("\n## 二、每 m 代表性解逐层（实际3D点 / 左视可见）")
    L("  （代表性解 = mXX.json；左视=右视）\n")
    for m in MS:
        if m not in rep_report:
            continue
        L(f"### m={m}")
        L("  z | 实际3D点 | 可见 | 对角线层?")
        L("  --|---------|------|---------")
        for (z, a3d, vis, diag) in rep_report[m]:
            L(f"  {z:2d} | {a3d:7d} | {vis:4d} | {str(diag)}")
        L("")

    L("## 三、跨解聚合：按归一化层位的可见点数均值热图（见 cube_proj_heatmap.svg）")
    L("  行 = m；列 = 归一化层位 (0 最内 → 1 最外, 21 箱)；值 = 该箱所有解可见点数均值。\n")

    L("## 四、关键结论")
    L("  - 左视 == 右视（每层可见点数相等，纯镜像），故“左右”是同一个数。")
    L("  - 底层 z=0 可见点数由最内 cell 是否落在对角线 (x=±y) 决定：")
    L("    对角线 cell → Y={x,x,-x,-x} 只有 2 个值 → 投影显示 2 点；")
    L("    非对角线 cell → Y={y,x,-y,-x} 4 个值 → 投影显示 4 点。")
    L("  - 因此“最下面 2 个点”不是普遍定律，而是该解最内环恰好在对角线上的特例；")
    L("    统计上各 m 的占比见上表“vis=2 占比”。")
    L("  - 可见点数 ∈ {2,4,8}：2=对角线单 cell；4=非对角线单 cell（多数层）；")
    L("    8=该层有 2 个 cell 且 Y 集合不重叠（即径向环占据 8 的层）。从未出现 16。")

    text = "\n".join(lines)
    os.makedirs("results", exist_ok=True)
    with open("results/cube_proj_allm.md", "w") as f:
        f.write(text)

    # ── 3) 网格投影图 SVG（每个 m 一张左视）─────────────────────────
    cols = 4
    pw, ph = 175, 165
    gx, gy = 15, 28
    W = cols * (pw + gx) + gx
    rows_n = (len([m for m in MS if m in grid_panels]) + cols - 1) // cols
    H = rows_n * (ph + gy) + gy
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'font-family="sans-serif" font-size="11">']
    mm = [m for m in MS if m in grid_panels]
    for idx, m in enumerate(mm):
        P, zs = grid_panels[m]
        cx0 = gx + (idx % cols) * (pw + gx)
        cy0 = gy + (idx // cols) * (ph + gy)
        svg.append(f'<rect x="{cx0}" y="{cy0}" width="{pw}" height="{ph}" '
                   f'fill="#0e1117" stroke="#555"/>')
        svg.append(f'<text x="{cx0+4}" y="{cy0+14}" fill="#9cd" '
                   f'font-size="12">m={m} ({len(P)}pts)</text>')
        # coordinates: left view (Y, Z), Y horizontal, Z vertical (outer at top)
        ys = [p[1] for p in P]
        ymin, ymax = min(ys), max(ys)
        zmin, zmax = min(zs), max(zs)
        def mu(y):
            return cx0 + 12 + (y - ymin) / (ymax - ymin + 1e-9) * (pw - 24)
        def mv(z):
            return cy0 + ph - 14 - (z - zmin) / (zmax - zmin + 1e-9) * (ph - 30)
        # dashed horizontal lines per distinct z
        for z in sorted(set(zs)):
            cz = mv(z)
            svg.append(f'<line x1="{cx0+10}" y1="{cz:.1f}" x2="{cx0+pw-10}" '
                       f'y2="{cz:.1f}" stroke="#2a3340" stroke-width="0.5" '
                       f'stroke-dasharray="2,2"/>')
        for (x, y), z in zip(P, zs):
            svg.append(f'<circle cx="{mu(y):.1f}" cy="{mv(z):.1f}" r="2.6" '
                       f'fill="#4fc3f7" stroke="#111" stroke-width="0.4"/>')
    svg.append('</svg>')
    with open("results/cube_proj_grid.svg", "w") as f:
        f.write("\n".join(svg))

    # ── 4) 热图 SVG（m × 归一化层位箱, 均值可见点数）────────────────
    hm_ms = [m for m in MS if m in norm_bins]
    bw = 26
    hmW = gx + NB * bw + 120
    hmH = gy + len(hm_ms) * 22 + 60
    hsvg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {hmW} {hmH}" '
            f'font-family="sans-serif" font-size="10">']
    # color scale: 2 -> blue, 4 -> green, 8 -> red
    def col(v):
        if v <= 2.5:
            return "#3a6ea5"
        if v <= 4.5:
            return "#3fa34d"
        if v <= 6.5:
            return "#d9a441"
        return "#c0392b"
    hsvg.append(f'<text x="{gx}" y="16" fill="#ccc">立方体投影每层可见点数均值热图 '
                f'(行=m, 列=归一化层位 0内→1外)</text>')
    for j, m in enumerate(hm_ms):
        y0 = gy + 30 + j * 22
        hsvg.append(f'<text x="4" y="{y0+14}" fill="#9cd">{m:2d}</text>')
        for b in range(NB):
            vals = norm_bins[m].get(b, [])
            mean = sum(vals) / len(vals) if vals else 0
            x0 = gx + b * bw
            if vals:
                hsvg.append(f'<rect x="{x0}" y="{y0}" width="{bw-1}" height="20" '
                            f'fill="{col(mean)}"/>')
                hsvg.append(f'<text x="{x0+bw/2:.0f}" y="{y0+13}" fill="#fff" '
                            f'font-size="8" text-anchor="middle">{mean:.1f}</text>')
            else:
                hsvg.append(f'<rect x="{x0}" y="{y0}" width="{bw-1}" height="20" '
                            f'fill="#1a1a1a"/>')
    # legend
    ly = gy + 30 + len(hm_ms) * 22 + 14
    for k, (lab, c) in enumerate([("2", "#3a6ea5"), ("4", "#3fa34d"),
                                  ("6", "#d9a441"), ("8", "#c0392b")]):
        hsvg.append(f'<rect x="{gx+k*60}" y="{ly}" width="14" height="12" fill="{c}"/>')
        hsvg.append(f'<text x="{gx+k*60+18}" y="{ly+11}" fill="#ccc">{lab}</text>')
    hsvg.append('</svg>')
    with open("results/cube_proj_heatmap.svg", "w") as f:
        f.write("\n".join(hsvg))

    # ── 5) json 汇总 ────────────────────────────────────────────────
    summary = {
        "total_solutions": total_sol,
        "ms": MS,
        "bottom_visible_dist": {str(m): dict(bottom_dist[m]) for m in bottom_dist},
        "norm_bins_mean": {str(m): {str(b): (sum(v)/len(v) if v else None)
                                    for b, v in norm_bins[m].items()} for m in hm_ms},
    }
    with open("results/cube_proj_allm.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(text)
    print("\n[written] results/cube_proj_allm.md / .json / cube_proj_grid.svg / "
          "cube_proj_heatmap.svg")


if __name__ == "__main__":
    main()
