# 运行解释器: C:/Users/djr82/AppData/Local/Programs/Python/Python313/python.exe（ortools 在此环境）
# -*- coding: utf-8 -*-
"""T42k: CP-SAT search on the 5-family avoidance system (T41-A reduction test).

Variables: v[x][v] on coarse board [0,m)^2.
Constraints:
  - 2 per row, 2 per column
  - no 3 collinear (all primitive directions, lines with >= 3 cells)
  - 5-family avoidance: for family (al,be), value c: forbid (mult(c)==2 AND mult(c*)>=1),
    c* = -c + (al-be)*(2m-1); encoded with one binary per canonical value pair.
Run: python t42k_sat5fam.py <m> <time_limit_s>
"""
import sys, time
from ortools.sat.python import cp_model

def build(m, fams, no3=True, time_s=60):
    model = cp_model.CpModel()
    v = {}
    for x in range(m):
        for y in range(m):
            v[(x, y)] = model.NewBoolVar(f"v_{x}_{y}")
    # rows/cols
    for y in range(m):
        model.Add(sum(v[(x, y)] for x in range(m)) == 2)
    for x in range(m):
        model.Add(sum(v[(x, y)] for y in range(m)) == 2)
    # no-3-collinear: for every line (any primitive direction) sum <= 2
    if no3:
        # enumerate all lines through all pairs of cells via normal forms (dx,dy)->c = dx*y - dy*x? use canonical line hashing
        from math import gcd
        lines = {}
        dirs = [(dx, dy) for dx in range(-m+1, m) for dy in range(-m+1, m)
                if (dx or dy) and gcd(abs(dx), abs(dy)) == 1 and (dx > 0 or (dx == 0 and dy > 0))]
        for (dx, dy) in dirs:
            # line key: value c = dx*y - dy*x, but normalize sign already canonical by dir
            for x in range(m):
                for y in range(m):
                    c = dx*y - dy*x
                    lines.setdefault((dx, dy, c), []).append((x, y))
        for key, cells in lines.items():
            if len(cells) >= 3:
                model.Add(sum(v[c_] for c_ in cells) <= 2)
    nb = 2*m - 1
    # cent avoidance: at most one cell per origin-line group of doubled coords
    # P = (2x-nb, 4y-nb); cells with parallel P pairwise forbidden
    from math import gcd as _g
    groups = {}
    for x in range(m):
        for y in range(m):
            u, w = 2*x - nb, 4*y - nb
            g = _g(abs(u), abs(w))
            key = (u//g, w//g)
            groups.setdefault(key, []).append(v[(x, y)])
    for key, cells in groups.items():
        if len(cells) >= 2:
            model.Add(sum(cells) <= 1)
    npairs = 0
    for (al, be) in fams:
        vals = {}
        for x in range(m):
            for y in range(m):
                c = al*x - 2*be*y
                vals.setdefault(c, []).append(v[(x, y)])
        msum = {c: model.NewIntVar(0, 2, f"m_{al}_{be}_{c}") for c in vals}
        for c, cells in vals.items():
            model.Add(msum[c] == sum(cells))
        seen = set()
        for c in list(vals):
            cs = -c + (al - be)*nb
            if cs == c:  # self-mirror: forbid double outright
                model.Add(msum[c] <= 1)
                continue
            pair = (min(c, cs), max(c, cs))
            if pair in seen: continue
            seen.add(pair)
            if cs not in msum:  # mirror value impossible: no constraint
                continue
            z = model.NewBoolVar(f"z_{al}_{be}_{pair[0]}")
            model.Add(msum[c] <= 1 + z)
            model.Add(msum[cs] <= 2 - 2*z)
            # symmetric side: forbid (2 at cs, >=1 at c)
            w = model.NewBoolVar(f"w_{al}_{be}_{pair[0]}")
            model.Add(msum[cs] <= 1 + w)
            model.Add(msum[c] <= 2 - 2*w)
            npairs += 2
    return model, v

def solve(m, fams, time_s, no3=True):
    t0 = time.time()
    model, v = build(m, fams, no3=no3, time_s=time_s)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_s
    solver.parameters.num_workers = 1
    st = solver.Solve(model)
    el = time.time() - t0
    name = solver.StatusName(st)
    sol = None
    if name == "OPTIMAL" or name == "FEASIBLE":
        sol = [(x, y) for (x, y), var in v.items() if solver.Value(var)]
    return name, sol, el, solver.ResponseProto().num_conflicts if hasattr(solver, 'ResponseProto') else -1

FAMS5 = [(1,1), (1,-1), (1,2), (1,-2), (1,-3)]
FAMS3 = [(1,1), (1,-1), (1,-2)]

if __name__ == "__main__":
    m = int(sys.argv[1]); t = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    which = sys.argv[3] if len(sys.argv) > 3 else "5"
    no3 = (len(sys.argv) <= 4) or (sys.argv[4] != "0")
    fams = FAMS5 if which == "5" else FAMS3
    # positive control at small m: system WITH no3 should be INFEASIBLE for m=5..7 (5 fams) per tower
    name, sol, el, _ = solve(m, fams, t, no3=no3)
    print(f"m={m} fams={which} no3={int(no3)}: {name} ({el:.0f}s)", flush=True)
    if sol:
        print("S =", sol)
        # verify on the fly: family kills must be absent; then check full mixed triples
        from t42a_avoidance import mixed_triples
        from collections import Counter
        tc = Counter(tt for *_, tt in mixed_triples(m, sol))
        print("full mixed-triple profile:", dict(tc))
