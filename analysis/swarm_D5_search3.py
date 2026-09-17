"""
swarm_D5_search3.py  --  D5 auxiliary #2: FRESH-RANDOM-START search (independent
basins from the 72-config seed), to test whether a config with total_bad < 72
exists.  Uses the validated engine's sa_search with defect-directed moves and
a longer per-restart budget.  Reports the best found, independently verified.
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_theory_m37 as E

OUT = os.path.join(HERE, "results", "swarm_D5_search3.json")

def main():
    rng = random.Random(777)
    m = 37
    n_restarts = 8
    time_each = 150.0
    overall_best = None
    print(f"== D5 search3: fresh-start defect-directed SA, m={m}, "
          f"{n_restarts} x {time_each}s ==")
    for rs in range(n_restarts):
        res = E.sa_search(m, time_budget=time_each, rng=rng,
                           defect_directed=True, T0=10.0, Tend=0.015,
                           flip_frac=0.4, perturb=20)
        if res is None:
            print(f"  rs{rs}: 2factor gen failed"); continue
        print(f"  rs{rs}: best_bad={res['best']} found={res['found']}", flush=True)
        if res["found"]:
            overall_best = res; break
        if overall_best is None or res["best"] < overall_best["best"]:
            overall_best = res
    # independent verification
    b = E.Board(m)
    b.build(overall_best["edges"], overall_best["cells"])
    vt = b.verify_total()
    rs = [0]*m; cs = [0]*m
    for (x, y) in overall_best["cells"]:
        rs[x]+=1; cs[y]+=1
    twf = all(rs[i]+cs[i]==2 for i in range(m))
    print(f"\n== best_bad={overall_best['best']} verify_total={vt} 2factor={twf} "
          f"found={vt==0} ==")
    out = {"m": m, "best_bad": overall_best["best"], "verify_total": vt,
           "two_factor": twf, "found": vt == 0,
           "edges": overall_best["edges"], "cells": overall_best["cells"],
           "seed": "fresh random, defect-directed SA"}
    json.dump(out, open(OUT, "w"), indent=2)
    print(f"saved {OUT}")

if __name__ == "__main__":
    import random
    main()
