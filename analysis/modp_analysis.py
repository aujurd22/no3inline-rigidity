"""
modp_analysis.py — Direction 1: Modular obstruction analysis for m=37 rot4-NTIL.

For each prime p, compute all X-layer determinants modulo p for a given 2-factor
configuration.  If the count of det ≡ 0 (mod p) has a positive lower bound across
ALL possible orientations of a given 2-factor (or across all 2-factors), that
would constitute a modular obstruction.

Usage:
    python modp_analysis.py [--primes 2,3,5,7,11,13,17,19,23,29,31,37,73]
                            [--trials 20] [--seed 42]
"""
import os, sys, json, random, math, time, itertools
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def det_collinear(p1, p2, p3):
    """3x3 determinant = 0 iff p1,p2,p3 collinear.  Exact integer."""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
    return x1*y2 + x2*y3 + x3*y1 - x1*y3 - x2*y1 - x3*y2

def det_mod(p1, p2, p3, mod):
    """det modulo p."""
    return det_collinear(p1, p2, p3) % mod

def load_edges(path):
    with open(path) as f:
        data = json.load(f)
    return [(e[0], e[1]) for e in data["edges"]]

def cells_from_edges(edges, orientation):
    """Given edges (list of (u,v) with u<=v) and orientation dict:
       orientation[(u,v)] = (x,y) where (x,y) is either (u,v) or (v,u).
       For loops: (x,y) = (u,u)."""
    cells = []
    for u, v in edges:
        if u == v:
            cells.append((u, u))
        else:
            key = (u, v)
            cells.append(orientation[key])
    return cells

def random_orientation(edges, rng):
    orient = {}
    for u, v in edges:
        if u == v:
            orient[(u, v)] = (u, u)
        else:
            if rng.randint(0, 1):
                orient[(u, v)] = (u, v)
            else:
                orient[(u, v)] = (v, u)
    return orient

def all_x_determinants(cells, m):
    """Compute ALL X-layer determinants for the given cells.
    Cells are (x,y) with x,y in [0,m-1].
    Returns list of det values (integers) for all C(37,3)*16 triples."""
    n = 2 * m
    # Precompute lifts for all cells
    lifts = []
    for (x, y) in cells:
        lifts.append([c4(x, y, r, n) for r in range(4)])
    
    dets = []
    n_cells = len(cells)  # should be m
    
    # X-layer: all C(m,3) triples of distinct cells × 16 rotation patterns
    for i in range(n_cells):
        for j in range(i + 1, n_cells):
            for k in range(j + 1, n_cells):
                for ri in range(4):
                    for rj in range(4):
                        for rk in range(4):
                            # Skip trivial patterns
                            d = det_collinear(lifts[i][ri], lifts[j][rj], lifts[k][rk])
                            dets.append(d)
    
    return dets

def compute_mod_statistics(cells, m, primes):
    """Compute X-layer determinant modulo each prime. Return counts of det ≡ 0 mod p per prime."""
    dets = all_x_determinants(cells, m)
    total = len(dets)
    stats = {}
    for p in primes:
        zero_count = sum(1 for d in dets if d % p == 0)
        stats[p] = {"total": total, "zero_mod": zero_count, "frac": zero_count / total}
    return stats

def run_trial(edges, m, primes, rng):
    """Single trial: random orientation, compute mod stats."""
    orient = random_orientation(edges, rng)
    cells = cells_from_edges(edges, orient)
    stats = compute_mod_statistics(cells, m, primes)
    return stats

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--primes", default="2,3,5,7,11,13,17,19,23,29,31,37,73")
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    primes = [int(p) for p in args.primes.split(",")]
    rng = random.Random(args.seed)
    m = 37
    
    # Load config_408 edges
    edges_path = os.path.join(HERE, "results", "config_408_edges.json")
    edges = load_edges(edges_path)
    print(f"Loaded {len(edges)} edges from config_408", flush=True)
    print(f"m={m}, primes={primes}, trials={args.trials}", flush=True)
    
    all_results = []
    trial_zero_counts = {p: [] for p in primes}
    
    for trial in range(args.trials):
        t0 = time.time()
        stats = run_trial(edges, m, primes, rng)
        elapsed = time.time() - t0
        all_results.append(stats)
        
        zero_str = ", ".join(f"p={p}: {stats[p]['zero_mod']:6d} / {stats[p]['total']:8d} = {stats[p]['frac']:.6f}" for p in primes)
        print(f"  trial {trial:3d}: {zero_str}  [{elapsed:.1f}s]", flush=True)
        
        for p in primes:
            trial_zero_counts[p].append(stats[p]['zero_mod'])
    
    # Summary
    print("\n" + "=" * 80)
    print(f"SUMMARY ({args.trials} trials)")
    print("=" * 80)
    for p in primes:
        zeros = trial_zero_counts[p]
        total_dets = all_results[0][p]["total"]
        print(f"  p={p:3d}: det≡0 count min={min(zeros):6d} max={max(zeros):6d} "
              f"mean={sum(zeros)/len(zeros):.1f} / {total_dets:8d} = {sum(zeros)/len(zeros)/total_dets*100:.4f}%")

if __name__ == "__main__":
    main()
