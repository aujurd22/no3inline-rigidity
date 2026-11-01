# 运行解释器: C:/Users/djr82/AppData/Local/Programs/Python/Python313/python.exe（ortools 在此环境）
# -*- coding: utf-8 -*-
"""T42m: deletion-based MUS extraction for the m=5 five-family system.
Reveal the minimal infeasible core -> human-readable combinatorial argument."""
import sys
from math import gcd
from ortools.sat.python import cp_model
from collections import Counter

def build_groups(m, fams):
    """Return (base_model_builder, groups) where each group is a list of (name, constraint-factory).
    We rebuild the model each time (cheap at m=5)."""
    groups = []  # (kind, key, cell-list or spec)
    # rows/cols fixed
    for y in range(m):
        groups.append(("row", y, [(x, y) for x in range(m)]))
    for x in range(m):
        groups.append(("col", x, [(x, y) for y in range(m)]))
    nb = 2*m - 1
    # no3 lines
    lines = {}
    dirs = [(dx, dy) for dx in range(-m+1, m) for dy in range(-m+1, m)
            if (dx or dy) and gcd(abs(dx), abs(dy)) == 1 and (dx > 0 or (dx == 0 and dy > 0))]
    for (dx, dy) in dirs:
        for x in range(m):
            for y in range(m):
                lines.setdefault((dx, dy, dx*y - dy*x), []).append((x, y))
    for key, cells in lines.items():
        if len(cells) >= 3:
            groups.append(("line", key, cells))
    # cent groups
    cent = {}
    for x in range(m):
        for y in range(m):
            u, w = 2*x - nb, 4*y - nb
            g = gcd(abs(u), abs(w))
            cent.setdefault((u//g, w//g), []).append((x, y))
    for key, cells in cent.items():
        if len(cells) >= 2:
            groups.append(("cent", key, cells))
    # family pairs: encode per (family, pair) with selector z/w — group = both selectors of a pair
    val = {}
    for (al, be) in fams:
        vv = {}
        for x in range(m):
            for y in range(m):
                c = al*x - 2*be*y
                vv.setdefault(c, []).append((x, y))
        seen = set()
        for c in list(vv):
            cs = -c + (al - be)*nb
            if cs == c:
                groups.append(("famself", (al, be, c), vv[c]))
                continue
            pair = (min(c, cs), max(c, cs))
            if pair in seen or cs not in vv: continue
            seen.add(pair)
            groups.append(("fam", (al, be) + pair, (vv[c], vv[cs])))
    return groups

def solve_with(m, groups, drop):
    model = cp_model.CpModel()
    v = {}
    for x in range(m):
        for y in range(m):
            v[(x, y)] = model.NewBoolVar(f"v{x}_{y}")
    for (kind, key, payload) in groups:
        gid = (kind, key)
        if gid in drop: continue
        if kind == "row":
            model.Add(sum(v[c] for c in payload) == 2)
        elif kind == "col":
            model.Add(sum(v[c] for c in payload) == 2)
        elif kind == "line":
            model.Add(sum(v[c] for c in payload) <= 2)
        elif kind == "cent":
            model.Add(sum(v[c] for c in payload) <= 1)
        elif kind == "famself":
            model.Add(sum(v[c] for c in payload) <= 1)
        elif kind == "fam":
            (al, be, c, cs) = key
            cellsC, cellsCS = payload
            mc = model.NewIntVar(0, 2, f"mc")
            mcs = model.NewIntVar(0, 2, f"mcs")
            model.Add(mc == sum(v[c_] for c_ in cellsC))
            model.Add(mcs == sum(v[c_] for c_ in cellsCS))
            z = model.NewBoolVar("z")
            model.Add(mc <= 1 + z)
            model.Add(mcs <= 2 - 2*z)
            w = model.NewBoolVar("w")
            model.Add(mcs <= 1 + w)
            model.Add(mc <= 2 - 2*w)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_workers = 1
    return solver.StatusName(solver.Solve(model))

if __name__ == "__main__":
    m = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    FAMS5 = [(1,1), (1,-1), (1,2), (1,-2), (1,-3)]
    groups = build_groups(m, FAMS5)
    print(f"m={m}: {len(groups)} constraint groups")
    st = solve_with(m, groups, set())
    print("full system:", st)
    if st != "INFEASIBLE":
        print("not infeasible — abort"); sys.exit(0)
    # deletion filter
    drop = set()
    changed = True
    round_ = 0
    while changed:
        changed = False; round_ += 1
        for i, g in enumerate(groups):
            gid = (g[0], g[1])
            if gid in drop: continue
            drop.add(gid)
            st = solve_with(m, groups, drop)
            if st == "INFEASIBLE":
                changed = True
                print(f"  round {round_}: dropped {g[0]}:{g[1]} (still INFEASIBLE, |drop|={len(drop)})", flush=True)
            else:
                drop.discard(gid)
    print(f"MUS-ish core: {len(groups) - len(drop)} of {len(groups)} groups kept")
    kept = [g for g in groups if (g[0], g[1]) not in drop]
    from collections import Counter as C2
    print("kept by kind:", dict(C2(g[0] for g in kept)))
    for g in kept:
        print("  KEEP", g[0], g[1])
