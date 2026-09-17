"""
swarm_D1_seeded.py  --  Long ILS SA attack SEEDED from the best-72 config, to test
whether the deep local min (72) can be escaped via two-switch restructuring +
perturbation.  Uses the VALIDATED engine; any candidate total_bad==0 is
independently confirmed with Board.verify_total() before being called a solution.
"""
import os, sys, json, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import solver_theory_m37 as S

def main():
    best = json.load(open(os.path.join(os.path.dirname(__file__),
                                        "solver_theory_m37_long.json")))
    rng = random.Random(424242)
    t0 = time.time()
    BUDGET = 600.0
    board = S.Board(37)
    board.build(best["edges"], best["cells"])
    cur = board.total_bad
    best_bad = cur
    best_edges = list(board.edges); best_cells = list(board.cells)
    E = 37
    stuck = 0
    T0, Tend = 8.0, 0.02
    while time.time() - t0 < BUDGET and cur > 0:
        frac = (time.time() - t0) / BUDGET
        T = T0 * (Tend / T0) ** frac
        if stuck >= 2500:
            board.build(best_edges, best_cells)
            cur = best_bad
            for _ in range(14):
                if rng.random() < 0.6:
                    e = rng.randrange(E)
                    if board.edges[e][0] != board.edges[e][1]:
                        board.flip_orientation(e)
                else:
                    e1 = rng.randrange(E); e2 = rng.randrange(E)
                    if e1 != e2:
                        board.two_switch(e1, e2)
            cur = board.total_bad
            stuck = 0; T = max(T, T0 * 0.5)
        # defect-directed move
        if board.hot and rng.random() < 0.6:
            if rng.random() < 0.6:
                cand = [e for e in board.hot if board.edges[e][0] != board.edges[e][1]]
                e = rng.choice(cand) if cand else rng.randrange(E)
                if board.edges[e][0] == board.edges[e][1]:
                    continue
                before = board.total_bad
                board.flip_orientation(e); newbad = board.total_bad
                delta = newbad - before
                if newbad <= before or rng.random() < __import__("math").exp(-delta / max(T, 1e-6)):
                    cur = newbad
                else:
                    board.flip_orientation(e); cur = board.total_bad
            else:
                e1 = rng.choice(list(board.hot)); e2 = rng.choice(list(board.hot))
                if e1 == e2:
                    continue
                before = board.total_bad
                delta, undo = board.two_switch(e1, e2)
                if undo is None:
                    continue
                newbad = board.total_bad
                if newbad <= before or rng.random() < __import__("math").exp(-delta / max(T, 1e-6)):
                    cur = newbad
                else:
                    board.undo_two_switch(undo); cur = board.total_bad
        else:
            if rng.random() < 0.6:
                e = rng.randrange(E)
                if board.edges[e][0] == board.edges[e][1]:
                    continue
                before = board.total_bad
                board.flip_orientation(e); newbad = board.total_bad
                delta = newbad - before
                if newbad <= before or rng.random() < __import__("math").exp(-delta / max(T, 1e-6)):
                    cur = newbad
                else:
                    board.flip_orientation(e); cur = board.total_bad
            else:
                e1 = rng.randrange(E); e2 = rng.randrange(E)
                if e1 == e2:
                    continue
                before = board.total_bad
                delta, undo = board.two_switch(e1, e2)
                if undo is None:
                    continue
                newbad = board.total_bad
                if newbad <= before or rng.random() < __import__("math").exp(-delta / max(T, 1e-6)):
                    cur = newbad
                else:
                    board.undo_two_switch(undo); cur = board.total_bad
        if cur < best_bad:
            best_bad = cur
            best_edges = list(board.edges); best_cells = list(board.cells)
            stuck = 0
            print(f"  t={time.time()-t0:.0f}s new best_bad={best_bad}", flush=True)
        else:
            stuck += 1
    # independent verification of the global best
    b2 = S.Board(37); b2.build(best_edges, best_cells)
    vt = b2.verify_total()
    out = {"seed": "best-72 config", "budget_s": BUDGET,
           "best_incr": best_bad, "verify_total": vt,
           "found": vt == 0,
           "edges": best_edges, "cells": best_cells}
    json.dump(out, open(os.path.join(os.path.dirname(__file__),
                                     "swarm_D1_seeded.json"), "w"), indent=2)
    print("SEEDED DONE best_incr=%d verify_total=%d found=%s" %
          (best_bad, vt, vt == 0), flush=True)

if __name__ == "__main__":
    main()
