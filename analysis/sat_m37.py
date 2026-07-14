"""CDCL SAT attack on m=37 rot4-NTIL (research_J direction #3).

Encoding (sound + complete, validated by solve_m37_r9b --validate):
  * one Boolean var x_{a,b} per fundamental-quadrant cell  (m^2 = 1369 vars)
  * 2-FACTOR:  for each vertex i,  rowSum[i] + colSum[i] == 2
    encoded manually as (at-most-2 via pairwise forbid) AND (at-least-2).
  * per-LINE at-most-2:  for each collinearity line L with cell->weight w,
               sum_k w_k * x_k <= 2
               weights are 1 (generic) or 2 (line through rotation center),
               so forbidden subsets are: any pair with w_i+w_j>2, and every
               triple of cells (all weights>=1 => 3 cells sum>=3>2).
Solver: glucose4 (CDCL, supports interrupt).  Time cap via Timer + bash timeout.
On SAT: decode cells, independent full-cross-product verification (verify_cells),
        write results/solution_m37_sat.json.
"""
import os, sys, time, json, threading, argparse, math
sys.path.insert(0, ".")
from solve_m37_r9b import generate_constraints, verify_cells
from pysat.solvers import Solver

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--solver", default="glucose4")
    ap.add_argument("--time", type=float, default=2700.0, help="soft time cap (s)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    m = args.m
    t0 = time.time()
    reps, line_cons, twofactor = generate_constraints(m, True)
    nvar = len(reps)
    V = [i + 1 for i in range(nvar)]   # 1-indexed SAT vars for cells
    print(f"[gen] m={m} nvar={nvar} lines={len(line_cons)} "
          f"2F={len(twofactor)} ({time.time()-t0:.1f}s)", flush=True)

    s = Solver(name=args.solver, incr=True)

    # ---- 2-factor: rowSum[i]+colSum[i]==2 for each vertex i ----
    # loop cell (i,i) touches vertex i twice => weight 2. Correct encoding:
    #   x_{ii}=1  =>  all other incident cells false (loop already gives deg 2)
    #   x_{ii}=0  =>  exactly 2 of the other incident cells true
    # (previous version wrongly forbade ALL pairs => at-most-1, making the
    #  formula trivially UNSAT in 0.12s; and counted the loop with weight 1.)
    # "exactly-2 of others" is encoded with the same pairwise/ternary pattern
    # already verified for per-line at-most-2, with every clause guarded by
    # -loop_var (Tseitin embedding of the implication  -loop => (exactly-2)).
    tc = time.time()
    n2f = 0
    for i in twofactor:
        loop_var = V[i * m + i]
        others = [V[a * m + b] for a in range(m) for b in range(m)
                  if (a == i or b == i) and not (a == i and b == i)]
        no = len(others)
        # loop selected => others all false
        for o in others:
            s.add_clause([-loop_var, -o]); n2f += 1
        # loop not selected => exactly 2 of others
        # (implication -loop => C  ==  loop OR C, so guard each clause with +loop_var)
        s.add_clause([loop_var] + others); n2f += 1            # forbids all-false
        for a in range(no):
            cl = [loop_var, -others[a]] + [others[b] for b in range(no) if b != a]
            s.add_clause(cl); n2f += 1                          # forbids exactly-1
        if no >= 3:
            for a in range(no):
                for b in range(a + 1, no):
                    for c in range(b + 1, no):
                        s.add_clause([loop_var, -others[a], -others[b], -others[c]])
                        n2f += 1                                # forbids >=3
    print(f"[2f] added {n2f:,} clauses for {len(twofactor)} vertex equalities "
          f"({time.time()-tc:.1f}s)", flush=True)

    # ---- per-line at-most-2 ----
    tl = time.time()
    ncl = 0
    for d in line_cons:
        items = list(d.items())          # (cell_idx, weight)
        k = len(items)
        # forbidden pairs (w_i + w_j > 2)
        if k >= 2:
            for a in range(k):
                va = V[items[a][0]]
                wa = items[a][1]
                for b in range(a + 1, k):
                    if wa + items[b][1] > 2:
                        s.add_clause([-va, -V[items[b][0]]])
                        ncl += 1
        # forbidden triples (any 3 cells, all weights >= 1 => sum >= 3 > 2)
        if k >= 3:
            for a in range(k):
                va = V[items[a][0]]
                for b in range(a + 1, k):
                    vb = V[items[b][0]]
                    for c in range(b + 1, k):
                        s.add_clause([-va, -vb, -V[items[c][0]]])
                        ncl += 1
    print(f"[lines] added {ncl:,} forbidden clauses "
          f"({time.time()-tl:.1f}s)", flush=True)
    print(f"[ready] starting {args.solver} with {args.time:.0f}s cap "
          f"(total clauses ~= {n2f + ncl:,})", flush=True)

    # ---- time-cap via interrupt ----
    stop = threading.Event()
    def _interrupt():
        if not stop.is_set():
            try:
                s.interrupt()
            except Exception:
                pass
    timer = threading.Timer(args.time, _interrupt)
    timer.start()
    t_solve = time.time()
    try:
        sat = s.solve()
    except Exception as e:
        sat = None
        print(f"[solve] exception: {e}", flush=True)
    elapsed = time.time() - t_solve
    stop.set()
    timer.cancel()

    if sat is True:
        model = s.get_model()
        chosen = [(reps[v - 1][0], reps[v - 1][1])
                  for v in model if v > 0 and v <= nvar]
        # defense-in-depth: a valid C4 2-factor must select exactly m cells
        ok, n = verify_cells(chosen, m)
        if len(chosen) != m:
            ok = False
            print(f"[SAT] WARNING: decoded {len(chosen)} cells, expected {m} "
                  f"— rejecting as invalid", flush=True)
        print(f"[SAT] found a solution! cells={len(chosen)} "
              f"verify_full_crossproduct={ok} ({elapsed:.1f}s)", flush=True)
        out = {"m": m, "status": "SAT", "solver": args.solver,
               "cells": chosen, "verify": ok, "elapsed": elapsed}
        with open(f"results/solution_m{m}_sat.json", "w") as f:
            json.dump(out, f, indent=1)
        print("[SAT] wrote results/solution_m37_sat.json", flush=True)
    else:
        if elapsed >= args.time - 5:
            print(f"[UNKNOWN] time cap hit, no solution found "
                  f"({elapsed:.1f}s) -- inconclusive for m={m}", flush=True)
        else:
            print(f"[UNSAT] solver reports UNSAT ({elapsed:.1f}s) -- "
                  f"m={m} has NO rot4-NTIL", flush=True)
            out = {"m": m, "status": "UNSAT", "solver": args.solver,
                   "elapsed": elapsed}
            with open(f"results/solution_m{m}_sat.json", "w") as f:
                json.dump(out, f, indent=1)
    s.delete()

if __name__ == "__main__":
    main()
