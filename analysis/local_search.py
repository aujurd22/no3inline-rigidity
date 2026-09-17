"""
local_search.py -- 置换子类上的模拟退火 (rot4-NTIL 启发式).

⚠️ 重要更正: 本脚本搜索**置换子类** (每行每列恰一个 cell). 但定理 2 (见
results/theorem_r9c_perm_equiv.md) 已证 2-因子 ⊃ 置换 (严格). 真实解可能
为非置换 2-因子 (m=8/12/18 实证), 故本脚本:
  - 找到解 => 合法构造性证明 (坐标可 verify_cells 独立验证);
  - 找不到 => **不**说明无解 (置换子类可能无 m=37 解, 但非置换 2-因子有).
完整攻击须用 solve_m37_r9b.py 的 2-因子模型.

目标: 找置换 pi 使 4m 个 C4 提升点无三点共线.
目标函数 bad = 共线三点组(点三元组)总数. 退火到 bad==0 即得到显式解.

增量更新: 交换 pi[a],pi[b] 只改变 cell a,b 的提升点; 仅重算涉及 a 或 b 的
cell-对 / cell-三元组贡献 (O(m^2) per move), 其余不变.

用法:
  python local_search.py --m 12 --moves 20000 --restarts 4 --seed 1   # 验证
  python local_search.py --m 37 --moves 40000 --restarts 12 --timelimit 5400 --log results/ls37.log
"""
import sys, os, json, time, math, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solve_m37_r9b import verify_cells

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def build_lift(pi, m):
    n = 2 * m
    lift = []
    for i in range(m):
        cell = (i, pi[i])
        lift.append([c4(cell, r, n) for r in range(4)])
    return lift

def pair_count(lift, p, q):
    lp = lift[p]; lq = lift[q]
    c = 0
    # 2 from p, 1 from q
    for a in range(4):
        x1, y1 = lp[a]
        for b in range(a + 1, 4):
            x2, y2 = lp[b]
            dx, dy = x2 - x1, y2 - y1
            for d in range(4):
                x3, y3 = lq[d]
                if dx * (y3 - y1) == dy * (x3 - x1):
                    c += 1
    # 2 from q, 1 from p
    for a in range(4):
        x1, y1 = lq[a]
        for b in range(a + 1, 4):
            x2, y2 = lq[b]
            dx, dy = x2 - x1, y2 - y1
            for d in range(4):
                x3, y3 = lp[d]
                if dx * (y3 - y1) == dy * (x3 - x1):
                    c += 1
    return c

def tri_count(lift, p, q, r):
    lp = lift[p]; lq = lift[q]; lr = lift[r]
    c = 0
    for a in range(4):
        x1, y1 = lp[a]
        for b in range(4):
            x2, y2 = lq[b]
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0:
                continue
            for d in range(4):
                x3, y3 = lr[d]
                if dx * (y3 - y1) == dy * (x3 - x1):
                    c += 1
    return c

def evaluate_all(lift, m):
    pair_c = {}
    tri_c = {}
    bad = 0
    for i in range(m):
        for j in range(i + 1, m):
            c = pair_count(lift, i, j)
            pair_c[(i, j)] = c
            bad += c
    for i in range(m):
        for j in range(i + 1, m):
            for k in range(j + 1, m):
                c = tri_count(lift, i, j, k)
                tri_c[(i, j, k)] = c
                bad += c
    return bad, pair_c, tri_c

def affected_keys(m, a, b):
    pairs = []
    for x in range(m):
        if x != a:
            pairs.append((a, x) if a < x else (x, a))
    for x in range(m):
        if x != b and x != a:
            pairs.append((b, x) if b < x else (x, b))
    tris = []
    # containing a not b
    rest = [x for x in range(m) if x != a and x != b]
    L = len(rest)
    for ii in range(L):
        for jj in range(ii + 1, L):
            t = tuple(sorted((a, rest[ii], rest[jj])))
            tris.append(t)
    # containing b not a (same rest list, but key includes b)
    for ii in range(L):
        for jj in range(ii + 1, L):
            t = tuple(sorted((b, rest[ii], rest[jj])))
            tris.append(t)
    # containing both a and b
    for x in rest:
        t = tuple(sorted((a, b, x)))
        tris.append(t)
    return pairs, tris

