"""
swarm_D5_search2.py  --  D5 direction auxiliary: directly test whether the
"72 deep local min" can be BEATEN.  If we find total_bad < 72 (ideally 0),
that refutes the impossibility hypothesis for m=37 and is a positive
breakthrough; if 72 holds as a global minimum after a serious attempt, that
strengthens (but still does NOT prove) impossibility.

Strategy (engine = solver_theory_m37.Board, validated):
  * Seed from the best known 72-config (a 2-factor structural local min where
    flip-only greedy is stuck).
  * Use defect-directed ILS with a HIGHER two_switch fraction than the default
    (two_switch is the only move type that can escape a 2-factor local min).
  * Larger perturbation (more random two_switches) to kick off the optimum.
  * Verify the returned best with Board.verify_total() (independent brute force)
    and confirm legal 2-factor + rot4 before reporting.
"""
import os, sys, json, math, random, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as E

OUT = os.path.join(HERE, "results", "swarm_D5_search2.json")

def main():
    rng = random.Random(20260715)
    m = 37
    # load 72 seed
    cfg = json.load(open(os.path.join(HERE, "results", "solver_theory_m37_long.json")))
    seed_edges = [tuple(e) for e in cfg["edges"]]
    seed_cells = [tuple(c) for c in cfg["cells"]]

    T0, Tend = 12.0, 0.01
    flip_frac = 0.35          # favor two_switch (escapes 2-factor local min)
    perturb = 40              # bigger perturbation
    time_budget = 1450.0      # ~24 min total across restarts
    n_restarts = 6
    STUCK = 1200

    overall_best = None
    print(f"== D5 search2: test beatability of 72 (m={m}, {n_restarts} restarts x "
          f"~{time_budget/n_restarts:.0f}s, flip_frac={flip_frac}, perturb={perturb}) ==")

    for rs in range(n_restarts):
        t0 = time.time()
        board = E.Board(m)
        board.build(seed_edges, seed_cells)
        cur = board.total_bad
        best = cur
        best_edges = list(board.edges); best_cells = list(board.cells)
        stuck = 0
        while time.time() - t0 < time_budget / n_restarts and cur > 0:
            frac = (time.time() - t0) / (time_budget / n_restarts)
            T = T0 * (Tend / T0) ** frac
            if stuck >= STUCK:
                board.build(best_edges, best_cells)
                cur = best
                # perturbation: random two_switches
                for _ in range(perturb):
                    e1 = rng.randrange(m); e2 = rng.randrange(m)
                    if e1 != e2:
                        board.two_switch(e1, e2)
                cur = board.total_bad
                stuck = 0
                T = max(T, T0 * 0.6)
            # defect-directed choice
            dd = board.hot and rng.random() < 0.8
            if rng.random() < flip_frac:
                e = (rng.choice(list(board.hot)) if dd else rng.randrange(m))
                if board.edges[e][0] == board.edges[e][1]:
                    continue
                before = board.total_bad
                board.flip_orientation(e)
                newbad = board.total_bad
                if newbad <= before or rng.random() < math.exp(-(newbad - before) / max(T, 1e-6)):
                    cur = newbad
                else:
                    board.flip_orientation(e); cur = board.total_bad
            else:
                e1 = (rng.choice(list(board.hot)) if dd else rng.randrange(m))
                e2 = (rng.choice(list(board.hot)) if dd else rng.randrange(m))
                if e1 == e2:
                    continue
                before = board.total_bad
                delta, undo = board.two_switch(e1, e2)
                if undo is None:
                    continue
                newbad = board.total_bad
                if newbad <= before or rng.random() < math.exp(-delta / max(T, 1e-6)):
                    cur = newbad
                else:
                    board.undo_two_switch(undo); cur = board.total_bad
            if cur < best:
                best = cur
                best_edges = list(board.edges); best_cells = list(board.cells)
                stuck = 0
                print(f"  rs{rs} improved to {best} at t={time.time()-t0:.0f}s", flush=True)
            else:
                stuck += 1
        print(f"  restart {rs}: best_bad={best} time={time.time()-t0:.0f}s", flush=True)
        if overall_best is None or best < overall_best["best"]:
            overall_best = {"best": best, "edges": best_edges, "cells": best_cells}

    # independent verification of the best
    b = E.Board(m)
    b.build(overall_best["edges"], overall_best["cells"])
    vt = b.verify_total()
    # 2-factor check
    rs=[0]*m; cs=[0]*m
    for (x,y) in overall_best["cells"]:
        rs[x]+=1; cs[y]+=1
    twf = all(rs[i]+cs[i]==2 for i in range(m))
    L = b.lifts
    rot = set(L) == set(E.c4(x,y,r,2*m) for (x,y) in overall_best["cells"] for r in range(4))
    print(f"\n== best_bad={overall_best['best']} verify_total={vt} 2factor={twf} "
          f"rot4set={rot} found={vt==0} ==")
    out = {"m": m, "best_bad": overall_best["best"], "verify_total": vt,
           "two_factor": twf, "rot4_set": rot, "found": vt == 0,
           "seed_was": 72,
           "edges": overall_best["edges"], "cells": overall_best["cells"],
           "note": ("ILS two-switch-biased search seeded from the 72 local min. "
                    "If best_bad<72 it refutes the 'deep local min = global min' "
                    "interpretation; best_bad==0 would be a breakthrough rot4-NTIL.")}
    json.dump(out, open(OUT, "w"), indent=2)
    print(f"saved {OUT}")

if __name__ == "__main__":
    main()
