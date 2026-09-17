"""D4: Lift the m=36 rot4 solution to m=37 via structured extension
(loop-extension + single-edge splits), then optimize orientation / 2-factor
structure with the VALIDATED SA engine to minimize (X). Breakthrough = verify_total()==0.

Time-budgeted to ~23 min. Writes results/swarm_D4_lift.json incrementally.
"""
import os, sys, json, time, random
from math import isqrt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver_theory_m37 import Board, sa_search

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'results', 'swarm_D4_lift.json')

cells36 = [tuple(c) for c in json.load(open(os.path.join(HERE, 'results/solutions/m36.json')))['cells']]
assert len(cells36) == 36

def edges_from_cells(cells):
    return [tuple(sorted(c)) for c in cells]

def initial_X(cells, m=37):
    b = Board(m); b.build(edges_from_cells(cells), cells)
    return b.verify_total()

def verify_2factor(edges, m):
    deg = [0]*m; seen = set()
    for (u, v) in edges:
        if (u, v) in seen or (v, u) in seen:
            return False
        seen.add((u, v)); deg[u]+=1; deg[v]+=1
    return all(d==2 for d in deg)

def save(ob, hist, found_flag):
    out = {"m": 37, "direction": "D4 structured lift from m=36",
           "found": found_flag, "best_bad": ob['best'] if ob else None,
           "edges": ob['edges'] if ob else None,
           "cells": ob['cells'] if ob else None,
           "note": "loop-extension + single-edge splits of the m=36 36-cycle, "
                   "optimized with validated SA (defect-directed ILS)."}
    if ob is not None:
        bb = Board(37); bb.build(ob['edges'], ob['cells'])
        defects = []; maxs = 0
        for k, p in bb.pc.items():
            s = (1 + isqrt(1 + 8*p)) // 2
            if s >= 3:
                maxs = max(maxs, s)
                defects.append({"line": list(k), "points": s,
                                "triples": bb._c3_from_pairs(p)})
        defects.sort(key=lambda d: -d["points"])
        out["lifts"] = bb.lifts
        out["n_defect_lines"] = len(defects)
        out["max_line_size"] = maxs
        out["defect_lines"] = defects[:60]
        out["n_lifts"] = len(bb.lifts)
    out["history"] = hist
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)

# ---- build seed list ----
seeds = [("loop", cells36 + [(36, 36)])]
for c in cells36:
    a, b = c
    if c == (a, b):
        nc = [cc for cc in cells36 if cc != c] + [(a, 36), (36, b)]
    else:
        nc = [cc for cc in cells36 if cc != c] + [(b, 36), (36, a)]
    seeds.append((f"split{c}", nc))

scored = sorted((initial_X(cells), name, cells) for name, cells in seeds)
loop_entry = next(e for e in scored if e[1] == "loop")
top_splits = [e for e in scored if e[1] != "loop"][:6]
chosen = [loop_entry] + top_splits
print(f"Chosen {len(chosen)} seeds (loop + 6 best splits). "
      f"initial X: {chosen[0][0]}..{chosen[-1][0]}", flush=True)

T0 = time.time()
DEADLINE = T0 + 1380
PER_SEED = 150
rng = random.Random(20260715)
overall_best = None
history = []

for idx, (ix, name, cells) in enumerate(chosen):
    if time.time() - T0 > DEADLINE - PER_SEED:
        print(f"  [time] stopping before seed {name}", flush=True); break
    edges = edges_from_cells(cells)
    assert verify_2factor(edges, 37), f"seed {name} not a valid 2-factor"
    print(f"  seed {idx} {name}: init X={ix}, SA {PER_SEED}s ...", flush=True)
    res = sa_search(37, time_budget=PER_SEED, rng=rng, init_edges=edges,
                    init_cells=cells, defect_directed=True, flip_frac=0.75,
                    T0=8.0, Tend=0.02, perturb=12)
    bb = Board(37); bb.build(res['edges'], res['cells'])
    vt = bb.verify_total()
    twf = verify_2factor([tuple(sorted(e)) for e in res['edges']], 37)
    found = (res['best'] == 0 and vt == 0 and twf)
    print(f"    -> SA best={res['best']} verify_total={vt} 2factor={twf} found={found}", flush=True)
    history.append({"seed": name, "init_X": ix, "sa_best": res['best'],
                    "verify_total": vt, "2factor": twf, "found": found, "time": res['time']})
    if overall_best is None or res['best'] < overall_best['best']:
        overall_best = res
    save(overall_best, history, found)
    if found:
        print(f"  *** BREAKTHROUGH on seed {name} ***", flush=True); break

# ---- final polish on the overall best config (if time remains) ----
remaining = DEADLINE - (time.time() - T0)
if overall_best is not None and remaining > 90 and not (overall_best['best'] == 0):
    polish = min(300, int(remaining) - 10)
    print(f"\n  final polish: SA {polish}s on best config (X={overall_best['best']}) ...", flush=True)
    res = sa_search(37, time_budget=polish, rng=rng,
                    init_edges=overall_best['edges'], init_cells=overall_best['cells'],
                    defect_directed=True, flip_frac=0.7, T0=6.0, Tend=0.01, perturb=16)
    bb = Board(37); bb.build(res['edges'], res['cells'])
    vt = bb.verify_total(); twf = verify_2factor([tuple(sorted(e)) for e in res['edges']], 37)
    found = (res['best'] == 0 and vt == 0 and twf)
    print(f"    -> polish best={res['best']} verify_total={vt} found={found}", flush=True)
    history.append({"seed": "polish-best", "init_X": overall_best['best'],
                    "sa_best": res['best'], "verify_total": vt, "2factor": twf,
                    "found": found, "time": res['time']})
    if res['best'] < overall_best['best']:
        overall_best = res
    save(overall_best, history, found)

print(f"\n== D4 done. best_bad={overall_best['best'] if overall_best else None} "
      f"found={overall_best and overall_best['best']==0} ==  saved {OUT}", flush=True)
