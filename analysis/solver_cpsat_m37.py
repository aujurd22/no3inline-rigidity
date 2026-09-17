"""
solver_cpsat_m37.py -- Compact CP-SAT (OR-Tools) solver for rot4-NTIL (m=37).

This is the "our structural pruning + their dynamic pruning" combination:
  * OUR pruning (static, theorem-driven, from SIRH / Th-44):
      - A rot4-NTIL is a 2-factor (simple 2-regular graph on {0..m-1})
        + orientation per edge + (X) no 3 of the 4m C4-lifts collinear.
      - Edges are encoded as UNORDERED (u,v) with u<=v, which makes the
        666 transposed pairs (= 2-cycles) STRUCTURALLY IMPOSSIBLE -> forbidden
        for free.  Row/col exactly-2 is automatic from the 2-factor.
      - Variables: one BoolVar x[e] per candidate edge, one BoolVar orient[e]
        per non-loop edge.  Model size ~ m(m+1)/2 + m(m-1)/2 << the 4m full
        point model that walled out earlier CP-SAT attempts at m>=17.
  * THEIR pruning (dynamic): OR-Tools CP-SAT conflict-driven clause learning,
    applied to the (X) constraint encoded as per-line cardinality bounds
    (sum of present lifts on each geometric line <= 2) + an objective that
    minimizes the number of overloaded lines.

If the solver returns a config with objective 0 -> a rot4-NTIL at m exists
(constructive proof).  If UNSAT -> proves none exists (under this exact model).
UNKNOWN -> timed out, best-effort residual reported.

Usage:
  python solver_cpsat_m37.py --validate            # recover m=5..12 (proves model)
  python solver_cpsat_m37.py --m 37 --time 600 \
        --out results/cpsat_m37.json \
        --hints results/solver_theory_m37_long.json
"""
import os, sys, time, json, pickle, argparse, random
from collections import defaultdict
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))

def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

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
# slot / line precompute (cached)
# ---------------------------------------------------------------------------
def build_slots(m):
    n = 2 * m
    candidates = [(u, v) for u in range(m) for v in range(u, m)]
    cidx = {e: i for i, e in enumerate(candidates)}
    slots = []  # (cand_idx, oi, r, px, py, is_loop)
    for (u, v) in candidates:
        is_loop = (u == v)
        orients = [(u, v)] if is_loop else [(u, v), (v, u)]
        for oi, (a, b) in enumerate(orients):
            for r in range(4):
                px, py = c4(a, b, r, n)
                slots.append((cidx[(u, v)], oi, r, px, py, is_loop))
    return candidates, slots

def build_linesets(m, slots, cache_dir=HERE):
    cache = os.path.join(cache_dir, f"cpsat_linesets_m{m}.pkl")
    if os.path.exists(cache):
        with open(cache, "rb") as f:
            return pickle.load(f)
    lines = defaultdict(set)
    ns = len(slots)
    for i in range(ns):
        pi = (slots[i][3], slots[i][4])
        for j in range(i + 1, ns):
            pj = (slots[j][3], slots[j][4])
            if pi == pj:
                continue
            k = line_of(pi, pj)
            lines[k].add(i)
            lines[k].add(j)
    out = {k: sorted(v) for k, v in lines.items() if len(v) >= 3}
    with open(cache, "wb") as f:
        pickle.dump(out, f)
    return out

