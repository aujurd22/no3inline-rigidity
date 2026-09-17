"""
direction3c_deep.py — Deep cycle-type search: find absolute minimum constrained triples.

Key finding: [28,9] has min 81 constrained triples (geometrically collinear cell triples).
If each constrained triple force ~5 clauses (from the D5v2 all-4-pair ratio),
then 81 ≈ 5 × 16.2 → 16 violations minimum.

We now search more broadly:
1. More samples per type (+500 each)
2. More cycle types (every 2-cycle decomposition of 37)
3. Use the ACTUAL clause format (orientation-aware) for a better count

Also check: can we find ANY 2-factor with < 81 constrained triples?
"""
import os, sys, json, random, time
from collections import defaultdict
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

M = 37

def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def generate_2factor(m, cycle_lengths, rng):
    """Return list of (u,v) edges representing a 2-factor with given cycles.
    NOTE: 2-cycles produce duplicate unordered pairs (a,b) and (b,a) -> 
    both are kept because they represent DISTINCT C4 orbits.
    The caller uses these as cells (orientation = first element of tuple)."""
    vertices = list(range(m))
    rng.shuffle(vertices)
    cells = []  # named cells because each edge is a cell (x_i, y_i)
    pos = 0
    for clen in cycle_lengths:
        cycle_verts = vertices[pos:pos+clen]
        pos += clen
        for k in range(clen):
            u = cycle_verts[k]
            v = cycle_verts[(k + 1) % clen]
            # Keep as-is; duplicates are OK (different C4 orbits)
            cells.append((u, v))
    assert len(cells) == m, f"generate_2factor: {len(cells)} != {m}"
    return cells

def count_geometric_violations(cells, m):
    """Count cell triples that have at least one collinear C4 lift.
    This uses the 16 R8 equivalence classes.
    Returns the number of 'geometrically constrained' cell triples."""
    n = 2 * m
    lifts = []
    for (x, y) in cells:
        lifts.append([c4(x, y, r, n) for r in range(4)])
    
    # 16 R8 rotation patterns
    r8_patterns = [
        (0,1,0),(0,1,1),(0,1,2),(0,1,3),
        (0,2,0),(0,2,1),(0,2,2),(0,2,3),
        (0,3,0),(0,3,1),(0,3,2),(0,3,3),
        (0,0,1),(0,0,2),(0,0,3),(0,0,0),
    ]
    
    viol_triples = 0
    for i in range(m):
        for j in range(i + 1, m):
            for k in range(j + 1, m):
                found = False
                for ri, rj, rk in r8_patterns:
                    pi = lifts[i][ri]
                    pj = lifts[j][rj]
                    pk = lifts[k][rk]
                    if pi == pj or pj == pk or pk == pi:
                        continue
                    det = (pj[0]-pi[0])*(pk[1]-pi[1]) - (pk[0]-pi[0])*(pj[1]-pi[1])
                    if det == 0:
                        found = True
                        break
                if found:
                    viol_triples += 1
    
    return viol_triples

def all_2_cycle_partitions(m):
    """Generate all 2-cycle partitions of m (a+b=m, a>=b>0)."""
    types = []
    for a in range(m//2, m):
        b = m - a
        if b >= 1:
            types.append([a, b])
    return types

def main():
    rng = random.Random(456)
    
    # First: scan ALL 2-cycle partitions with 100 samples each
    two_cycle_types = all_2_cycle_partitions(M)
    
    print(f"=== Deep Cycle-Type Search: ALL 2-Cycle Partitions of {M} ===", flush=True)
    print(f"Testing {len(two_cycle_types)} partition types × 100 samples each", flush=True)
    print("-" * 70, flush=True)
    
    best_overall = float('inf')
    best_type = None
    best_edges = None
    results = []
    
    t_start = time.time()
    for cycle_type in two_cycle_types:
        n_samples = 100
        min_gv = float('inf')
        best_for_type = None
        
        for trial in range(n_samples):
            edges = generate_2factor(M, cycle_type, rng)
            cells = [(u, v) for (u, v) in edges]
            gv = count_geometric_violations(cells, M)
            if gv < min_gv:
                min_gv = gv
                best_for_type = (gv, edges)
                if gv == 0:
                    print(f"\n  *** ZERO VIOLATIONS FOUND! type={cycle_type} ***", flush=True)
                    break
        
        results.append((cycle_type, min_gv))
        
        if min_gv < best_overall:
            best_overall = min_gv
            best_type = cycle_type
            best_edges = best_for_type[1]
        
        # Progress
        elapsed = time.time() - t_start
        if elapsed > 60:  # Show top results every 60s
            top5 = sorted(results, key=lambda x: x[1])[:5]
            print(f"\n  Status: {len(results)}/{len(two_cycle_types)} types checked [{elapsed:.0f}s]", flush=True)
            print(f"  Top 5 so far:", flush=True)
            for ct, gv in top5:
                print(f"    {ct}: min_gv={gv}", flush=True)
    
    total_time = time.time() - t_start
    
    # Sort and display top results
    results.sort(key=lambda x: x[1])
    
    print(f"\n{'='*70}", flush=True)
    print(f"RESULTS: ALL 2-Cycle Types ({total_time:.0f}s)", flush=True)
    print(f"{'Rank':>5s} | {'Partition':>10s} | {'Min GV':>8s} | Est. Viol (GV/5)", flush=True)
    print("-" * 50, flush=True)
    for rank, (ct, gv) in enumerate(results[:10]):
        est_viol = gv / 5
        print(f"{rank+1:5d} | {str(ct):>10s} | {gv:8d} | {est_viol:.1f}", flush=True)
    
    print(f"\nBest overall: {best_type} with {best_overall} geometric violations", flush=True)
    print(f"Estimated minimum violations (GV/5): {best_overall/5:.1f}", flush=True)
    
    # Save the best config
    if best_edges:
        out_path = os.path.join(HERE, "results", f"best_gv_{best_overall}_edges.json")
        with open(out_path, "w") as f:
            json.dump({
                "m": M,
                "edges": best_edges,
                "cycle_type": best_type,
                "geometric_violations": best_overall
            }, f)
        print(f"Saved best config to {out_path}", flush=True)

if __name__ == "__main__":
    main()
