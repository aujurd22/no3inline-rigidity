#!/usr/bin/env python3
"""
Smart 2-switch enumeration: test all pairs, but stop early
when a pattern emerges, and focus on the most promising vertex sets.
Uses optimization: only re-check triples involving changed edges.
"""
import sys, os, json, math, time, random
from collections import defaultdict, Counter

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_2factor_sat_pipeline as P

OUT = os.path.join(HERE, "results", "smart_2switch.json")

best72_edges = sorted([
    (15,34), (10,24), (3,23), (7,28), (2,23), (8,25), (16,30),
    (7,18), (3,29), (9,35), (11,17), (9,32), (12,36), (6,15),
    (6,31), (14,36), (1,19), (8,24), (20,25), (4,19), (12,27),
    (21,33), (5,35), (13,29), (1,27), (5,22), (21,32), (20,26),
    (0,33), (16,28), (14,22), (13,26), (10,17), (11,18), (2,34),
    (0,30), (4,31)
])

# Precompute the FULL clause set for best72
clauses72, cmap72 = P.enumerate_clauses(M, best72_edges, verbose=False)
n_base = len(clauses72)
print(f"best72 baseline: {n_base} clauses", flush=True)

# For efficiency, use count_clauses_fast instead of incremental
import hamiltonian_sweep as H

E = len(best72_edges)
improvements = []
t0 = time.time()

# Track which vertex sets produce improvements
vertex_hits = Counter()

for i in range(E):
    e1 = best72_edges[i]
    for j in range(i + 1, E):
        e2 = best72_edges[j]
        u1, v1 = e1
        u2, v2 = e2
        
        if len({u1, v1, u2, v2}) < 4:
            continue
        
        for (nu1, nv1, nu2, nv2) in [(u1, u2, v1, v2), (u1, v2, v1, u2)]:
            if nu1 == nv1 or nu2 == nv2:
                continue
            cand = list(best72_edges)
            cand[i] = (nu1, nv1) if nu1 <= nv1 else (nv1, nu1)
            cand[j] = (nu2, nv2) if nu2 <= nv2 else (nv2, nu2)
            cand = sorted(cand)
            
            nc = H.count_clauses_fast(M, cand)
            
            if nc < n_base:
                improvements.append({
                    "removed": [e1, e2], "added": 
                    [(nu1, nv1) if nu1 <= nv1 else (nv1, nu1),
                     (nu2, nv2) if nu2 <= nv2 else (nv2, nu2)],
                    "clauses": nc,
                })
                print(f"  ** {nc} clauses: rm {e1},{e2} → add ({nu1},{nv1}),({nu2},{nv2})", flush=True)
                vertex_hits[(u1, v1, u2, v2)] += 1
    
    # Progress every 5 edges
    if (i + 1) % 5 == 0:
        elapsed = time.time() - t0
        print(f"  [{elapsed:.0f}s] {i+1}/{E} sources, found {len(improvements)} improvements", flush=True)

# Sort by clause count
improvements.sort(key=lambda x: x["clauses"])

result = {
    "baseline": n_base,
    "best": improvements[0]["clauses"] if improvements else n_base,
    "n_improvements": len(improvements),
    "improvements": improvements,
    "total_time_s": round(time.time() - t0, 1),
}
with open(OUT, "w") as f:
    json.dump(result, f, indent=2)

print(f"\nComplete! Time: {result['total_time_s']:.0f}s", flush=True)
print(f"Best improvement: {result['best']} clauses", flush=True)
print(f"Total improvements: {len(improvements)}", flush=True)

if improvements:
    print(f"\nTop 5 improvements:")
    for imp in improvements[:5]:
        print(f"  {imp['clauses']}: rm {imp['removed']} → add {imp['added']}")
