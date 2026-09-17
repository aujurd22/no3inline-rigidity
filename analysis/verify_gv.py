"""
verify_gv.py — Verify geometric violation count for known configs.

The deep search found [29,8] has the lowest GV (63) with naive orientation.
But the best known config (config_408) has cycle type [28,9] and achieves
16 violations with optimized orientation.

This script checks:
1. What's the GV count for config_408's actual edges?
2. What's the GV count for the new best [29,8] edges?
3. What's the actual clause count for [29,8] with naive orientation?

If [29,8] has both lower GV AND lower clauses than config_408, it's
a genuinely better candidate.
"""
import os, sys, json, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solver_theory_m37 import c4

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))

def c4_cell(x, y, r, n):
    return c4(x, y, r, n)

def count_geometric_violations(cells, m):
    n = 2 * m
    lifts = []
    for (x, y) in cells:
        lifts.append([c4(x, y, r, n) for r in range(4)])
    
    r8_patterns = [
        (0,1,0),(0,1,1),(0,1,2),(0,1,3),
        (0,2,0),(0,2,1),(0,2,2),(0,2,3),
        (0,3,0),(0,3,1),(0,3,2),(0,3,3),
        (0,0,1),(0,0,2),(0,0,3),(0,0,0),
    ]
    
    viol = 0
    for i in range(m):
        for j in range(i + 1, m):
            for k in range(j + 1, m):
                found = False
                for ri, rj, rk in r8_patterns:
                    pi = lifts[i][ri]; pj = lifts[j][rj]; pk = lifts[k][rk]
                    if pi == pj or pj == pk or pk == pi:
                        continue
                    det = (pj[0]-pi[0])*(pk[1]-pi[1]) - (pk[0]-pi[0])*(pj[1]-pi[1])
                    if det == 0:
                        found = True; break
                if found:
                    viol += 1
    return viol

# Load config_408
with open(os.path.join(HERE, "results", "config_408_edges.json")) as f:
    d408 = json.load(f)
edges_408 = [(e[0], e[1]) for e in d408["edges"]]
cells_408 = [(u, v) for (u, v) in edges_408]  # naive orientation

gv_408 = count_geometric_violations(cells_408, M)
print(f"config_408:")
print(f"  Cycle type: [9,28]")
print(f"  Edges: {len(edges_408)}")
print(f"  GV (naive orient): {gv_408}")
print(f"  Known violations (optimal): 16")
print(f"  Ratio: {gv_408 / 16:.2f}")
print()

# Load the new best config ([29,8] from deep search)
try:
    with open(os.path.join(HERE, "results", "best_gv_63_edges.json")) as f:
        best = json.load(f)
    cells_best = [(e[0], e[1]) for e in best["edges"]]
    gv_best = count_geometric_violations(cells_best, M)
    print(f"Best [29,8] config:")
    print(f"  Edges: {len(best['edges'])}")
    print(f"  GV (naive orient): {gv_best}")
except FileNotFoundError:
    print("No best_gv_63_edges.json found")
