"""
Benchmark: how fast is enumerate_clauses for 1 config?
Then produce a fast clause proxy.
"""
import sys, time, json
sys.path.insert(0, "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis")
from solver_2factor_sat_pipeline import enumerate_clauses

M = 37

# Load config_408
with open("D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis\\results\\config_408_edges.json") as f:
    data = json.load(f)
edges = [tuple(e) for e in data["edges"]]

# Time one call
t0 = time.time()
clauses, cmap = enumerate_clauses(M, edges, verbose=False)
t = time.time() - t0
print(f"enumerate_clauses: {t:.3f}s for {len(clauses)} clauses")
print(f"  That's ≈ {t*1000/len(edges):.2f}ms per edge")
print(f"  C(37,3) = {M*(M-1)*(M-2)//6} triples checked")

# For 5000 configs
total = t * 5000
print(f"\n5000 configs would take: {total:.0f}s = {total/60:.1f}min")

# Faster approach: precompute the collinearity matrix
# For each pair of (cell_coords, orientation), we have 4 lifts
# Precompute ALL lift coordinates
n = 2 * M

def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = n - 1 - y, x
        pts.append((x, y))
    return pts

# Precompute all 8 orbits (37 cells × 2 orientations)
t1 = time.time()
all_orbits = {}
for u in range(M):
    for v in range(M):
        all_orbits[(u,v,0)] = c4_lift(u, v)
        all_orbits[(u,v,1)] = c4_lift(v, u)
t2 = time.time()
print(f"\nPrecompute all {2*M*M} orbits: {t2-t1:.3f}s")

# Now count clauses quickly for any config
# For each triple, check all 8 orientation combos
# but using precomputed orbits
from itertools import combinations

# Precompute: for each triple of cells (by coordinates), which orientation combos are bad?
# This is the key: we can look up (cell coordinates, orientation) → 4 lifts instantly
# But we still need to check collinearity

def fast_count(edges):
    """Count clauses using precomputed orbits."""
    n_clauses = 0
    # Don't iterate all C(37,3) — precompute which triples are "interesting"
    for a, b, c in combinations(range(37), 3):
        u1,v1 = edges[a]
        u2,v2 = edges[b]
        u3,v3 = edges[c]
        for bits in range(8):
            t1 = (bits >> 0) & 1
            t2 = (bits >> 1) & 1
            t3 = (bits >> 2) & 1
            lifts = (all_orbits[(u1,v1,t1)] + 
                     all_orbits[(u2,v2,t2)] + 
                     all_orbits[(u3,v3,t3)])
            # Quick collinearity check
            bad = False
            for i in range(12):
                if bad: break
                pi = lifts[i]
                for j in range(i+1, 12):
                    if bad: break
                    pj = lifts[j]
                    if pi[0] == pj[0] and pi[1] == pj[1]:
                        continue
                    dx1, dy1 = pj[0]-pi[0], pj[1]-pi[1]
                    cnt = 2
                    for k in range(j+1, 12):
                        pk = lifts[k]
                        if pk[0] == pi[0] and pk[1] == pi[1]:
                            continue
                        dx2, dy2 = pk[0]-pi[0], pk[1]-pi[1]
                        if dx1*dy2 == dx2*dy1:  # cross product = 0
                            cnt += 1
                            if cnt >= 3:
                                bad = True
                                break
            if bad:
                n_clauses += 1
    return n_clauses

# Time the fast version on config_408
t3 = time.time()
fc = fast_count(edges)
t4 = time.time()
print(f"\nfast_count on config_408: {t4-t3:.3f}s, got {fc} clauses")
print(f"  Expected 408, got {fc} — match: {fc == len(clauses)}")