def run_once(m, rng, moves, T0, T1, start_kind="random", known=None):
    if start_kind == "welch" and m % 2 == 1:
        # primitive root for prime m (heuristic; fall back if not prime)
        try:
            # find a generator of F_m^* (needs m prime)
            phi = m - 1
            fac = {}
            nn = phi
            d = 2
            while d * d <= nn:
                while nn % d == 0:
                    fac[d] = fac.get(d, 0) + 1
                    nn //= d
                d += 1 if d == 2 else 2
            if nn > 1:
                fac[nn] = 1
            for g in range(2, m):
                ok = all(pow(g, phi // q, m) != 1 for q in fac)
                if ok:
                    pi = [(pow(g, i, m)) for i in range(m)]
                    # ensure permutation of 0..m-1: g^i mod m for i=0..m-1 with m prime gives all residues
                    if sorted(pi) == list(range(m)):
                        break
            else:
                pi = list(range(m)); rng.shuffle(pi)
            if sorted(pi) != list(range(m)):
                pi = list(range(m)); rng.shuffle(pi)
        except Exception:
            pi = list(range(m)); rng.shuffle(pi)
    elif known:
        pi = list(known)
    else:
        pi = list(range(m)); rng.shuffle(pi)

    lift = build_lift(pi, m)
    bad, pair_c, tri_c = evaluate_all(lift, m)
    best_bad = bad
    best_pi = pi[:]
    starts = []
    for mv in range(moves):
        frac = mv / moves
        T = T0 * ((T1 / T0) ** frac)
        a, b = rng.sample(range(m), 2)
        pk, tk = affected_keys(m, a, b)
        # subtract
        delta = 0
        for key in pk:
            delta -= pair_c[key]
        for key in tk:
            delta -= tri_c[key]
        # swap
        pi[a], pi[b] = pi[b], pi[a]
        build_lift_pair(lift, pi, a, m)
        build_lift_pair(lift, pi, b, m)
        # recompute & add
        for key in pk:
            c = pair_count(lift, key[0], key[1])
            pair_c[key] = c
            delta += c
        for key in tk:
            c = tri_count(lift, key[0], key[1], key[2])
            tri_c[key] = c
            delta += c
        new_bad = bad + delta
        if delta <= 0 or rng.random() < math.exp(-delta / T):
            bad = new_bad
            if bad < best_bad:
                best_bad = bad
                best_pi = pi[:]
                if bad == 0:
                    return 0, best_pi
        else:
            # revert: undo pi swap, rebuild lift, recompute affected contributions
            pi[a], pi[b] = pi[b], pi[a]
            build_lift_pair(lift, pi, a, m)
            build_lift_pair(lift, pi, b, m)
            for key in pk:
                pair_c[key] = pair_count(lift, key[0], key[1])
            for key in tk:
                tri_c[key] = tri_count(lift, key[0], key[1], key[2])
            # bad unchanged (delta was not applied)
    return best_bad, best_pi

def build_lift_pair(lift, pi, i, m):
    n = 2 * m
    cell = (i, pi[i])
    lift[i] = [c4(cell, r, n) for r in range(4)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=12)
    ap.add_argument("--moves", type=int, default=20000)
    ap.add_argument("--restarts", type=int, default=4)
    ap.add_argument("--timelimit", type=float, default=0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--start", default="random")
    ap.add_argument("--log", default="")
    ap.add_argument("--save", default="")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    log = open(args.log, "w") if args.log else None
    def say(*a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        if log:
            log.write(s + "\n"); log.flush()

    say(f"# local_search m={args.m} moves={args.moves} restarts={args.restarts} "
        f"seed={args.seed} start={args.start}")
    t_start = time.time()
    global_best = None
    global_min = None
    for rs in range(args.restarts):
        bb, bpi = run_once(args.m, rng, args.moves, T0=max(1, args.m),
                           T1=0.05, start_kind=args.start)
        say(f"  restart {rs}: best_bad={bb} pi0..5={bpi[:6]}")
        if global_min is None or bb < global_min:
            global_min = bb
            global_best = bpi[:]
        if bb == 0:
            say(f"  >>> SOLUTION FOUND at restart {rs}")
            break
        if args.timelimit and (time.time() - t_start) > args.timelimit:
            say("  timelimit reached, stopping restarts")
            break
    say(f"# DONE global_min={global_min} elapsed={time.time()-t_start:.1f}s")
    if global_best is not None and global_min == 0:
        cells = [(i, global_best[i]) for i in range(args.m)]
        vf, nc = verify_cells(cells, args.m)
        say(f"# VERIFY no3collinear={vf} points={4*args.m}")
        if args.save:
            with open(args.save, "w") as f:
                json.dump({"m": args.m, "cells": cells, "verify": vf}, f, indent=2)
            say(f"# saved -> {args.save}")
    elif global_best is not None and args.save:
        cells = [(i, global_best[i]) for i in range(args.m)]
        with open(args.save, "w") as f:
            json.dump({"m": args.m, "cells": cells, "bad": global_min}, f, indent=2)
        say(f"# saved best (bad={global_min}) -> {args.save}")

if __name__ == "__main__":
    main()
