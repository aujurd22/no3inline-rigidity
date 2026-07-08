#!/usr/bin/env python3
"""
C4 conflict graph analysis: measure how the domain-cell conflict 
graph density changes with n.

Key idea: C4 domain cells are vertices. Two cells are "conflicting" if 
there's a collinear triple involving their combined 8 images + any third cell.
High conflict density → few solutions.
"""

import os, math, json
from collections import defaultdict

CACHE = r'D:\djr82\Documents\workbuddy\2026-07-03-16-29-36\no3line-publish\analysis\flammenkamp_cache'
ALPH = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+|-/~^_:;,.|'
VAL = {c: i for i, c in enumerate(ALPH)}


def dir_of(pt, n):
    a = 2*pt[0] - (n-1); b = 2*pt[1] - (n-1)
    g = math.gcd(a,b) or 1; a //= g; b //= g
    if a < 0 or (a == 0 and b < 0): a, b = -a, -b
    if a == 0: b = 1
    if b == 0: a = 1
    return (a, b)


def c4_images(r, c, N):
    """Return all 4 full-grid images of C4 domain cell (r,c)."""
    n = 2 * N
    pts = [
        (r, c),
        (c, n - 1 - r),
        (n - 1 - r, n - 1 - c),
        (n - 1 - c, r)
    ]
    return pts


def collinear(p1, p2, p3):
    (x1,y1),(x2,y2),(x3,y3) = p1, p2, p3
    return (x2-x1)*(y3-y1) == (x3-x1)*(y2-y1)


def compute_conflict_graph_fast(N):
    """Fast conflict graph computation.
    
    Two domain cells conflict if any triple among their 8 combined images
    is collinear AND at least 2 images come from different cells.
    
    Optimization: only check triples where 2 images from cell A and 1 from cell B.
    """
    n = 2 * N
    total_cells = N * N
    conflicts = 0
    total_pairs = 0
    
    # Precompute all 4 images for each domain cell
    cell_images = {}
    for r in range(N):
        for c in range(N):
            cell_images[(r,c)] = c4_images(r, c, N)
    
    # For each pair of cells, check if they're compatible
    # Use sampling for large N
    if N > 16:
        # Sample a fraction of pairs
        sample_rate = 1600 / (N * N)  # ~1600 pairs per N
        sample_rate = min(1.0, max(0.05, sample_rate))
    else:
        sample_rate = 1.0
    
    import random
    random.seed(20260709)
    
    cells = list(cell_images.keys())
    sampled_pairs = 0
    
    for i in range(len(cells)):
        for j in range(i+1, len(cells)):
            if random.random() > sample_rate:
                continue
            sampled_pairs += 1
            
            r1, c1 = cells[i]
            r2, c2 = cells[j]
            imgs1 = cell_images[(r1,c1)]
            imgs2 = cell_images[(r2,c2)]
            
            # Check all triples with 2 from cell1, 1 from cell2
            conflict = False
            for a in range(4):
                for b in range(a+1, 4):
                    for k in range(4):
                        p1, p2, p3 = imgs1[a], imgs1[b], imgs2[k]
                        if collinear(p1, p2, p3):
                            conflict = True
                            break
                    if conflict: break
                if conflict: break
            
            if not conflict:
                # Check all triples with 1 from cell1, 2 from cell2
                for a in range(4):
                    for b in range(a+1, 4):
                        for k in range(4):
                            p1, p2, p3 = imgs1[k], imgs2[a], imgs2[b]
                            if collinear(p1, p2, p3):
                                conflict = True
                                break
                        if conflict: break
                    if conflict: break
            
            if conflict:
                conflicts += 1
    
    total_pairs_sampled = sampled_pairs
    est_conflict_density = conflicts / sampled_pairs if sampled_pairs > 0 else 0
    est_total_conflicts = int(est_conflict_density * total_cells * (total_cells - 1) / 2)
    
    return {
        'N': N,
        'total_cells': total_cells,
        'total_pairs': total_cells * (total_cells - 1) // 2,
        'pairs_sampled': sampled_pairs,
        'conflicts_found': conflicts,
        'conflict_density': est_conflict_density,
        'est_total_conflicts': est_total_conflicts,
    }


def conflict_vs_n():
    """Measure conflict density as function of N/n."""
    print(f"\n{'='*60}")
    print(f"C4 Domain Cell Conflict Graph Analysis")
    print(f"{'='*60}")
    print(f"{'n':>4} {'N':>4} {'cells':>6} {'sampled':>8} {'conflict':>9} {'density':>8}")
    print("-" * 50)
    
    for n in range(10, 60, 2):
        N = n // 2
        res = compute_conflict_graph_fast(N)
        
        print(f"{n:>4} {N:>4} {res['total_cells']:>6} {res['pairs_sampled']:>8} "
              f"{res['conflicts_found']:>7}  {res['conflict_density']:>7.4f}")


