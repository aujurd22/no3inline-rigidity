#!/usr/bin/env python3
"""
C4-symmetric Costas arrays as an exact CP-SAT (Theorem R8-C, linear CSP).

A C4-rotation-symmetric Costas array of order n = 4m is encoded by `m` cells in
the (2m)x(2m) fundamental quadrant.  The C4-orbit of each cell gives 4 dots on
the n x n board; the full dot set is the union over the m chosen cells.  The
Costas condition (all (4m)(4m-1) ordered displacement vectors distinct) is
*linear* in the cell coordinates (R8-C), hence an exact CP-SAT:

  * sum(sel) = m
  * each board row / column contains exactly one dot  (permutation)
  * for each displacement-vector code value v: at most one active ordered pair
    of dots has that displacement  (Costas / 2D Sidon)

This is the Costas analogue of `cpsat_m37.py` (which handles the *quadratic*
rot4-NTIL case).  An UNSAT result at a given m means no C4-symmetric Costas
array of order 4m exists.

Usage:
  python cpsat_costas_symmetric.py --m 5          # single order
  python cpsat_costas_symmetric.py --sweep 1 9    # m = 1..8 (orders 4..32)
"""
import argparse, sys, time

try:
    from ortools.sat.python import cp_model
    HAVE = True
except Exception:
    HAVE = False
    print("OR-Tools not available", file=sys.stderr)


def dot(p, t, N):
    """C4^r rotation of cell p=(x,y) on an N x N board (center (N-1)/2)."""
    x, y = p
    if t == 0:
        return (x, y)
    if t == 1:
        return (N - 1 - y, x)
    if t == 2:
        return (N - 1 - x, N - 1 - y)
    return (y, N - 1 - x)


def build_and_solve(m, timelimit=300.0, workers=8):
    n = 4 * m
    N = n
    q = 2 * m                      # fundamental quadrant side
    quad = [(x, y) for x in range(q) for y in range(q)]
    Q = len(quad)
    # index cell positions
    cidx = {p: i for i, p in enumerate(quad)}

    model = cp_model.CpModel()
    sel = [model.NewBoolVar(f"sel{i}") for i in range(Q)]
    model.Add(sum(sel) == m)

    # precompute dot coords for every (cell, rotation)
    dcoord = {}
    for ci, p in enumerate(quad):
        for t in range(4):
            dcoord[(ci, t)] = dot(p, t, N)

    # permutation: each row and each column has exactly one dot.
    # dot (ci,t) is active iff sel[ci]==1, and contributes its row/col.
    for r in range(N):
        terms = [sel[ci] for ci in range(Q) for t in range(4) if dcoord[(ci, t)][0] == r]
        model.Add(sum(terms) == 1)
    for c in range(N):
        terms = [sel[ci] for ci in range(Q) for t in range(4) if dcoord[(ci, t)][1] == c]
        model.Add(sum(terms) == 1)

    # Costas: group all ordered pairs of dots by displacement code; require at
    # most one ACTIVE pair per code.  active((ci,t),(cj,s)) = sel[ci] (if ci==cj)
    # or sel[ci]*sel[cj] (if ci!=cj).
    bycode = {}
    R = 2 * N + 1
    off = N
    # total candidate dots = 4Q
    for ai in range(Q):
        for at in range(4):
            for bj in range(Q):
                for bt in range(4):
                    if ai == bj and at == bt:
                        continue
                    A = dcoord[(ai, at)]
                    B = dcoord[(bj, bt)]
                    dx, dy = B[0] - A[0], B[1] - A[1]
                    code = (dx + off) * R + (dy + off)
                    bycode.setdefault(code, []).append((ai, bj))

    # product vars cache for ci!=cj pairs
    prod = {}
    def prod_var(ci, cj):
        if ci == cj:
            return sel[ci]
        key = (ci, cj) if ci < cj else (cj, ci)
        if key not in prod:
            v = model.NewBoolVar(f"p{key[0]}_{key[1]}")
            model.Add(v <= sel[key[0]])
            model.Add(v <= sel[key[1]])
            model.Add(v >= sel[key[0]] + sel[key[1]] - 1)
            prod[key] = v
        return prod[key]

    for code, pairs in bycode.items():
        terms = [prod_var(ai, bj) for (ai, bj) in pairs]
        model.Add(sum(terms) <= 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timelimit
    solver.parameters.num_search_workers = workers
    st = solver.Solve(model)
    status = solver.StatusName(st)
    cells = [quad[i] for i in range(Q) if solver.Value(sel[i]) == 1] if status in ("FEASIBLE", "OPTIMAL") else []
    return status, cells


def is_costas_from_cells(cells, m):
    n = 4 * m
    N = n
    dots = []
    for p in cells:
        dots.extend(dot(p, t, N) for t in range(4))
    rows = [d[0] for d in dots]; cols = [d[1] for d in dots]
    if len(set(rows)) != n or len(set(cols)) != n:
        return False, "not a permutation"
    seen = set()
    for i in range(len(dots)):
        for j in range(len(dots)):
            if i == j: continue
            d = (dots[j][0] - dots[i][0], dots[j][1] - dots[i][1])
            if d in seen: return False, f"repeat displacement {d}"
            seen.add(d)
    return True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=0)
    ap.add_argument("--sweep", type=int, nargs=2, default=None,
                    metavar=("M0", "M1"), help="sweep m=M0..M1-1")
    ap.add_argument("--timelimit", type=float, default=300.0)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    if not HAVE:
        print("no OR-Tools"); return
    ms = list(range(args.sweep[0], args.sweep[1])) if args.sweep else [args.m]
    if not ms:
        ms = [5]
    print(f"=== C4-symmetric Costas CP-SAT (Theorem R8-C, linear CSP) ===")
    for m in ms:
        if m < 1:
            continue
        t0 = time.time()
        status, cells = build_and_solve(m, args.timelimit, args.workers)
        ok = False
        if cells:
            ok, _ = is_costas_from_cells(cells, m)
        print(f"  m={m} (order n={4*m}): status={status} found={len(cells)} "
              f"verify={ok} [{time.time()-t0:.1f}s]"
              + (f" cells={cells}" if cells else ""))
        if cells and ok:
            print(f"  *** C4-SYMMETRIC COSTAS ARRAY OF ORDER {4*m} FOUND ***")


if __name__ == "__main__":
    main()
