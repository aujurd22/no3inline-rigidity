#!/usr/bin/env python3
"""
concentric_test.py -- 验证"rot4-NTIL 解是否每个距离环恰好一个 cell"的普适结构定律。

动机(用户 3D 发散 + 我的主动推断):
  3D 透镜显示 m=16 解每层 4 点、radius_spread=0(完美同心)。若此"每环一 cell"
  对所有 m 成立, 则是给 m=37 的全新构造约束: 搜索从 m 选 m 个 cell(从 m^2 组合)
  降为"每个距离环选恰好 1 个", 变量量骤减。等价于把解空间投影到"环分配"粗粒度。

同时重算 side-view (X,Z)/(Y,Z) 共线数, 验证它作为"有序度 order parameter"的稳健性
(完美解应有大量斜向共线, 打乱则掉)。

坐标约定严格复用 quadratic_sidon_completeness.c4。
"""
import os, json, math
from collections import defaultdict, Counter

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def lift(cells, m):
    n = 2 * m
    pts = []
    for (x, y) in cells:
        for r in range(4):
            pts.append(c4((x, y), r, n))
    return pts

def dd_center(pt, m):
    # 到 C4 旋转中心(m,m)的精确平方距离(奇数坐标下, 中心在 m)。
    # 注意: 必须距旋转中心而非原点, 否则同一 cell 的 4 个 lift 距离不同, 环分类错误。
    x, y = pt
    return (x - m) * (x - m) + (y - m) * (y - m)

def side_collinear_count(pts, m, axis):
    # 投影到 (axis_coord, z), z = 到中心距离 rank
    # axis='x' -> (X, z); axis='y' -> (Y, z)
    dvals = [dd_center(p, m) for p in pts]
    # 离散化 rank: 用排序后的唯一距离索引
    uniq = sorted(set(dvals))
    zmap = {d: i for i, d in enumerate(uniq)}
    zs = [zmap[d] for d in dvals]
    proj = []
    for i, p in enumerate(pts):
        coord = p[0] if axis == 'x' else p[1]
        proj.append((coord, zs[i], i))
    P = len(proj)
    cnt = 0
    diag = 0  # 非水平(不同 z)的共线
    for i in range(P):
        xi, zi, _ = proj[i]
        for j in range(i + 1, P):
            xj, zj, _ = proj[j]
            dx = xj - xi; dz = zj - zi
            for k in range(j + 1, P):
                xk, zk, _ = proj[k]
                if dx * (zk - zi) == dz * (xk - xi):
                    cnt += 1
                    if not (zi == zj == zk):
                        diag += 1
    return cnt, diag

def analyze(m, cells):
    n = 2 * m
    pts = lift(cells, m)
    # 每 cell 的距离环
    ring_of_cell = {}
    for (x, y) in cells:
        # cell 的 4 个 lift 距离相同
        d = dd_center(c4((x, y), 0, n), m)
        ring_of_cell[(x, y)] = d
    ring_counts = Counter(ring_of_cell.values())
    n_rings = len(ring_counts)
    max_per_ring = max(ring_counts.values())
    perfectly_concentric = (n_rings == len(cells))  # 每环恰好 1 cell
    # side view
    cnt_x, diag_x = side_collinear_count(pts, m, 'x')
    cnt_y, diag_y = side_collinear_count(pts, m, 'y')
    return {
        "m": m,
        "ncells": len(cells),
        "n_rings": n_rings,
        "max_per_ring": max_per_ring,
        "per_ring_hist": dict(sorted(ring_counts.items())),
        "perfectly_concentric": perfectly_concentric,
        "side_collinear_x": cnt_x,
        "side_diag_x": diag_x,
        "side_collinear_y": cnt_y,
        "side_diag_y": diag_y,
    }

def main():
    base = "analysis/results/solutions"
    files = sorted(os.listdir(base))
    rows = []
    for fn in files:
        if not fn.endswith(".json"):
            continue
        m = int(fn[1:3])
        with open(os.path.join(base, fn)) as f:
            d = json.load(f)
        cells = [tuple(c) for c in d["cells"]]
        rows.append(analyze(m, cells))
    # 汇总
    pc = sum(1 for r in rows if r["perfectly_concentric"])
    print(f"载入 {len(rows)} 个解")
    print(f"完美同心(每环恰好1 cell): {pc}/{len(rows)} = {pc/len(rows):.2%}")
    print(f"max_per_ring 分布: {Counter(r['max_per_ring'] for r in rows)}")
    print()
    print(f"{'m':>3} {'cells':>5} {'rings':>5} {'max/ring':>8} {'concentric':>10} {'sideX':>6} {'diagX':>6}")
    for r in rows:
        print(f"{r['m']:>3} {r['ncells']:>5} {r['n_rings']:>5} {r['max_per_ring']:>8} "
              f"{str(r['perfectly_concentric']):>10} {r['side_collinear_x']:>6} {r['side_diag_x']:>6}")
    out = {"rows": rows, "perfectly_concentric_count": pc,
           "total": len(rows),
           "max_per_ring_dist": dict(Counter(r['max_per_ring'] for r in rows))}
    os.makedirs("results", exist_ok=True)
    with open("results/concentric_test.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\n写入 results/concentric_test.json")

if __name__ == "__main__":
    main()
