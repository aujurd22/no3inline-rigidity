#!/usr/bin/env python3
"""
local_search_fix.py -- 忠实实现用户提出的构造思路（带理论先验的局部搜索）:

  1. 先固定一些点（anchors，按已知理论不移动）
  2. 随机 / 高概率区 放上其余点
  3. 看共线三元组数量 bad
  4. "移动一个点，看 bad 是否下降；下降就留，再移另一个" -> 贪心/模拟退火下降
  5. bad==0 即得到一个经验可验证的 rot4-NTIL 解（由 R9b 定理自动是 2-因子）

设计要点（与已验证坐标约定一致，见 solve_m37_r9b / quadratic_sidon_completeness）:
  - 基本域 cell (x,y) in [0,m),  lifted = c4(cell,r,2m) for r=0..3  -> 4m 点
  - 共线判定: 整数叉积 dx*(y3-y1)==dy*(x3-x1)
  - 解的定义: 4m 个 C4 对称点无三点共线 == rot4-NTIL（定理保证是 2-因子）
  - 不 import ortools（避免环境依赖）

运行: python local_search_fix.py            # 小 m 规律扫描
      python local_search_fix.py --m 8 --mode sa --init highprob --anchors 0.4 --iters 4000
"""
import sys, os, json, time, math, random, argparse
from collections import defaultdict

# ── 内联坐标约定（与 quadratic_sidon_completeness.c4 完全一致）─────────────
def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def lift(cells, m):
    """返回 4m 个提升点（list of (x,y)）。cell 互不相同 => 4m 互不相同。"""
    n = 2 * m
    pts = []
    for (x, y) in cells:
        for r in range(4):
            pts.append(c4((x, y), r, n))
    return pts

def count_bad(cells, m):
    """共线三元组总数（一条含 k 点的线贡献 C(k,3)）。bad==0 => 无三点共线。"""
    pts = lift(cells, m)
    P = len(pts)
    bad = 0
    for i in range(P):
        x1, y1 = pts[i]
        for j in range(i + 1, P):
            x2, y2 = pts[j]
            dx, dy = x2 - x1, y2 - y1
            for k in range(j + 1, P):
                if dx * (pts[k][1] - y1) == dy * (pts[k][0] - x1):
                    bad += 1
    return bad

def brute_collinear(cells, m):
    """独立验证（与 verify_cells 一致的布尔真值）。"""
    pts = lift(cells, m)
    P = len(pts)
    for i in range(P):
        x1, y1 = pts[i]
        for j in range(i + 1, P):
            x2, y2 = pts[j]
            dx, dy = x2 - x1, y2 - y1
            for k in range(j + 1, P):
                if dx * (pts[k][1] - y1) == dy * (pts[k][0] - x1):
                    return True
    return False

# ── 理论先验 ──────────────────────────────────────────────────────────────
def prior_weight(x, y, m):
    """高概率区先验: 避开主对角线(x==y)，偏好中环(mid-ring)。"""
    w = 1.0
    if x == y:
        w *= 0.12
    c = (m - 1) / 2.0
    rx = abs(x - c) / (c + 1e-9)
    ry = abs(y - c) / (c + 1e-9)
    rm = (rx + ry) / 2.0
    mid = math.exp(-((rm - 0.62) ** 2) / (2 * 0.22 * 0.22))  # peak ~0.62
    w *= (0.25 + 0.75 * mid)
    return w

def build_prior_table(m):
    tbl = {}
    tot = 0.0
    for x in range(m):
        for y in range(m):
            w = prior_weight(x, y, m)
            tbl[(x, y)] = (w, tot)
            tot += w
    return tbl, tot

def sample_by_prior(tbl, tot, occupied):
    """按先验权重抽样一个未被占用的 cell。"""
    while True:
        r = random.random() * tot
        # 线性扫描（m 小，足够快）
        for (x, y), (w, acc) in tbl.items():
            if acc + w >= r:
                if (x, y) not in occupied:
                    return (x, y)
                break

def diffs_sidon_ok(cells):
    """FDR/Part-I: 差异 a-b 的 Sidon 条件（必要）。a-b = 2(y-x)。

    对任意非零 d: 出现次数(d) + 出现次数(-d) 应 <= 2（即每个对称差异对至多 2 次）。
    d==0 自身可任意多次（主对角 cell 的对称差）。"""
    cc = defaultdict(int)
    for (x, y) in cells:
        cc[2 * (y - x)] += 1
    seen = set()
    for d in list(cc.keys()):
        if d == 0 or d in seen:
            continue
        if cc[d] + cc.get(-d, 0) > 2:
            return False
        seen.add(-d)
    return True

