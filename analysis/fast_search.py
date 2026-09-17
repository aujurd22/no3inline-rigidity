#!/usr/bin/env python3
"""
Fast mutation search starting from known-good cycles.
Saves best result immediately when found.
"""
import sys, os, json, math, time, random
from collections import defaultdict, Counter

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H

OUT = os.path.join(HERE, "results", "fast_search_best.json")

# Start from the known 452-clause cycle
seed_edges = sorted([
    (0,30), (0,33), (1,19), (1,27), (2,23), (2,34), (3,23), (3,29),
    (4,7), (4,19), (5,22), (5,35), (6,15), (6,31), (7,18),
    (8,24), (8,25), (9,32), (9,35), (10,17), (10,24), (11,17), (11,18),
    (12,27), (12,36), (13,26), (13,29), (14,22), (14,36),
    (15,34), (16,28), (16,30), (20,25), (20,26), (21,32), (21,33), (28,31)
])

current_edges = list(seed_edges)
current_nc = H.count_clauses_fast(M, current_edges)
best_edges = list(current_edges)
best_nc = current_nc

print(f"Start: {best_nc} clauses", flush=True)

# Quick save
with open(OUT, "w") as f:
    json.dump({"best_clauses": best_nc, "step": 0, "edges": sorted(best_edges)}, f, indent=2)

rng = random.Random(20260715)
history = [(0, best_nc)]

for step in range(3000):
    # Try a 2-switch
    e = list(current_edges)
    i, j = rng.sample(range(len(e)), 2)
    u1, v1 = e[i]
    u2, v2 = e[j]
    if len({u1, v1, u2, v2}) < 4:
        continue
    
    # Both alternatives
    cands = []
    for (nu1, nv1, nu2, nv2) in [(u1, u2, v1, v2), (u1, v2, v1, u2)]:
        if nu1 == nv1 or nu2 == nv2:
            continue
        c = list(e)
        c[i] = (nu1, nv1) if nu1 <= nv1 else (nv1, nu1)
        c[j] = (nu2, nv2) if nu2 <= nv2 else (nv2, nu2)
        c = sorted(c)
        if len(set(c)) == M:
            cands.append(c)
    
    if not cands:
        continue
    
    # Accept if better, or with some probability
    cand = rng.choice(cands)
    nc = H.count_clauses_fast(M, cand)
    
    if nc <= current_nc:
        current_nc = nc
        current_edges = cand
        
        if nc < best_nc:
            best_nc = nc
            best_edges = list(cand)
            print(f"Step {step}: NEW BEST {nc} clauses", flush=True)
            history.append((step, best_nc))
            with open(OUT, "w") as f:
                json.dump({"best_clauses": best_nc, "step": step,
                          "edges": sorted(best_edges), "history": history}, f, indent=2)
    
    # Restart from best periodically
    if step % 200 == 199:
        current_edges = list(best_edges)
        current_nc = best_nc
        print(f"  Step {step}: restart from best={best_nc}", flush=True)

print(f"\nFinal best: {best_nc} clauses", flush=True)
with open(OUT, "w") as f:
    json.dump({"best_clauses": best_nc, "step": step,
              "edges": sorted(best_edges), "history": history}, f, indent=2)
