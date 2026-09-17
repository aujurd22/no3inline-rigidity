#!/usr/bin/env python3
"""
Brute-force enumeration of ALL 2-switches from best72.
For each pair of edges (i,j), try both 2-switch alternatives
and compute the clause count.
Saves all improvements found.
"""
import sys, os, json, math, time, random
from collections import defaultdict, Counter

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H

OUT = os.path.join(HERE, "results", "brute_2switch_best72.json")

# best72 edges (THE ORDER MATTERS for indexing in clauses)
best72_edges = sorted([
    (15,34), (10,24), (3,23), (7,28), (2,23), (8,25), (16,30),
    (7,18), (3,29), (9,35), (11,17), (9,32), (12,36), (6,15),
    (6,31), (14,36), (1,19), (8,24), (20,25), (4,19), (12,27),
    (21,33), (5,35), (13,29), (1,27), (5,22), (21,32), (20,26),
    (0,33), (16,28), (14,22), (13,26), (10,17), (11,18), (2,34),
    (0,30), (4,31)
])

print(f"best72 baseline: {H.count_clauses_fast(M, best72_edges)} clauses", flush=True)

improvements = []
best_overall = 470

E = len(best72_edges)
t0 = time.time()

# Test ALL edge pairs
for i in range(E):
    e1 = best72_edges[i]
    for j in range(i + 1, E):
        e2 = best72_edges[j]
        u1, v1 = e1
        u2, v2 = e2
        
        # Must have 4 distinct vertices
        if len({u1, v1, u2, v2}) < 4:
            continue
        
        # Two 2-switch results
        for (nu1, nv1, nu2, nv2) in [(u1, u2, v1, v2), (u1, v2, v1, u2)]:
            if nu1 == nv1 or nu2 == nv2:
                continue
            cand = list(best72_edges)
            cand[i] = (nu1, nv1) if nu1 <= nv1 else (nv1, nu1)
            cand[j] = (nu2, nv2) if nu2 <= nv2 else (nv2, nu2)
            cand = sorted(cand)
            
            # Quick validity check
            deg = Counter()
            for u, v in cand:
                deg[u] += 1
                deg[v] += 1
            if any(d != 2 for d in deg.values()):
                continue
            
            nc = H.count_clauses_fast(M, cand)
            
            if nc < best_overall:
                best_overall = nc
                improvements.append({
                    "removed": [e1, e2],
                    "added": [(nu1, nv1) if nu1 <= nv1 else (nv1, nu1),
                              (nu2, nv2) if nu2 <= nv2 else (nv2, nu2)],
                    "clauses": nc,
                    "time_s": round(time.time() - t0, 1),
                })
                print(f"  ** IMPROVEMENT: {nc} clauses: remove {e1},{e2} add ({nu1},{nv1}),({nu2},{nv2})", flush=True)
    
    # Progress every 10 edges
    if (i + 1) % 5 == 0:
        elapsed = time.time() - t0
        eta = elapsed / (i + 1) * (E - i - 1)
        print(f"  Progress: {i+1}/{E} sources checked ({elapsed:.0f}s, ETA ~{eta:.0f}s)", flush=True)

print(f"\nEnumeration complete! Time: {time.time()-t0:.0f}s", flush=True)

# Save
result = {
    "baseline_clauses": 470,
    "best_found_clauses": best_overall,
    "n_improvements": len(improvements),
    "improvements": sorted(improvements, key=lambda x: x["clauses"]),
}
with open(OUT, "w") as f:
    json.dump(result, f, indent=2)

print(f"\nBest improvement: {best_overall} clauses", flush=True)
print(f"Total improvements found: {len(improvements)}", flush=True)
if improvements:
    best_imp = min(improvements, key=lambda x: x["clauses"])
    print(f"Best switch: remove {best_imp['removed']}, add {best_imp['added']}", flush=True)