# ── 初始化 ────────────────────────────────────────────────────────────────
def init_random(m, rng):
    occ = set()
    cells = []
    while len(cells) < m:
        c = (rng.randrange(m), rng.randrange(m))
        if c not in occ:
            occ.add(c); cells.append(c)
    return cells

def init_highprob(m, rng, tbl, tot):
    occ = set()
    cells = []
    while len(cells) < m:
        c = sample_by_prior(tbl, tot, occ)
        occ.add(c); cells.append(c)
    return cells

def init_sidon(m, rng):
    """贪心构造满足 Sidon 差异集的初值（理论固定）。"""
    occ = set()
    cells = []
    candidates = [(x, y) for x in range(m) for y in range(m)]
    rng.shuffle(candidates)
    for c in candidates:
        if c in occ:
            continue
        trial = cells + [c]
        if diffs_sidon_ok(trial):
            occ.add(c); cells.append(c)
            if len(cells) == m:
                break
    # 若不够 m，补随机
    while len(cells) < m:
        c = (rng.randrange(m), rng.randrange(m))
        if c not in occ:
            occ.add(c); cells.append(c)
    return cells

# ── 单次运行 ──────────────────────────────────────────────────────────────
def run_once(m, rng, mode, init_kind, anchors, iters, T0, T1,
             sidon_filter, tbl, tot):
    if init_kind == "highprob":
        cells = init_highprob(m, rng, tbl, tot)
    elif init_kind == "sidon":
        cells = init_sidon(m, rng)
    else:
        cells = init_random(m, rng)
    occ = set(cells)
    # 锚点：随机固定一部分（不移动）
    n_anchor = int(round(anchors * m))
    anchor_set = set(rng.sample(range(m), n_anchor)) if n_anchor > 0 else set()
    free = [i for i in range(m) if i not in anchor_set]

    bad = count_bad(cells, m)
    best = bad
    best_cells = list(cells)
    traj = [bad]
    stall = 0
    for it in range(iters):
        if not free:
            break
        frac = it / iters if iters else 0
        T = T0 * ((T1 / T0) ** frac) if mode == "sa" else 0.0
        k = rng.choice(free)
        old = cells[k]
        # 选新位置
        if init_kind == "highprob":
            new = sample_by_prior(tbl, tot, occ - {old})
        else:
            while True:
                new = (rng.randrange(m), rng.randrange(m))
                if new != old and new not in (occ - {old}):
                    break
        if sidon_filter:
            trial = list(cells); trial[k] = new
            if not diffs_sidon_ok(trial):
                continue
        cells[k] = new
        occ.discard(old); occ.add(new)
        nb = count_bad(cells, m)
        delta = nb - bad
        accept = False
        if mode == "greedy":
            accept = (delta < 0)
        else:
            accept = (delta <= 0) or (rng.random() < math.exp(-delta / T) if T > 0 else False)
        if accept:
            bad = nb
            stall = 0
            if bad < best:
                best = bad; best_cells = list(cells)
                if bad == 0:
                    break
        else:
            cells[k] = old
            occ.discard(new); occ.add(old)
            stall += 1
        if it % 200 == 0:
            traj.append(bad)
    solved = (best == 0)
    verified = False
    if solved:
        verified = not brute_collinear(best_cells, m)
    return {
        "solved": solved, "verified": verified, "final_bad": best,
        "best_cells": best_cells, "traj": traj,
        "iters": iters, "anchors": anchors, "init": init_kind,
        "mode": mode, "sidon_filter": sidon_filter,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=0)
    ap.add_argument("--mode", default="sa", choices=["greedy", "sa"])
    ap.add_argument("--init", default="random", choices=["random", "highprob", "sidon"])
    ap.add_argument("--anchors", type=float, default=0.0)
    ap.add_argument("--iters", type=int, default=3000)
    ap.add_argument("--restarts", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sidon-filter", action="store_true")
    ap.add_argument("--out", default="results/local_search_fix.json")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    if args.m > 0:
        ms = [args.m]
    else:
        ms = [4, 5, 6, 7, 8]

    results = {}
    for m in ms:
        tbl, tot = build_prior_table(m)
        T0 = max(2.0, m * 1.0); T1 = 0.2
        rec = run_once(m, rng, args.mode, args.init, args.anchors,
                       args.iters, T0, T1, args.sidon_filter, tbl, tot)
        print(f"m={m} {args.mode}/{args.init}/anc={args.anchors}"
              f" sidonF={args.sidon_filter}: solved={rec['solved']} "
              f"verified={rec['verified']} final_bad={rec['final_bad']} "
              f"traj_tail={rec['traj'][-3:]}", flush=True)
        results[m] = rec
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump({"args": vars(args), "results": results}, f, indent=2)
    print(f"# saved -> {args.out}")

if __name__ == "__main__":
    main()
