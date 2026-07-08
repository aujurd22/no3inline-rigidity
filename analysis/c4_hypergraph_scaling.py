#!/usr/bin/env python3
"""
C4-domain hypergraph density scaling analysis.

Key question: as N grows, how does the 3-uniform hypergraph density
on C4 domain cells scale?

Hypothesis: The C4 CSP is hard because:
1. Pairwise conflict graph is sparse (density ∝ 1/N)
2. But 3-uniform hypergraph density grows as N²
3. The C4 solution count ∝ N! · (1 - h(N))^C(N²,3) 
   where h(N) is hyperedge density → super-exponential drop
"""

import os, math, json, random, itertools
from collections import defaultdict

OUT_DIR = r'D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3line-publish\analysis'


def collinear(p1, p2, p3):
    (x1,y1),(x2,y2),(x3,y3) = p1, p2, p3
    return (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1)


def c4_images(r, c, N):
    n = 2 * N
    return [(r, c), (c, n-1-r), (n-1-r, n-1-c), (n-1-c, r)]


def compute_hypergraph_density(N, sample_size=50000):
    """Estimate 3-uniform hypergraph density by sampling triples.
    
    Randomly sample triples of domain cells and check if any
    choice of 1 image from each of the 3 cells is collinear.
    """
    n = 2 * N
    total_cells = N * N
    
    # Precompute images
    images = {}
    for r in range(N):
        for c in range(N):
            images[(r,c)] = c4_images(r, c, N)
    
    cells = list(images.keys())
    
    # Sample triples
    random.seed(20260709 + N)
    hyperedges = 0
    checked = 0
    
    for _ in range(sample_size):
        i, j, k = random.sample(range(total_cells), 3)
        checked += 1
        
        imgs1 = images[cells[i]]
        imgs2 = images[cells[j]]
        imgs3 = images[cells[k]]
        
        has_hyperedge = False
        # Check all 4×4×4 = 64 choices
        for a in range(4):
            if has_hyperedge: break
            for b in range(4):
                if has_hyperedge: break
                for c in range(4):
                    if collinear(imgs1[a], imgs2[b], imgs3[c]):
                        has_hyperedge = True
                        break
        
        if has_hyperedge:
            hyperedges += 1
    
    density = hyperedges / checked
    total_triples = total_cells * (total_cells - 1) * (total_cells - 2) // 6
    
    return {
        'N': N,
        'total_cells': total_cells,
        'total_triples': total_triples,
        'sampled': checked,
        'hyperedges_found': hyperedges,
        'edge_density': density,
        'est_total_hyperedges': int(density * total_triples),
    }


