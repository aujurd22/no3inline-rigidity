#!/usr/bin/env python3
"""
cube_lens.py -- 把已知 2D rot4-NTIL 解按"到缺失中心的距离"升到 3D 做结构透镜。

  - 缺失中心: 奇数坐标关于 0 对称，(0,0) 非格点 -> 原点
  - z = 点到中心欧几里得距离的"排位"(最内圈->z=0 底层, 外圈->高层)
  - 观察: 每层点数/环性, 点相对中心的向量 (X,Y,z), 层间向量
  - 打乱: 移动 k 个基本域 cell, 看 3D 共线三元组数与环结构如何变化

轻量: 仅后处理已知解, 不求解。默认 m=16。
"""
import json, math, random, os, sys
from collections import defaultdict

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def lift(cells, m):
    n = 2 * m
    return [c4(c, r, n) for c in cells for r in range(4)]

def load_ref(m, base="analysis/results/solutions"):
    with open(os.path.join(base, f"m{m:02d}.json")) as f:
        return [tuple(c) for c in json.load(f)["cells"]]

def embed(cells, m):
    """返回 4m 个居中坐标 + 每层 (z) 点列表。"""
    pts = lift(cells, m)
    cen = (m - 0.5, m - 0.5)
    P = [(p[0] - cen[0], p[1] - cen[1]) for p in pts]
    dists = [math.hypot(x, y) for (x, y) in P]
    uniq = sorted(set(round(d, 6) for d in dists))
    rank = {d: i for i, d in enumerate(uniq)}
    zs = [rank[round(d, 6)] for d in dists]
    layers = defaultdict(list)
    for i, (xy, z) in enumerate(zip(P, zs)):
        layers[z].append(xy)
    return P, zs, layers, uniq

def count_3d_collinear(P, zs):
    """3D 共线三元组数 (含 z)。P 居中 (x,y), zs 层。点 = (x,y,z)。"""
    Q = [(P[i][0], P[i][1], zs[i]) for i in range(len(P))]
    bad = 0
    n = len(Q)
    for i in range(n):
        x1, y1, z1 = Q[i]
        for j in range(i + 1, n):
            x2, y2, z2 = Q[j]
            dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
            for k in range(j + 1, n):
                x3, y3, z3 = Q[k]
                # 叉积=0
                if (dy * (z3 - z1) - dz * (y3 - y1)) == 0 and \
                   (dz * (x3 - x1) - dx * (z3 - z1)) == 0 and \
                   (dx * (y3 - y1) - dy * (x3 - x1)) == 0:
                    bad += 1
    return bad

def main():
    m = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    Ks = [int(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else "2,4,8")]
    rng = random.Random(7)
    cells = load_ref(m)
    P, zs, layers, uniq = embed(cells, m)
    nlay = len(layers)
    # 结构报告
    layer_info = {}
    for z in sorted(layers):
        xy = layers[z]
        rs = [math.hypot(x, y) for (x, y) in xy]
        layer_info[z] = {
            "count": len(xy),
            "mean_radius": sum(rs) / len(rs),
            "radius_spread": max(rs) - min(rs),
        }
    # 与中心向量: 模长分布
    mods = [math.hypot(x, y, z) for (x, y), z in zip(P, zs)]
    # 层间向量 (z 与 z+1 配对, 取每对同 idx 差)
    inter = []
    for i in range(len(P)):
        if zs[i] + 1 < nlay:
            # 找同 idx 在 z+1 层的对应? 简化: 统计相邻层点对的 Δz=1 与水平位移
            pass
    base_3d = count_3d_collinear(P, zs)
    # 打乱测试
    scramble_res = {}
    for k in Ks:
        deltas = []
        for r in range(8):
            c = [tuple(x) for x in cells]
            occ = set(c)
            idxs = rng.sample(range(len(c)), min(k, len(c)))
            for i in idxs:
                while True:
                    nc = (rng.randrange(m), rng.randrange(m))
                    if nc not in occ:
                        break
                occ.discard(c[i]); occ.add(nc); c[i] = nc
            P2, zs2, _, _ = embed(c, m)
            d3 = count_3d_collinear(P2, zs2)
            deltas.append(d3 - base_3d)
        scramble_res[k] = {
            "base_3d_collinear": base_3d,
            "mean_delta_after_scramble": sum(deltas) / len(deltas),
        }
    out = {
        "m": m, "n_points": len(P), "n_layers": nlay,
        "layer_radii": [round(u, 3) for u in uniq],
        "layer_info": {str(z): v for z, v in layer_info.items()},
        "base_3d_collinear": base_3d,
        "mod_min": min(mods), "mod_max": max(mods),
        "scramble_3d": scramble_res,
    }
    os.makedirs("results", exist_ok=True)
    with open("results/cube_lens.json", "w") as f:
        json.dump(out, f, indent=2)
    # 导出点 + 画分层散点 SVG（颜色=z 层）
    pts_out = [{"x": round(P[i][0], 3), "y": round(P[i][1], 3), "z": zs[i]} for i in range(len(P))]
    with open("results/cube_points.json", "w") as f:
        json.dump({"m": m, "points": pts_out}, f, indent=2)
    # SVG: 2D 投影, 颜色按 z 层 (暖色=外层), 透明背景适配 widget
    import colorsys
    nlay = max(zs) + 1
    W, H, R = 680, 680, 300
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">']
    svg.append(f'<circle cx="{W/2}" cy="{H/2}" r="4" fill="none" stroke="#888" stroke-width="1"/>')  # 缺失中心
    svg.append(f'<text x="{W/2+8}" y="{H/2-8}" fill="#888" font-size="13">missing center (0,0)</text>')
    for i in range(len(P)):
        x, y, z = P[i][0], P[i][1], zs[i]
        cx = W / 2 + x / (m) * R
        cy = H / 2 - y / (m) * R
        rdot = 6.0
        hue = 0.62 - 0.62 * (z / max(1, nlay - 1))  # 蓝(内)->红(外)
        col = colorsys.hsv_to_rgb(max(0.0, hue), 0.85, 1.0)
        c = f'#{int(col[0]*255):02x}{int(col[1]*255):02x}{int(col[2]*255):02x}'
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rdot}" fill="{c}" stroke="#222" stroke-width="0.8"/>')
    svg.append(f'<text x="10" y="{H-10}" fill="#ccc" font-size="12">m={m}: {len(P)} pts, {nlay} concentric layers (z=dist rank), 3D-collinear={base_3d}</text>')
    svg.append('</svg>')
    with open("results/cube_scatter.svg", "w") as f:
        f.write("\n".join(svg))
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
