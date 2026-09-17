"""
solver_full_model.py — Complete CP-SAT model for rot4-NTIL(m),
ALLOWING 2-cycles (mutual transposed pairs).

THE KEY CORRECTION:
In the compact model (solver_cpsat_m37.py), edges are unordered (u,v) with u≤v,
and each edge gets at most ONE orientation.  This makes 2-cycles (i,j)+(j,i)
STRUCTURALLY IMPOSSIBLE.  The "no 2-cycles" restriction is NOT forced by any
theorem — it is an artificial subspace that both the SA and the compact CP-SAT
search, and 72 may be the basin of THAT subspace, not the full problem.

This model:
- Variable z_ij ∈ {0,1} for EVERY directed pair (i,j), i,j∈{0..m-1}
  (including loops i=j).  This is m² = 1369 variables for m=37.
- Degree constraint: 2·z_ii + Σ_{j≠i}(z_ij + z_ji) = 2   (each vertex deg 2)
- Total cells: Σ_i Σ_j z_ij = m   (37 cells, each contributing 2 deg, total 74)
- OPTIONAL: max_2cycles = k  constrains how many mutual pairs can co-exist.
  A 2-cycle at {i,j} means z_ij = z_ji = 1.
- Per-line (X): sum of present lifts on each geometric line ≤ 2.
  Same slot encoding as the compact model, but present = z_ij directly
  (no separate edge/orient selection).
- Objective: minimize #overloaded lines (or total_bad).

Validation plan:
  1. m=5..12, k=0  → must find same OPTIMAL obj=0 solutions as compact model.
  2. m=5..12, k=1  → test if allowing 1 2-cycle still yields solutions.
  3. m=37, k=0     → should reproduce FEASIBLE obj=72 (cross-check).
  4. m=37, k=1..4  → the ATTACK: does allowing 2-cycles lower the floor below 72?
"""
import os, sys, time, json, pickle, argparse
from collections import defaultdict
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))

def igcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a

def line_of(p, q):
    dx = q[0] - p[0]; dy = q[1] - p[1]
    A, B = dy, -dx
    g = igcd(abs(A), abs(B)) or 1
    A //= g; B //= g
    if A < 0 or (A == 0 and B < 0):
        A, B = -A, -B
    return (A, B, A * p[0] + B * p[1])

# ---------------------------------------------------------------------------
# C4 lift of a directed cell (i,j)
# ---------------------------------------------------------------------------
def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def cell_lifts(i, j, n):
    """Return list of 4 lift points for directed cell (i,j)."""
    return [c4(i, j, r, n) for r in range(4)]

# ---------------------------------------------------------------------------
# Precompute slots and line sets (cached per m)
# ---------------------------------------------------------------------------
def build_slots(m):
    """Return (cell_index_map, slots).
    cell_index_map[i][j] = idx (0..m²-1)
    slots[idx] = list of 4 slot triples (idx, r, px, py)
    """
    n = 2 * m
    idx = {}
    slots = []  # flat list of (cell_idx, r, px, py)
    cell_idx = 0
    for i in range(m):
        for j in range(m):
            idx[(i, j)] = cell_idx
            for r in range(4):
                px, py = c4(i, j, r, n)
                slots.append((cell_idx, r, px, py))
            cell_idx += 1
    return idx, slots

def build_linesets(m, slots, cache_dir=HERE):
    """Same geometry as compact model: group slots by geometric line signature,
    keep only lines with >=3 slots."""
    cache = os.path.join(cache_dir, f"full_linesets_m{m}.pkl")
    if os.path.exists(cache):
        with open(cache, "rb") as f:
            return pickle.load(f)
    lines = defaultdict(set)
    ns = len(slots)  # 4*m²
    for a in range(ns):
        pa = (slots[a][2], slots[a][3])  # px, py
        for b in range(a + 1, ns):
            pb = (slots[b][2], slots[b][3])
            if pa == pb:
                continue
            k = line_of(pa, pb)
            lines[k].add(a)
            lines[k].add(b)
    out = {k: sorted(v) for k, v in lines.items() if len(v) >= 3}
    with open(cache, "wb") as f:
        pickle.dump(out, f)
    return out

