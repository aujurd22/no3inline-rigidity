# 运行解释器: C:/Users/djr82/AppData/Local/Programs/Python/Python313/python.exe（ortools 在此环境）
# -*- coding: utf-8 -*-
"""T42l: CP-SAT saturation search for T'-F2 — rot2 NTIL solution with NO
F2-unimodular mixed triangle (2 reps + antipode, |det|=1 in original coords).

Model on full n x n board (n even):
  - 2 per row, 2 per column
  - no 3 collinear (all primitive directions)
  - rot2 symmetry: v[x][y] == v[n-1-x][n-1-y]
  - F2-avoidance: for every triple of left-half cells (p,q,r) with
    |det(q-p, antipode(r)-p)| == 1: p+q+r <= 2  (not all chosen)
Positive control: n=6,8 -> INFEASIBLE expected (all solutions have F2 triangles).
Run: python t42l_sat_f2free.py <n> <time_limit_s>
"""
import sys, time
from math import gcd
from itertools import combinations
from ortools.sat.python import cp_model

def build(n):
    model = cp_model.CpModel()
    v = {}
    for x in range(n):
        for y in range(n):
            v[(x, y)] = model.NewBoolVar(f"v{x}_{y}")
    for y in range(n):
        model.Add(sum(v[(x, y)] for x in range(n)) == 2)
    for x in range(n):
        model.Add(sum(v[(x, y)] for y in range(n)) == 2)
    # rot2 symmetry
    for x in range(n):
        for y in range(n):
            model.Add(v[(x, y)] == v[(n-1-x, n-1-y)])
    # no-3-collinear (all primitive directions)
    lines = {}
    dirs = [(dx, dy) for dx in range(-n+1, n) for dy in range(-n+1, n)
            if (dx or dy) and gcd(abs(dx), abs(dy)) == 1 and (dx > 0 or (dx == 0 and dy > 0))]
    for (dx, dy) in dirs:
        for x in range(n):
            for y in range(n):
                lines.setdefault((dx, dy, dx*y - dy*x), []).append((x, y))
    for key, cells in lines.items():
        if len(cells) >= 3:
            model.Add(sum(v[c] for c in cells) <= 2)
    # F2-avoidance over left-half cells (reps live here by rot2 pairing)
    half = n // 2
    L = [(x, y) for x in range(half) for y in range(n)]
    bad = 0
    for p, q, r in combinations(L, 3):
        for a, b, cc in ((p, q, r), (p, r, q), (q, r, p)):
            dx, dy = b[0]-a[0], b[1]-a[1]
            ex, ey = (n-1-cc[0])-a[0], (n-1-cc[1])-a[1]
            if abs(dx*ey - dy*ex) == 1:
                model.Add(v[p] + v[q] + v[r] <= 2)
                bad += 1
                break
    return model, v, bad

if __name__ == "__main__":
    n = int(sys.argv[1]); t = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    t0 = time.time()
    model, v, bad = build(n)
    print(f"n={n}: built in {time.time()-t0:.0f}s, F2-forbidden triples = {bad}", flush=True)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = t
    solver.parameters.num_workers = 1
    st = solver.StatusName(solver.Solve(model))
    print(f"n={n}: {st} ({time.time()-t0:.0f}s)")
    if st in ("OPTIMAL", "FEASIBLE"):
        pts = [(x, y) for (x, y), var in v.items() if solver.Value(var)]
        print("S =", pts)
        # independent check: min |det| over mixed triples of chosen points
        reps = sorted(p for p in pts if p[0] < n/2)
        best = 10**9
        from itertools import combinations as C2
        for p, q, r in C2(reps, 3):
            for a, b, cc in ((p,q,r),(p,r,q),(q,r,p)):
                d = abs((b[0]-a[0])*((n-1-cc[1])-a[1]) - (b[1]-a[1])*((n-1-cc[0])-a[0]))
                best = min(best, d)
        print(f"independent min |F2 det| over chosen = {best}")
