#!/usr/bin/env python3
"""
cube_proj.py -- rot4 解 3D 嵌入的 5 视图投影 + 侧面共线分析。

  俯视/仰视 (X,Y) = 原 2D 解。
  前(X,Z) 后(-X,Z) 左(Y,Z) 右(-Y,Z): 侧面投影, Z=到缺失中心距离排位(环)。
  检查: 侧面投影里除了"同一环压成的水平带"外, 是否还有额外(斜向)共线。
"""
import json, math, os
from cube_lens import embed, load_ref

def count_2d_collinear(pts):
    """pts: list of (u,v). 返回 (总共线三元组, 水平带共线三元组(同v))。"""
    n = len(pts)
    tot = 0; horiz = 0
    for i in range(n):
        x1, y1 = pts[i]
        for j in range(i + 1, n):
            x2, y2 = pts[j]
            dx, dy = x2 - x1, y2 - y1
            for k in range(j + 1, n):
                x3, y3 = pts[k]
                if dx * (y3 - y1) == dy * (x3 - x1):
                    tot += 1
                    if y1 == y2 == y3:
                        horiz += 1
    return tot, horiz

def main():
    m = 16
    cells = load_ref(m)
    P, zs, layers, uniq = embed(cells, m)
    # 五视图点集
    top = [(x, y) for (x, y) in P]                       # (X,Y)
    front = [(x, z) for (x, y), z in zip(P, zs)]          # (X,Z)
    back = [(-x, z) for (x, y), z in zip(P, zs)]          # (-X,Z)
    left = [(y, z) for (x, y), z in zip(P, zs)]           # (Y,Z)
    right = [(-y, z) for (x, y), z in zip(P, zs)]         # (-Y,Z)

    views = {"top": top, "front": front, "back": back, "left": left, "right": right}
    analysis = {}
    for name, pts in views.items():
        tot, horiz = count_2d_collinear(pts)
        analysis[name] = {"total_collinear": tot, "horizontal_band": horiz,
                          "other_diag": tot - horiz}

    out = {"m": m, "n_points": len(P), "n_layers": len(layers),
           "views": analysis}
    os.makedirs("results", exist_ok=True)
    with open("results/cube_proj.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2, ensure_ascii=False))

    # ── 渲染 2x2 侧面 + 俯视 五视图（俯视放中上, 前/后/左/右 环绕）────────
    # 布局: 上排 俯视 | 前视 ; 下排 左视 | 右视 ; 后视用文字标注=前视镜像
    W, H = 680, 520
    panels = [
        ("top", top, 20, 20, "俯视 (X,Y) = 原解"),
        ("front", front, 350, 20, "前视 (X,Z)"),
        ("left", left, 20, 270, "左视 (Y,Z)"),
        ("right", right, 350, 270, "右视 (-Y,Z)"),
    ]
    PW, PH = 310, 230
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">']
    for name, pts, ox, oy, title in panels:
        svg.append(f'<rect x="{ox}" y="{oy}" width="{PW}" height="{PH}" fill="#0e1117" stroke="#444" stroke-width="1"/>')
        svg.append(f'<text x="{ox+6}" y="{oy+16}" fill="#ccc" font-size="13">{title}</text>')
        # 坐标范围
        us = [p[0] for p in pts]; vs = [p[1] for p in pts]
        umin, umax = min(us), max(us); vmin, vmax = min(vs), max(vs)
        def mapu(u):
            return ox + 20 + (u - umin) / (umax - umin + 1e-9) * (PW - 40)
        def mapv(v):
            return oy + PH - 20 - (v - vmin) / (vmax - vmin + 1e-9) * (PH - 40)
        for (u, v) in pts:
            cu, cv = mapu(u), mapv(v)
            svg.append(f'<circle cx="{cu:.1f}" cy="{cv:.1f}" r="3.5" fill="#4fc3f7" stroke="#222" stroke-width="0.6"/>')
        # 水平带引导线(同 v)
        vset = sorted(set(vs))
        for v in vset:
            cv = mapv(v)
            svg.append(f'<line x1="{ox+20}" y1="{cv:.1f}" x2="{ox+PW-20}" y2="{cv:.1f}" stroke="#333" stroke-width="0.5" stroke-dasharray="3,3"/>')
    svg.append(f'<text x="350" y="{270-8}" fill="#aaa" font-size="11">后视(-X,Z)=前视 X 镜像; 仰视=俯视; 四侧由 C4 对称仅 2 种本质模式</text>')
    svg.append('</svg>')
    with open("results/cube_proj.svg", "w") as f:
        f.write("\n".join(svg))
    print("# saved -> results/cube_proj.svg")

if __name__ == "__main__":
    main()