def scaling_analysis():
    """Analyze hypergraph density scaling and connect to C4 solvability."""
    results = []
    
    print(f"\n{'='*65}")
    print(f"C4 Domain Hypergraph Density Scaling")
    print(f"{'='*65}")
    print(f"{'n':>4} {'N':>4} {'cells':>6} {'sampled':>8} {'edges':>8} {'density':>10}")
    print("-" * 50)
    
    for n in range(12, 60, 2):
        N = n // 2
        res = compute_hypergraph_density(N, sample_size=20000)
        results.append(res)
        
        print(f"{n:>4} {N:>4} {res['total_cells']:>6} {res['sampled']:>8} "
              f"{res['hyperedges_found']:>6}  {res['edge_density']:>9.5f}")
    
    # Fit density as function of N
    Ns = [r['N'] for r in results]
    dens = [r['edge_density'] for r in results]
    
    # log(density) ~ a + b*log(N)
    import math
    logNs = [math.log(N) for N in Ns]
    logdens = [math.log(max(d, 1e-10)) for d in dens]
    
    mean_ln = sum(logNs) / len(logNs)
    mean_ld = sum(logdens) / len(logdens)
    
    num = sum((ln - mean_ln) * (ld - mean_ld) for ln, ld in zip(logNs, logdens))
    den = sum((ln - mean_ln)**2 for ln in logNs)
    
    b = num / den
    a = mean_ld - b * mean_ln
    
    print(f"\n  density(N) ∝ N^{b:.3f}")
    print(f"  (log-log fit: log(density) = {a:.2f} + {b:.3f} × log(N))")
    
    # Extrapolate to n=76
    N76 = 38
    dens76 = math.exp(a + b * math.log(N76))
    total_triples_76 = (N76*N76) * (N76*N76-1) * (N76*N76-2) // 6
    est_edges_76 = int(dens76 * total_triples_76)
    
    # Also compute: expected hyperedges per C4 solution (N cells)
    # Expected hyperedges = C(N,3) × density
    N_sol = N76
    expected_hyperedges_sol = math.comb(N_sol, 3) * dens76
    
    print(f"\n=== n=76 (N=38) Extrapolation ===")
    print(f"  Estimated hyperedge density: {dens76:.6e}")
    print(f"  Total domain triples: {total_triples_76:,}")
    print(f"  Estimated total hyperedges: {est_edges_76:,}")
    print(f"  Expected hyperedges in a C4 solution (C({N_sol},3) × density): {expected_hyperedges_sol:.2f}")
    print(f"\n  Interpretation:")
    if expected_hyperedges_sol > 1:
        print(f"    A random selection of {N_sol} cells (one per row) is expected to")
        print(f"    contain {expected_hyperedges_sol:.1f} collinear triples (hyperedge violations).")
        print(f"    → n=76 C4 solutions would need to AVOID all of these.")
        print(f"    → Feasibility depends on the hypergraph's 'avoidance' structure.")
    else:
        print(f"    A random selection of {N_sol} cells has <1 expected hyperedge.")
        print(f"    → Hypergraph is sparse enough that MANY independent sets exist.")
    
    # Save results
    path = os.path.join(OUT_DIR, 'c4_hypergraph_scaling.json')
    with open(path, 'w') as f:
        json.dump({
            'results': results,
            'fit': {'a': a, 'b': b, 'log_density_regression': f'log(dens) = {a:.2f} + {b:.3f}×log(N)'},
            'extrapolation_n76': {
                'N': 38,
                'density': dens76,
                'expected_hyperedges_in_solution': expected_hyperedges_sol,
            }
        }, f, indent=2)
    print(f"\n  Results saved to {path}")


def saturation_analysis():
    """Analyze the 'saturation' of the C4 hypergraph.
    
    For a given N, what fraction of domain cell triples are hyperedges?
    This tells us how much 'constraint pressure' exists.
    
    Key metric: typical number of collinear triples per N-cell set.
    """
    print(f"\n\n{'='*65}")
    print(f"C4 Constraint Saturation Analysis")
    print(f"{'='*65}")
    
    # From the hypergraph density data, compute expected violations
    # for a random N-cell selection (one per row)
    
    results = compute_hypergraph_density(14)  # n=28
    N = 14
    
    # A C4 solution selects 14 cells, one per domain row
    # Number of triples: C(14,3) = 364
    # Expected hyperedges: 364 × density
    
    print(f"n=28 (N=14):")
    print(f"  C4 hypergraph density: {results['edge_density']:.5f}")
    print(f"  Triples per solution: C({N},3) = {math.comb(N,3)}")
    print(f"  Expected violations per solution: {results['edge_density'] * math.comb(N,3):.2f}")
    print(f"  Actual solutions: 58")
    print(f"  → All 58 solutions avoid {results['edge_density'] * math.comb(N,3):.1f} expected violations")
    
    # For n=56 (N=28)
    res56 = compute_hypergraph_density(28)
    print(f"\nn=56 (N=28):")
    print(f"  C4 hypergraph density: {res56['edge_density']:.5f}")
    print(f"  Triples per solution: C({28},3) = {math.comb(28,3)}")
    print(f"  Expected violations per solution: {res56['edge_density'] * math.comb(28,3):.2f}")
    print(f"  Actual solutions: 10,441")
    
    # For n=76 (N=38)
    dens76 = results['edge_density'] * (38/14) ** -0.5  # Rough extrapolation
    # Actually use the fit
    import math
    # density ∝ N^{-0.5} roughly from previous fit
    N76 = 38
    N28 = 28
    # Approximate from n=28 data
    exp_viol_28 = res56['edge_density'] * math.comb(28, 3)
    
    # Fit density~N^b from earlier
    # Let me just use the scaling
    print(f"\nn=76 (N=38):")
    print(f"  Triples per solution: C(38,3) = {math.comb(38,3):,}")
    print(f"  If density ∝ N^(-0.5): expected violations ≈ {exp_viol_28 * (38/28)**(3-0.5):.1f}")
    # This accounts for C(N,3) ~ N³ and density ~ N^(-0.5), so total ~ N^(2.5)


if __name__ == '__main__':
    scaling_analysis()
    saturation_analysis()
