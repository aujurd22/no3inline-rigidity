# -*- coding: utf-8 -*-
"""T43a: Linear-potential separation search for the 5-family system (Open Problem 5.1).

Layer 1: LP relaxation of the FULL system (m=5..8).  If INFEASIBLE -> Farkas dual
         directly yields a linear potential (the dream).
Layer 2: LP relaxation of the m=5 MUS core (29 groups).  Core-level Farkas test.
Layer 3: per-column D/C split enumeration (column x: both points y>=h  vs  <=1 point
         y>=h), LP per pattern -> count feasible patterns, locate where integrality bites.

Phase-1 convention: soft slacks on line/cent/famself/fam constraints; rows/cols hard.
If phase-1 optimum > 0 -> system LP-infeasible; GLOP duals at optimum give the
multiplier vector = candidate potential.

Run: C:/Users/djr82/AppData/Local/Programs/Python/Python313/python.exe t43a_lp_potential.py <m> <layer>
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t42m_mus5 import build_groups
from ortools.linear_solver import pywraplp

FAMS5 = [(1, 1), (1, -1), (1, 2), (1, -2), (1, -3)]


def group_cells(g):
    kind, key, payload = g
    if kind == "fam":
        (al, be, c, cs) = key
        cellsC, cellsCS = payload
        return [("fam", (list(cellsC), list(cellsCS)), None, (al, be, c, cs))]
    if kind in ("row", "col", "line", "cent", "famself"):
        return [("le", list(payload), 2 if kind in ("row", "col", "line") else 1, kind)]
    raise ValueError(kind)


def build_lp(m, groups, soft=True):
    """Rows/cols hard ==2; others either hard (soft=False) or slack-minimized."""
    solver = pywraplp.Solver.CreateSolver("GLOP")
    v = {}
    for x in range(m):
        for y in range(m):
            v[(x, y)] = solver.NumVar(0, 1, f"v{x}_{y}")
    specs = []
    for g in groups:
        specs.extend(group_cells(g))
    slacks = []
    for idx, (kind, cells, rhs, tag) in enumerate(specs):
        if kind == "le":
            expr = solver.Sum([v[c] for c in cells])
            if soft:
                s = solver.NumVar(0, solver.infinity(), f"s{idx}")
                slacks.append(s)
                solver.Add(expr - s <= rhs)
            else:
                solver.Add(expr <= rhs)
        elif kind == "fam":
            cellsC, cellsCS = cells
            mc = solver.Sum([v[c] for c in cellsC])
            mcs = solver.Sum([v[c] for c in cellsCS])
            # EXACT integer semantics given no3 (mc,mcs <= 2 implied by collinearity):
            #   forbidden = {mc+mcs >= 3}; hull = single linear ineq mc+mcs <= 2
            if soft:
                s1 = solver.NumVar(0, solver.infinity(), f"s{idx}a")
                slacks.append(s1)
                solver.Add(mc + mcs - s1 <= 2)
            else:
                solver.Add(mc + mcs <= 2)
    for (kind, cells, rhs, tag) in specs:
        if tag in ("row", "col"):
            solver.Add(solver.Sum([v[c] for c in cells]) == 2)
    if soft:
        solver.Minimize(solver.Sum(slacks))
    return solver, v, slacks, specs


def solve_lp(solver, time_s=120):
    solver.SetTimeLimit(int(time_s * 1000))
    st = solver.Solve()
    name = str(solver.Solve()) if False else None
    # pywraplp status names
    stmap = {0: "OPTIMAL", 1: "FEASIBLE", 2: "INFEASIBLE", 3: "UNBOUNDED", 4: "ABNORMAL", 5: "NOT_SOLVED"}
    name = stmap.get(int(st) if st is not None else -1, "?")
    obj = solver.Objective().Value() if name in ("OPTIMAL", "FEASIBLE") else None
    return name, obj


def layer1(m, time_s=120):
    groups = build_groups(m, FAMS5)
    print(f"=== Layer1 full system LP  m={m}  ({len(groups)} groups) ===", flush=True)
    solver, v, slacks, specs = build_lp(m, groups, soft=True)
    name, obj = solve_lp(solver, time_s)
    print(f"phase1: {name}  min-total-slack={obj}")
    if obj is not None and obj > 1e-9:
        s2, v2, _, sp2 = build_lp(m, groups, soft=False)
        name2, _ = solve_lp(s2, time_s)
        print(f"hard LP: {name2}")
        if name2 == "INFEASIBLE":
            print(">>> LP INFEASIBLE -> linear Farkas potential EXISTS")
            print("duals (constraint name -> dual), nonzero only:")
            for con in solver.constraints():
                d = con.dual_value()
                if abs(d) > 1e-9:
                    print(f"   {con.name()}: {d:.6f}")
        return
    if obj is None:
        print("LP solver failed/timeout")
        return
    # LP feasible -> fractional witness stats
    vals = {(x, y): v[(x, y)].solution_value() for x in range(m) for y in range(m)}
    import statistics
    flat = list(vals.values())
    print(f"LP FEASIBLE - fractional witness: mean={statistics.mean(flat):.4f} min={min(flat):.4f} max={max(flat):.4f}")
    hot_cells = sorted(vals.items(), key=lambda kv: -kv[1])[:8]
    print("  top cells:", [(c, round(q, 3)) for c, q in hot_cells])
    # which soft constraints carry slack > 0
    used = []
    for idx, (kind, cells, rhs, tag) in enumerate(specs):
        if tag in ("row", "col"):
            continue
        s = solver.Var(f"s{idx}") if False else None
    # simpler: re-read slack values by name
    for idx, (kind, cells, rhs, tag) in enumerate(specs):
        if tag in ("row", "col"):
            continue
        sv = solver.LookupConstraint or None
    # GLOP python API: iterate variables for slack values
    slack_total = 0.0
    slack_kinds = {}
    for var in solver.variables():
        nm = var.name()
        if nm.startswith("s") and var.solution_value() and var.solution_value() > 1e-9:
            base = nm.split("a")[0].split("b")[0]
            k = specs[int(base[1:])][3]
            slack_kinds[k] = slack_kinds.get(k, 0.0) + var.solution_value()
            slack_total += var.solution_value()
    print(f"  slack by kind: { {k: round(val,3) for k,val in slack_kinds.items()} } total={slack_total:.3f}")


def layer2_core(m=5, time_s=300):
    import re, ast
    tdir = os.path.dirname(os.path.abspath(__file__))
    logf = os.path.join(tdir, f"mus_m{m}.log")
    if not os.path.exists(logf):
        print(f"(no {logf}; skip core layer)")
        return
    kept = []
    for line in open(logf, encoding="utf-8", errors="replace"):
        mm = re.match(r"\s*KEEP (\w+) (.+)$", line.rstrip())
        if mm:
            kind = mm.group(1)
            try:
                key = ast.literal_eval(mm.group(2).strip())
            except Exception:
                continue
            kept.append((kind, key))
    groups_all = build_groups(m, FAMS5)
    keyset = set(kept)
    core = [g for g in groups_all if (g[0], g[1]) in keyset]
    print(f"=== Layer2 core LP  m={m}  core groups={len(core)} (parsed {len(kept)}) ===")
    solver, v, slacks, specs = build_lp(m, core, soft=True)
    name, obj = solve_lp(solver, time_s)
    print(f"phase1: {name}  min-total-slack={obj}")
    if obj is not None and obj > 1e-9:
        s2, v2, _, sp2 = build_lp(m, core, soft=False)
        name2, _ = solve_lp(s2, time_s)
        print(f"hard LP: {name2}")
        if name2 == "INFEASIBLE":
            print(">>> CORE LP INFEASIBLE -> Farkas potential on the 29-group core EXISTS")
            print("phase-1 duals (nonzero):")
            for con in solver.constraints():
                d = con.dual_value()
                if abs(d) > 1e-9:
                    print(f"   {con.name()}: {d:.6f}")
    elif obj is not None:
        print(">>> CORE LP FEASIBLE: no linear Farkas even on the MUS core.")
        print("    Linear potential dead at core level -> integrality essential.")
        vals = {(x, y): v[(x, y)].solution_value() for x in range(m) for y in range(m)}
        import statistics
        flat = list(vals.values())
        print(f"    witness mean={statistics.mean(flat):.4f}")


if __name__ == "__main__":
    m = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    layer = sys.argv[2] if len(sys.argv) > 2 else "1"
    if layer == "1":
        layer1(m)
    elif layer == "2":
        layer2_core(m)