def count_2cycles(zvals, m):
    """Count mutual pairs (i,j) with both directions selected."""
    k = 0
    for i in range(m):
        for j in range(i + 1, m):
            if zvals[i * m + j] and zvals[j * m + i]:
                k += 1
    return k

# ---------------------------------------------------------------------------
# Full CP-SAT model
# ---------------------------------------------------------------------------
def solve(m, time_limit=600, max_2cycles=None, verbose=False):
    from ortools.sat.python import cp_model

    t0 = time.time()
    cell_idx, slots = build_slots(m)
    n_slots = len(slots)  # 4*m²
    linesets = build_linesets(m, slots)
    if verbose:
        print(f"  m={m}: cells={m*m} slots={n_slots} "
              f"lines(>=3)={len(linesets)} precompute={time.time()-t0:.1f}s",
              flush=True)

    model = cp_model.CpModel()

    # z[i*m + j] = 1 iff directed cell (i,j) selected
    z = [model.NewBoolVar(f"z_{i}_{j}") for i in range(m) for j in range(m)]

    # Degree constraint: 2*z_ii + Σ_{j≠i}(z_ij + z_ji) = 2
    for i in range(m):
        terms = [2 * z[i * m + i]]  # loop contributes 2
        for j in range(m):
            if i != j:
                terms.append(z[i * m + j])   # (i,j) contributes 1 to deg(i)
                terms.append(z[j * m + i])   # (j,i) also contributes 1 to deg(i)
        model.Add(sum(terms) == 2)

    # Total cells = m (each contributes 2 degrees, total degree = 2m)
    model.Add(sum(z) == m)

    # Optional: limit 2-cycles
    if max_2cycles is not None:
        # A 2-cycle at {i,j} occurs if z_ij AND z_ji are both 1
        # Sum_{i<j} (z_ij AND z_ji) <= max_2cycles
        # Encode each mutual pair as a BoolVar
        pair_vars = []
        for i in range(m):
            for j in range(i + 1, m):
                pv = model.NewBoolVar(f"p2c_{i}_{j}")
                # pv = 1 iff z_ij AND z_ji
                model.AddBoolAnd([z[i * m + j], z[j * m + i]]).OnlyEnforceIf(pv)
                model.AddBoolOr([z[i * m + j].Not(), z[j * m + i].Not()]).OnlyEnforceIf(pv.Not())
                pair_vars.append(pv)
        model.Add(sum(pair_vars) <= max_2cycles)

    # Slot present literal = z[cell_idx] (since cell (i,j) directly)
    # We need a BoolVar per slot
    present = [None] * n_slots
    for s_idx, (ci, r, px, py) in enumerate(slots):
        present[s_idx] = z[ci]

    # (X): per line, sum present <= 2; minimize overloaded lines
    overloaded = []
    for k, S in linesets.items():
        terms = [present[si] for si in S]
        svar = model.NewIntVar(0, len(S), f"s_{k}")
        model.Add(svar == sum(terms))
        over = model.NewBoolVar(f"over_{k}")
        model.Add(svar >= 3).OnlyEnforceIf(over)
        model.Add(svar <= 2).OnlyEnforceIf(over.Not())
        overloaded.append(over)

    model.Minimize(sum(overloaded))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = False
    st = solver.Solve(model)
    status = solver.StatusName(st)
    res = {"m": m, "max_2cycles": max_2cycles, "status": status,
           "objective": None, "time": solver.WallTime(), "found": False}

    if status in ("OPTIMAL", "FEASIBLE"):
        obj = int(solver.ObjectiveValue())
        res["objective"] = obj
        if obj == 0:
            # decode cells
            cells = []
            for i in range(m):
                for j in range(m):
                    if solver.Value(z[i * m + j]):
                        cells.append((i, j))
            res["found"] = True
            res["cells"] = cells
            res["n_2cycles"] = count_2cycles(
                [solver.Value(z[idx]) for idx in range(m * m)], m)

    return res

