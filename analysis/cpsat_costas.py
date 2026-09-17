#!/usr/bin/env python3
"""Exact CP-SAT encoder for the general Costas array problem.

A Costas array of order n is a permutation pi of {0..n-1} whose n(n-1) ordered
displacement vectors (pi(j)-pi(i), j-i) are all distinct.  Equivalently it is a
permutation matrix with no two ordered pairs of 1-cells sharing a displacement.

Encoding (exact, per Theorem R8-style "distinct displacement" CSP):
  - x[i][j] in {0,1}, i,j in 0..n-1  (cell (i,j) is plotted)
  - row/col exact-1:  sum_j x[i][j] = 1,  sum_i x[i][j] = 1
  - for each displacement (dx,dy) with >=2 ordered cell-pairs, the number of
    active pairs is <= 1   (p = x[a][b] AND x[c][d] auxiliary booleans)

This is the direct template for attacking the open orders 32 and 33.

Run:
  python cpsat_costas.py --validate          # find >=1 solution for n=1..11
  python cpsat_costas.py --n 32 --timelimit 3600
  python cpsat_costas.py --n 33 --timelimit 3600
"""
import argparse
import time

try:
    from ortools.sat.python import cp_model
    HAVE_ORTOOLS = True
except Exception:
    HAVE_ORTOOLS = False


def build_model(n):
    """Return (model, x, solver, status_name_fn) for order-n Costas."""
    model = cp_model.CpModel()
    x = [[model.NewBoolVar(f"x{i}_{j}") for j in range(n)] for i in range(n)]
    for i in range(n):
        model.Add(sum(x[i][j] for j in range(n)) == 1)
    for j in range(n):
        model.Add(sum(x[i][j] for i in range(n)) == 1)

    # displacement -> list of ordered cell-pairs ((a,b),(c,d)) with (c-a,d-b)=(dx,dy)
    from collections import defaultdict
    disp = defaultdict(list)
    for a in range(n):
        for b in range(n):
            for c in range(n):
                for d in range(n):
                    if (a, b) == (c, d):
                        continue
                    dx = c - a
                    dy = d - b
                    disp[(dx, dy)].append(((a, b), (c, d)))

    # only displacement classes with >=2 pairs can violate distinctness
    for (dx, dy), pairs in disp.items():
        if len(pairs) < 2:
            continue
        terms = []
        for (a, b), (c, d) in pairs:
            p = model.NewBoolVar(f"p_{dx}_{dy}_{a}_{b}_{c}_{d}")
            model.Add(p <= x[a][b])
            model.Add(p <= x[c][d])
            model.Add(p >= x[a][b] + x[c][d] - 1)
            terms.append(p)
        model.Add(sum(terms) <= 1)
    return model, x


def solve(n, timelimit, workers=4, mem_mb=4000):
    if not HAVE_ORTOOLS:
        return None, []
    model, x = build_model(n)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timelimit
    solver.parameters.num_search_workers = workers
    solver.parameters.max_memory_in_mb = mem_mb
    st = solver.Solve(model)
    status = solver.StatusName(st)
    sol = []
    if status in ("FEASIBLE", "OPTIMAL"):
        pi = [-1] * n
        for i in range(n):
            for j in range(n):
                if solver.Value(x[i][j]) == 1:
                    pi[i] = j
        sol = pi
    return status, sol


def is_costas(pi):
    n = len(pi)
    diffs = set()
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = (pi[j] - pi[i], j - i)
            if d in diffs:
                return False
            diffs.add(d)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--timelimit", type=float, default=3600.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--mem-mb", type=int, default=4000)
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    if not HAVE_ORTOOLS:
        print("OR-Tools not available")
        return

    if args.validate:
        print("== Costas CP-SAT validation (find >=1 solution per n) ==")
        for n in range(1, 12):
            t0 = time.time()
            status, pi = solve(n, 30.0, workers=4)
            ok = (pi != []) and is_costas(pi)
            print(f"  n={n}: status={status} costas_ok={ok} "
                  f"pi={pi if n <= 8 else pi[:8]}... [{time.time()-t0:.1f}s]")
        return

    if args.n <= 0:
        print("specify --n or --validate")
        return
    t0 = time.time()
    status, pi = solve(args.n, args.timelimit, args.workers, args.mem_mb)
    print(f"[Costas n={args.n}] status={status} time={time.time()-t0:.1f}s")
    if pi:
        print(f"  pi={pi}")
        print(f"  is_costas={is_costas(pi)}")


if __name__ == "__main__":
    main()
