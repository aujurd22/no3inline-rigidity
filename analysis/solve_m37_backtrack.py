"""
solve_m37_backtrack.py
======================
Faster exact attack on m=37 (n=74, C4-symmetric) No-Three-In-Line, operating
DIRECTLY in the proven-correct quadratic space of R8 (the (X)+(S) determinant
system), with *incremental* pruning -- instead of the 1.26M pre-enumerated
per-line linear constraints used by cpsat_symmetric_ntil.py.

Why this can be faster:
  - R8 proved rot4-NTIL <=> distinct m-subset of the m x m fundamental quadrant
    satisfying (X)+(S).  The per-line model *expands* (X)+(S) into ~1.26M linear
    at-most-2 constraints.  Here we keep the quadratic forms and prune
    incrementally: when we add cell k we only test triples/pairs involving k.
  - Additional cheap necessary pruner: FDR linear a-b Sidon (R1) -- redundant for
    the equivalence but extremely fast to enforce.

Pruning data (memoised, computed lazily during search):
  pairX[(i,j)]  = set of cells k such that (i,j,k) is collinear under SOME
                  rotation combo (i gets r1, j gets r2, k gets r3).
  pairS[(i,j)]  = True iff cell i's two rotation images + cell j's one image are
                  collinear under some (r1,r2,r3)  (i = double cell, j = single).

Usage:
  python solve_m37_backtrack.py --m 37 --timelimit 3600 --restarts 200
"""
import os, sys, time, argparse, random
from collections import defaultdict
import math

N = None  # board side = 2m, set per run

# ── C4 rotation (same convention as quadratic_sidon_completeness.py) ──
def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def inv_rot(P, r, N):
    # cell c with lift[c][r] == P  ->  c = c4(P, (4-r)%4, N)
    return c4(P, (4 - r) % 4, N)

# ── global precomputed tables (per m) ──
LIFT = []          # LIFT[i] = [c4(cell_i,0..3)]
PAIRX = {}         # memoised X bad-third-cell sets
PAIRS = {}         # memoised S booleans
M = 0

def build(m):
    global N, LIFT, PAIRX, PAIRS, M
    N = 2 * m
    M = m
    LIFT = []
    for idx in range(m * m):
        x, y = idx // m, idx % m
        LIFT.append([c4((x, y), r, N) for r in range(4)])
    PAIRX = {}
    PAIRS = {}

