#!/usr/bin/env python3
"""
ls_radial.py -- 验证「径向层」是否真能帮构造 (proposal 1 的实用化测试)

假设: 解近似同心(每环1 cell)。若如此, 用「每环取1点」的合法起点做初始化,
应比随机初始化更容易降到 bad=0。本脚本在小 m 上对比两种初始化 + 相同 SA 下降的成功率。

坐标约定复用 quadratic_sidon_completeness.c4 (奇数坐标 + C4 提升)。
"""
import os, json, math, random, argparse
from collections import defaultdict

def c4(p, r, N):
    x, y = p
    return [(x, y), (N-1-y, x), (N-1-x, N-1-y), (y, N-1-x)][r]

def lift(cells, m):
    n = 2*m
    return [c4(c, r, n) for c in cells for r in range(4)]

def brute_collinear(cells, m):
    pts = lift(cells, m)
    P = len(pts)
    for i in range(P):
        x1,y1 = pts[i]
        for j in range(i+1,P):
            x2,y2 = pts[j]
            dx,dy = x2-x1, y2-y1
            for k in range(j+1,P):
                if dx*(pts[k][1]-y1) == dy*(pts[k][0]-x1):
                    return True
    return False

def count_bad(cells, m):
    pts = lift(cells, m)
    P = len(pts); bad = 0
    for i in range(P):
        x1,y1 = pts[i]
        for j in range(i+1,P):
            x2,y2 = pts[j]
            dx,dy = x2-x1, y2-y1
            for k in range(j+1,P):
                if dx*(pts[k][1]-y1) == dy*(pts[k][0]-x1):
                    bad += 1
    return bad

def rings_of(m):
    rd = defaultdict(list)
    for x in range(m):
        for y in range(m):
            d = (m-2*x-1)**2 + (m-2*y-1)**2
            rd[d].append((x,y))
    return rd

def concentric_init(m, rng):
    rd = rings_of(m)
    keys = list(rd.keys())
    rng.shuffle(keys)
    cells = []
    for k in keys:
        if len(cells) >= m: break
        cells.append(rng.choice(rd[k]))
    # 若环数 < m, 补随机(不应发生, R>>m)
    while len(cells) < m:
        cells.append((rng.randrange(m), rng.randrange(m)))
    return cells[:m]

def random_init(m, rng):
    cells = set()
    while len(cells) < m:
        cells.add((rng.randrange(m), rng.randrange(m)))
    return list(cells)

def sa_descent(cells0, m, iters, rng, T0=2.0, T1=0.2):
    cells = list(cells0)
    occ = set(cells)
    bad = count_bad(cells, m)
    best = bad; best_cells = list(cells)
    if bad == 0:
        return True, True, 0, best_cells
    for it in range(iters):
        T = T0 * ((T1/T0)**(it/iters))
        i = rng.randrange(m)
        old = cells[i]
        while True:
            nc = (rng.randrange(m), rng.randrange(m))
            if nc not in occ: break
        cells[i] = nc; occ.discard(old); occ.add(nc)
        nb = count_bad(cells, m)
        delta = nb - bad
        if delta <= 0 or rng.random() < math.exp(-delta/T):
            bad = nb
            if bad < best:
                best = bad; best_cells = list(cells)
        else:
            cells[i] = old; occ.discard(nc); occ.add(old)
        if best == 0:
            break
    solved = (best == 0)
    verified = solved and (not brute_collinear(best_cells, m))
    return solved, verified, best, best_cells

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", default="8,10,12,14,16")
    ap.add_argument("--restarts", type=int, default=20)
    ap.add_argument("--iters", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="results/radial_init_test.json")
    a = ap.parse_args()
    ms = [int(x) for x in a.ms.split(",")]
    rng = random.Random(a.seed)
    out = {}
    for m in ms:
        row = {}
        for kind in ("random", "concentric"):
            succ = 0; minbad = []
            for r in range(a.restarts):
                init = random_init(m,rng) if kind=="random" else concentric_init(m,rng)
                s,v,b,bc = sa_descent(init, m, a.iters, rng)
                if s and v: succ += 1
                minbad.append(b)
            row[kind] = {"success": succ, "rate": succ/a.restarts,
                         "minbad_avg": sum(minbad)/len(minbad)}
            print(f"m={m} {kind:11s}: {succ}/{a.restarts}  minbad_avg={sum(minbad)/len(minbad):.1f}", flush=True)
        out[m] = row
    os.makedirs("results", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2)
    print("写入", a.out)

if __name__ == "__main__":
    main()