def permutation_space_analysis():
    """Analyze the permutation constraint: how many of N! permutations
    satisfy the C4 collinearity constraint?"""
    print(f"\n{'='*60}")
    print(f"Permutation Space Analysis")
    print(f"{'='*60}")
    
    # From data: column degree always = 2, so row selection is a permutation
    
    # For each C4 solution, extract the permutation sigma: row r selects column sigma(r)
    # Then analyze what patterns the valid permutations share
    
    for n in [12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56]:
        sols = []
        for ext in ['', '.few']:
            p = os.path.join(CACHE, f'n{n}_rot4{ext}')
            if os.path.exists(p):
                with open(p) as f:
                    for line in f:
                        line = line.rstrip()
                        if not line: continue
                        pre = line[0]
                        body = line[1:] if pre in '.:/-ocx+*' else line
                        if len(body) >= 2*n:
                            pts = []
                            for r in range(n):
                                c1 = VAL.get(body[2*r]); c2 = VAL.get(body[2*r+1])
                                if c1 is None or c2 is None or c1 >= n or c2 >= n:
                                    pts = None; break
                                pts.append((r, c1)); pts.append((r, c2))
                            if pts: sols.append(pts)
        
        if not sols: continue
        
        N = n // 2
        
        # Extract permutation from each solution
        # Domain rows [0,N) each define a permutation entry
        # A domain row r has point (r, sigma(r)), giving permutation sigma(r)
        perms = []
        for pts in sols:
            sigma = {}
            for r, c in pts:
                if r < N and c < N:
                    sigma[r] = c
            if len(sigma) == N:
                perms.append([sigma[i] for i in range(N)])
        
        # Analyze permutation patterns
        # 1. Fixed points: sigma(r) = r
        # 2. 2-cycles: sigma(sigma(r)) = r  
        # 3. Long cycles
        
        fixed_pts = [sum(1 for r in range(N) if p[r] == r) for p in perms]
        avg_fixed = sum(fixed_pts) / len(fixed_pts) if fixed_pts else 0
        
        # Cycle structure: count 2-cycles
        two_cycles = []
        for p in perms:
            seen = set()
            count_2 = 0
            for r in range(N):
                if r in seen: continue
                if p[r] == r:
                    seen.add(r)
                elif p[p[r]] == r and p[r] != r:
                    count_2 += 1
                    seen.add(r); seen.add(p[r])
            two_cycles.append(count_2)
        
        avg_2cyc = sum(two_cycles) / len(two_cycles) if two_cycles else 0
        
        # Number of distinct permutations
        unique_perms = len(set(tuple(p) for p in perms))
        
        print(f"\nn={n:>3} N={N:>3}: {len(perms)} solutions, {unique_perms} unique perms")
        print(f"  avg fixed points: {avg_fixed:.2f} / {N} ({(avg_fixed/N*100 if N else 0):.1f}%)")
        print(f"  avg 2-cycles: {avg_2cyc:.2f} / {N//2}")
        
        # Show sample permutation (first)
        if perms:
            print(f"  sample: {perms[0][:min(16, N)]}{'...' if N > 16 else ''}")


def n76_prediction():
    """Synthesize all findings to predict n=76."""
    print(f"\n{'='*60}")
    print(f"Synthesis: n=76 Prediction")
    print(f"{'='*60}")
    
    # Known data points
    data = {
        12: 4, 14: 13, 16: 13, 18: 7, 20: 16, 
        22: 8, 24: 23, 26: 36, 28: 58, 30: 92,
        32: 101, 34: 172, 36: 281, 38: 337, 40: 541,
        42: 746, 44: 1016, 54: 7696, 56: 10441
    }
    
    # Compute success probability: P(N) = solutions / N!
    import math
    print(f"{'n':>4} {'N':>4} {'solutions':>10} {'log(N!)':>10} {'log(P)':>10} {'P':>12}")
    
    for n in sorted(data.keys()):
        N = n // 2
        sols = data[n]
        logNfact = math.lgamma(N + 1) / math.log(math.e)  # Natural log
        logP = math.log(sols) - logNfact if sols > 0 else -float('inf')
        p_val = math.exp(logP) if logP > -50 else 0
        
        print(f"{n:>4} {N:>4} {sols:>10,} {logNfact:>10.1f} {logP:>10.1f} {p_val:>12.2e}")
    
    # Fit log(P) as function of N
    log_ps = []
    Ns = []
    for n in sorted(data.keys()):
        N = n // 2
        sols = data[n]
        logNfact = math.lgamma(N + 1)
        logP = math.log(sols) - logNfact
        log_ps.append(logP)
        Ns.append(N)
    
    # Linear regression: log(P) ~ a + b*N
    mean_N = sum(Ns) / len(Ns)
    mean_lp = sum(log_ps) / len(log_ps)
    
    num = sum((N - mean_N) * (lp - mean_lp) for N, lp in zip(Ns, log_ps))
    den = sum((N - mean_N)**2 for N in Ns)
    
    b = num / den
    a = mean_lp - b * mean_N
    
    print(f"\n  log(P(N)) = {a:.2f} + {b:.4f} × N")
    print(f"  P(N) = exp({a:.2f}) × exp({b:.4f} × N)")
    
    # Predict for n=76
    N_pred = 38
    logP_pred = a + b * N_pred
    logNfact_pred = math.lgamma(N_pred + 1)
    logSols_pred = logP_pred + logNfact_pred
    sols_pred = math.exp(logSols_pred)
    
    print(f"\n=== n=76 Prediction ===")
    print(f"  N = {N_pred}")
    print(f"  log(P) ≈ {logP_pred:.1f}")
    print(f"  log(N! × P) ≈ {logSols_pred:.1f}")
    print(f"  Predicted solutions: {sols_pred:.2e}")
    
    if sols_pred > 1:
        print(f"  → n=76 likely HAS C4 solutions (predicted {sols_pred:.1f})")
    else:
        print(f"  → n=76 likely has NO C4 solutions")


if __name__ == '__main__':
    conflict_vs_n()
    print()
    permutation_space_analysis()
    print()
    n76_prediction()