def pair_x_bad(i, j):
    """set of cells k (k!=i,j) collinear with (i,j) under some rotation combo
    (i->r1, j->r2, k->r3).  Computed lazily + memoised."""
    key = (i, j)
    if key in PAIRX:
        return PAIRX[key]
    bad = set()
    for r1 in range(4):
        p1 = LIFT[i][r1]
        for r2 in range(4):
            p2 = LIFT[j][r2]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            if dx == 0 and dy == 0:
                continue
            g = math.gcd(abs(dx), abs(dy))
            sx, sy = dx // g, dy // g
            # t range so that p1 + t*(sx,sy) stays in [0,N-1]^2
            tmin, tmax = -10**9, 10**9
            for coord, s in ((p1[0], sx), (p1[1], sy)):
                if s > 0:
                    tmin = max(tmin, -(coord) // s)
                    tmax = min(tmax, (N - 1 - coord) // s)
                elif s < 0:
                    tmin = max(tmin, (N - 1 - coord) // s)
                    tmax = min(tmax, -(coord) // s)
            pts = [p1, p2]
            for t in range(tmin, tmax + 1):
                P = (p1[0] + t * sx, p1[1] + t * sy)
                if P in pts:
                    continue
                for r3 in range(4):
                    c = inv_rot(P, r3, N)
                    cx, cy = c
                    if 0 <= cx < M and 0 <= cy < M:
                        ci = cx * M + cy
                        if ci != i and ci != j:
                            bad.add(ci)
    PAIRX[key] = bad
    return bad

def pair_s_bad(i, j):
    """True iff cell i (two images r1<r2) + cell j (image r3) collinear for
    some (r1,r2,r3).  i = double cell, j = single cell."""
    key = (i, j)
    if key in PAIRS:
        return PAIRS[key]
    res = False
    for r1 in range(4):
        for r2 in range(r1 + 1, 4):
            p1 = LIFT[i][r1]; p2 = LIFT[i][r2]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            if dx == 0 and dy == 0:
                continue
            for r3 in range(4):
                p3 = LIFT[j][r3]
                if p3 == p1 or p3 == p2:
                    continue
                if dx * (p3[1] - p1[1]) == dy * (p3[0] - p1[0]):
                    res = True
                    break
            if res:
                break
        if res:
            break
    PAIRS[key] = res
    return res

# ── FDR (linear a-b Sidon) pruner ──
def cell_diff(idx):
    x, y = idx // M, idx % M
    a = 2 * (M - x) - 1
    b = 2 * (M - y) - 1
    return a - b

def solve(m, timelimit, restarts, seed=0):
    build(m)
    rng = random.Random(seed)
    start = time.time()
    deadline = start + timelimit
    nodes = [0]
    best_depth = [0]
    r3_global = 0  # placeholder; real impl below uses nested loops

    def backtrack(chosen, fdr_cnt, avail):
        if time.time() > deadline:
            return None
        nodes[0] += 1
        d = len(chosen)
        if d > best_depth[0]:
            best_depth[0] = d
        if d == m:
            return list(chosen)
        cands = []
        for k in avail:
            if k in chosen:
                continue
            dk = cell_diff(k)
            if fdr_cnt.get(dk, 0) + fdr_cnt.get(-dk, 0) >= 2:
                continue
            ok = True
            for i in chosen:
                if pair_s_bad(i, k) or pair_s_bad(k, i):
                    ok = False
                    break
            if not ok:
                continue
            ch = list(chosen)
            nch = len(ch)
            broken = False
            for a in range(nch):
                ia = ch[a]
                for b in range(a + 1, nch):
                    ib = ch[b]
                    if k in pair_x_bad(ia, ib) or k in pair_x_bad(ib, ia):
                        broken = True
                        break
                if broken:
                    break
            if broken:
                continue
            cands.append(k)
        if not cands:
            return None
        rng.shuffle(cands)
        for k in cands:
            chosen.add(k)
            fdr_cnt[cell_diff(k)] = fdr_cnt.get(cell_diff(k), 0) + 1
            res = backtrack(chosen, fdr_cnt, avail)
            if res is not None:
                return res
            fdr_cnt[cell_diff(k)] -= 1
            if fdr_cnt[cell_diff(k)] == 0:
                del fdr_cnt[cell_diff(k)]
            chosen.discard(k)
            if time.time() > deadline:
                return None
        return None

    for rs in range(restarts):
        if time.time() > deadline:
            break
        chosen = set()
        fdr_cnt = defaultdict(int)
        avail = list(range(m * m))
        rng.shuffle(avail)
        res = backtrack(chosen, fdr_cnt, avail)
        if res is not None:
            return res, nodes[0], best_depth[0], rs
        print(f"[restart {rs}] no solution; nodes={nodes[0]} best_depth={best_depth[0]} "
              f"t={time.time()-start:.1f}s", flush=True)
    return None, nodes[0], best_depth[0], restarts

def verify(cells, m):
    n = 2 * m
    lifted = set()
    for idx in cells:
        x, y = idx // m, idx % m
        for r in range(4):
            lifted.add(c4((x, y), r, n))
    pl = list(lifted)
    for i in range(len(pl)):
        x1, y1 = pl[i]
        for j in range(i + 1, len(pl)):
            x2, y2 = pl[j]
            dx, dy = x2 - x1, y2 - y1
            for k in range(j + 1, len(pl)):
                x3, y3 = pl[k]
                if dx * (y3 - y1) == dy * (x3 - x1):
                    return False, (pl[i], pl[j], pl[k])
    return True, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--m', type=int, default=37)
    ap.add_argument('--timelimit', type=int, default=3600)
    ap.add_argument('--restarts', type=int, default=50)
    ap.add_argument('--seed', type=int, default=12345)
    args = ap.parse_args()
    print(f"[start] m={args.m} timelimit={args.timelimit}s restarts={args.restarts} "
          f"cells={args.m*args.m}", flush=True)
    t0 = time.time()
    res, nodes, best, rs = solve(args.m, args.timelimit, args.restarts, args.seed)
    dt = time.time() - t0
    if res is not None:
        ok, info = verify(res, args.m)
        print(f"[FOUND] restart={rs} nodes={nodes} best_depth={best} t={dt:.1f}s "
              f"verify_ntil={ok}", flush=True)
        out = "results/m37_backtrack_solution.txt"
        with open(out, 'w') as f:
            f.write(" ".join(str(c) for c in sorted(res)))
            f.write(f"\n# verify_ntil={ok} nodes={nodes} t={dt:.1f}s restart={rs}\n")
        print(f"[saved] {out}", flush=True)
    else:
        print(f"[TIMEOUT/UNSAT-not-proven] nodes={nodes} best_depth={best} t={dt:.1f}s", flush=True)

if __name__ == '__main__':
    main()
