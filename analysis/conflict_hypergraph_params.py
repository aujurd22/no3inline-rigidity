"""Compute conflict hypergraph parameters for the rot4 NTIL problem.
Measures: (X) triple degree per cell, (S) edge degree, effective sparsity."""

import sys, json, math, time
from collections import Counter

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def line_key(p, q):
    x1, y1 = p; x2, y2 = q
    A, B, C = y2 - y1, x1 - x2, x2 * y1 - x1 * y2
    g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
    if g: A //= g; B //= g; C //= g
    if A < 0 or (A == 0 and B < 0): A, B, C = -A, -B, -C
    return (A, B, C)

def build_line_pts(pts):
    n = len(pts); lp = {}
    for i in range(n):
        xi, yi = pts[i]
        for j in range(i + 1, n):
            xj, yj = pts[j]
            if xi == xj and yi == yj: continue
            k = line_key((xi, yi), (xj, yj))
            s = lp.get(k)
            if s is None: lp[k] = {i, j}
            else: s.add(i); s.add(j)
    return lp

def cells_from_2factor(xs, ys):
    """Cells from 2-factor representation (parallel arrays)."""
    return list(zip(xs, ys))

def pts_from_cells(cells, m):
    N = 2 * m
    return [c4(c, r, N) for c in cells for r in range(4)]

def measure_hypergraph(m, nsamp=200):
    """Sample random 2-factors and measure (X)/(S) conflict parameters."""
    import random
    rng = random.Random(0)
    N = 2 * m
    
    # Degree counters
    x_deg = Counter()   # (i,j) → number of (X) triples it's in (from sampled factors)
    s_edge_count = 0   # total (S) edges in sampled factors
    x_triple_count = 0 # total (X) triples in sampled factors
    total_pairs_sampled = 0
    
    for _ in range(nsamp):
        # Generate random 2-factor (configuration model)
        xs = list(range(m))
        ys = list(range(m))
        rng.shuffle(xs)
        rng.shuffle(ys)
        cells = list(zip(xs, ys))
        pts = pts_from_cells(cells, m)
        
        # Build line-point map → identify bad lines
        lp = build_line_pts(pts)
        
        # For each line with ≥3 points, identify which cells caused it
        for k, pt_set in lp.items():
            n_pts = len(pt_set)
            if n_pts >= 3:
                # Map point indices back to cells
                involved_cells = set(idx // 4 for idx in pt_set)
                nc = len(involved_cells)
                if nc == 3:  # (X) type: 3 distinct cells
                    for c_in in involved_cells:
                        x_deg[cells[c_in]] += 1
                    x_triple_count += 1
                elif nc == 2:  # (S) type: 2 cells, ≥3 lifted points
                    s_edge_count += 1
                # nc==1 would be a single cell with ≥3 lifted points = loop
        total_pairs_sampled += 1
    
    avg_x_deg = sum(x_deg.values()) / max(1, len(x_deg)) if x_deg else 0
    avg_x_per_factor = x_triple_count / nsamp
    avg_s_per_factor = s_edge_count / nsamp
    
    return {
        "m": m, "nsamp": nsamp,
        "avg_x_per_factor": avg_x_per_factor,
        "avg_s_per_factor": avg_s_per_factor,
        "avg_total_bad_per_factor": (x_triple_count + s_edge_count) / nsamp,
        "avg_x_deg_per_cell": avg_x_deg,
        "unique_cells_in_x": len(x_deg),
        "x_deg_max": max(x_deg.values()) if x_deg else 0,
    }

# Run for selected m
results = {}
for m in [10, 14, 18, 22, 26, 30, 37]:
    t0 = time.time()
    r = measure_hypergraph(m, nsamp=min(500, 10000 // m))
    r["time_s"] = round(time.time() - t0, 1)
    results[m] = r
    print(f"m={m}: avg_bad={r['avg_total_bad_per_factor']:.2f}, "
          f"avg_x_deg={r['avg_x_deg_per_cell']:.3f}, "
          f"max_x_deg={r['x_deg_max']}, "
          f"unique_cells_in_x={r['unique_cells_in_x']}, "
          f"{r['time_s']}s", flush=True)

with open("results/conflict_hypergraph_params.json", "w") as f:
    json.dump(results, f, indent=1)

print("\nDone. Results saved to results/conflict_hypergraph_params.json")