# ---------------------------------------------------------------------------
# CP-SAT model
# ---------------------------------------------------------------------------
def solve(m, time_limit=600, hints=None, verbose=False):
    from ortools.sat.python import cp_model
    t0 = time.time()
    candidates, slots = build_slots(m)
    n = 2 * m
    linesets = build_linesets(m, slots)
    if verbose:
        print(f"  slots={len(slots)} lines(>=3)={len(linesets)} "
              f"precompute={time.time()-t0:.1f}s", flush=True)

    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x_{i}") for i in range(len(candidates))]
    orient = [None] * len(candidates)
    # orientation vars only for non-loop edges
    incident = defaultdict(list)   # v -> list of (eidx, weight)
    for ei, (u, v) in enumerate(candidates):
        if u == v:
            # loop at u contributes degree 2 at u (NOT 4): add a single
            # entry of weight 2.  (Original code appended twice -> weight 4,
            # which wrongly forbade every loop edge and could yield a false
            # UNSAT for any solution that needs a diagonal/loop cell.)
            incident[u].append((ei, 2))
        else:
            incident[u].append((ei, 1))
            incident[v].append((ei, 1))
        if u != v:
            orient[ei] = model.NewBoolVar(f"o_{ei}")

    # 2-factor: each vertex degree exactly 2
    for v in range(m):
        model.Add(sum(w * x[ei] for ei, w in incident[v]) == 2)
    model.Add(sum(x) == m)

    # present literal per slot
    present = [None] * len(slots)
    overloaded = []
    for si, (ei, oi, r, px, py, is_loop) in enumerate(slots):
        if is_loop:
            present[si] = x[ei]
        else:
            pres = model.NewBoolVar(f"p_{si}")
            lit = orient[ei] if oi == 1 else orient[ei].Not()
            model.AddBoolAnd([x[ei], lit]).OnlyEnforceIf(pres)
            model.AddBoolOr([x[ei].Not(), lit.Not()]).OnlyEnforceIf(pres.Not())
            present[si] = pres

    # (X): per line, sum of present <= 2 ; objective minimizes #overloaded lines
    for k, S in linesets.items():
        terms = [present[si] for si in S]
        svar = model.NewIntVar(0, len(S), f"s_{k}")
        model.Add(svar == sum(terms))
        over = model.NewBoolVar(f"over_{k}")
        model.Add(svar >= 3).OnlyEnforceIf(over)
        model.Add(svar <= 2).OnlyEnforceIf(over.Not())
        overloaded.append(over)

    model.Minimize(sum(overloaded))

    # hints from a known config
    if hints:
        edges_h, cells_h = hints
        hint_cell = {}
        for (u, v), (a, b) in zip(edges_h, cells_h):
            key = (u, v) if u <= v else (v, u)
            hint_cell[key] = (a, b)
        for ei, (u, v) in enumerate(candidates):
            model.AddHint(x[ei], 1 if (u, v) in hint_cell else 0)
            if u != v and (u, v) in hint_cell:
                hc = hint_cell[(u, v)]
                model.AddHint(orient[ei], 0 if hc == (u, v) else 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = False
    st = solver.Solve(model)
    status = solver.StatusName(st)
    res = {"m": m, "status": status, "objective": None,
           "time": solver.WallTime(), "found": False}
    if status in ("OPTIMAL", "FEASIBLE") and solver.ObjectiveValue() == 0:
        # decode
        edges, cells = [], []
        for ei, (u, v) in enumerate(candidates):
            if solver.Value(x[ei]) == 1:
                if u == v:
                    cells.append((u, u))
                else:
                    oi = solver.Value(orient[ei])
                    cells.append((u, v) if oi == 0 else (v, u))
                edges.append((u, v))
        res["found"] = True
        res["edges"] = edges
        res["cells"] = cells
        res["objective"] = 0
    elif status in ("OPTIMAL", "FEASIBLE"):
        res["objective"] = int(solver.ObjectiveValue())
    return res

# ---------------------------------------------------------------------------
# validation against the incremental Board (proves the model is correct)
# ---------------------------------------------------------------------------
def validate(lo=5, hi=12, per=30):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "st", os.path.join(HERE, "solver_theory_m37.py"))
    st = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(st)
    allok = True
    for m in range(lo, hi + 1):
        r = solve(m, time_limit=per, verbose=True)
        ok = False
        if r["found"]:
            board = st.Board(m)
            board.build(r["edges"], r["cells"])
            ok = (board.total_bad == 0)
            if not ok:
                print(f"  m={m}: SOLVED but Board.total_bad={board.total_bad} "
                      f"(model/decoder mismatch!)", flush=True)
        print(f"  m={m}: status={r['status']} obj={r['objective']} "
              f"verify={ok}", flush=True)
        allok = allok and ok
    print("VALIDATION", "PASS" if allok else "FAIL")
    return allok

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--time", type=float, default=600)
    ap.add_argument("--out", default="results/cpsat_m37.json")
    ap.add_argument("--hints", default=None)
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()
    if args.validate:
        validate()
    else:
        hints = None
        if args.hints:
            with open(args.hints) as f:
                h = json.load(f)
            hints = (h["edges"], h["cells"])
        r = solve(args.m, time_limit=args.time, hints=hints, verbose=True)
        print(f"RESULT m={args.m}: status={r['status']} objective={r['objective']} "
              f"found={r['found']} time={r['time']:.1f}s", flush=True)
        if r["found"]:
            out = {"m": args.m, "found": True, "edges": r["edges"],
                   "cells": r["cells"]}
            with open(args.out, "w") as f:
                json.dump(out, f)
            print(f"  saved solution -> {args.out}")
