#!/usr/bin/env python3
"""
Targeted search: starting from best72, aggressively apply 2-switches
to find cycles with minimal clauses. Saves best found every step.
"""
import sys, os, json, math, time, random
from collections import defaultdict, Counter

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H

OUT = os.path.join(HERE, "results", "targeted_search_best.json")

# Start from best72
current_edges = sorted([
    (15,34), (10,24), (3,23), (7,28), (2,23), (8,25), (16,30),
    (7,18), (3,29), (9,35), (11,17), (9,32), (12,36), (6,15),
    (6,31), (14,36), (1,19), (8,24), (20,25), (4,19), (12,27),
    (21,33), (5,35), (13,29), (1,27), (5,22), (21,32), (20,26),
    (0,33), (16,28), (14,22), (13,26), (10,17), (11,18), (2,34),
    (0,30), (4,31)
])

current_nc = H.count_clauses_fast(M, current_edges)
best_edges = list(current_edges)
best_nc = current_nc

print(f"Start: {best_nc} clauses", flush=True)

rng = random.Random(20260715)
history = [(0, best_nc)]

# Strategy: simulated annealing with periodic restarts from best
temp = 30.0
for step in range(2000):
    temp = max(0.5, temp * 0.997)
    
    # Pick 2 edges to swap
    e = list(current_edges)
    i, j = rng.sample(range(len(e)), 2)
    u1, v1 = e[i]
    u2, v2 = e[j]
    if len({u1, v1, u2, v2}) < 4:
        continue
    
    # Both 2-switch possibilities
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
    
    cand = rng.choice(cands)
    nc = H.count_clauses_fast(M, cand)
    delta = nc - current_nc
    
    if delta < 0 or rng.random() < math.exp(-delta / temp):
        current_nc = nc
        current_edges = cand
        
        if nc < best_nc:
            best_nc = nc
            best_edges = list(cand)
            print(f"Step {step}: NEW BEST {nc} clauses", flush=True)
            history.append((step, best_nc))
            # Save immediately
            with open(OUT, "w") as f:
                json.dump({"best_clauses": best_nc, "step": step,
                          "edges": sorted(best_edges), "history": history}, f, indent=2)
    
    # Periodic restart from best to avoid wandering
    if step % 100 == 99 and current_nc > best_nc + 50:
        current_edges = list(best_edges)
        current_nc = best_nc

print(f"\nFinal best: {best_nc} clauses", flush=True)
print(f"Edges: {sorted(best_edges)}", flush=True)