# ---------------------------------------------------------------------------
# Independent verification using the existing Board
# ---------------------------------------------------------------------------
def verify_with_board(m, cells):
    """Use solver_theory_m37.Board to verify (X) = 0 independently."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "st", os.path.join(HERE, "solver_theory_m37.py"))
    st = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(st)

    # Build edges list: for each cell (i,j), edge = (min(i,j), max(i,j))
    # Duplicate edges are allowed (2-cycles produce duplicate unordered pairs)
    edges = []
    for (i, j) in cells:
        if i == j:
            edges.append((i, i))
        else:
            edges.append((min(i, j), max(i, j)))

    board = st.Board(m)
    board.build(edges, cells)
    vt = board.verify_total()
    return vt, board.lifts, board.total_bad

# ---------------------------------------------------------------------------
# Validation: k=0 should match compact CP-SAT on small m
# ---------------------------------------------------------------------------
def validate(lo=5, hi=12, per=60):
    """Run full model with k=0 on small m; verify results with Board."""
    allok = True
    for m in range(lo, hi + 1):
        r = solve(m, time_limit=per, max_2cycles=0, verbose=True)
        ok = False
        if r["found"]:
            vt, lifts, tb = verify_with_board(m, r["cells"])
            ok = (vt == 0)
            if not ok:
                print(f"  m={m}: solved but Board.verify_total={vt} "
                      f"(encoding mismatch!)", flush=True)
        print(f"  m={m}: status={r['status']} obj={r['objective']} "
              f"verify={ok} k0=0={'yes' if r.get('n_2cycles',0)==0 else 'NO!'}",
              flush=True)
        allok = allok and ok
    print("VALIDATION", "PASS" if allok else "FAIL")
    return allok

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--time", type=float, default=600)
    ap.add_argument("--max-2cycles", type=int, default=None,
                    help="max number of mutual transposed pairs (2-cycles). "
                         "None = unconstrained, 0 = forbid all (compact model)")
    ap.add_argument("--out", default="results/full_model_m37.json")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--sweep", type=int, default=None,
                    help="sweep k=0..N, run each with --time and report")
    args = ap.parse_args()

    if args.validate:
        validate()
    elif args.sweep is not None:
        # Sweep max_2cycles from 0 to args.sweep
        results = []
        for k in range(args.sweep + 1):
            print(f"\n=== max_2cycles={k} ===", flush=True)
            r = solve(args.m, time_limit=args.time, max_2cycles=k, verbose=True)
            results.append(r)
            print(f"  RESULT k={k}: status={r['status']} obj={r['objective']} "
                  f"found={r['found']} time={r['time']:.1f}s", flush=True)
        # Save sweep results
        sweep_out = args.out.replace(".json", f"_sweep0to{args.sweep}.json")
        with open(sweep_out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSweep saved -> {sweep_out}")
    else:
        r = solve(args.m, time_limit=args.time,
                  max_2cycles=args.max_2cycles, verbose=True)
        print(f"RESULT m={args.m}: max_2cycles={args.max_2cycles} "
              f"status={r['status']} objective={r['objective']} "
              f"found={r['found']} time={r['time']:.1f}s", flush=True)
        if r["found"]:
            out = {"m": args.m, "max_2cycles": args.max_2cycles,
                   "found": True, "cells": r["cells"],
                   "n_2cycles": r["n_2cycles"]}
            with open(args.out, "w") as f:
                json.dump(out, f)
            print(f"  saved -> {args.out}")
        else:
            # Save partial results too
            out = {"m": args.m, "max_2cycles": args.max_2cycles,
                   "found": False, "objective": r["objective"]}
            with open(args.out, "w") as f:
                json.dump(out, f)
