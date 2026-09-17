#!/usr/bin/env python3
"""skewed_generator.py — Generate m=37 2-factors with SKEWED clause distribution
(mimicking the m=36 solution's hot-edge strategy).

Key insight from A5 analysis:
- m=36 solution works because 4 edges carry 40% of clause constraints
- These 4 edges have SPANS {2, 7, 13, 15} — "dangerous" spans
- Remaining 32 edges have "safe" spans with low clause count
- m=37 best72 has min span=4, uniformly distributed

Strategy: Generate Hamiltonian cycles with VERY uneven span distribution.
Include a few short-span edges (1-3) and many long-span edges.
"""

import sys, os, json, time, random, math
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H

M = 37

# Lazy ortools import — for SAT checks, use venv python
def _get_sat_pipeline():
    import solver_2factor_sat_pipeline as P
    return P


def span_of(u, v):
    return min(abs(u - v), M - abs(u - v))


def generate_skewed_cycle(rng, n_short=3, short_spans=None, min_other=8):
    """Generate a Hamiltonian cycle on Z/37Z with deliberately skewed span distribution.
    
    n_short: how many edges have "short" (dangerous) spans
    short_spans: specific spans to use for short edges (e.g., [1,2,3])
    min_other: minimum span for the remaining edges
    
    Returns a list of 37 sorted edges (2-factor).
    """
    if short_spans is None:
        short_spans = [1, 2, 3, 4]
    
    # Try to construct a cycle
    for _ in range(1000):
        vertices = list(range(M))
        rng.shuffle(vertices)
        
        # We'll build the cycle vertex by vertex, controlling edge spans
        edges = []
        used = set()
        
        # Start with a random vertex
        start = rng.randrange(M)
        used.add(start)
        path = [start]
        
        # Place short-span edges at strategic positions
        short_edge_targets = []
        remaining_short = n_short
        for pos in range(1, M):
            if remaining_short > 0:
                # Try to make this edge have a short span
                candidates = []
                for v in range(M):
                    if v not in used:
                        s = span_of(path[-1], v)
                        if s in short_spans:
                            candidates.append((s, v))
                if candidates:
                    candidates.sort()
                    # Pick the shortest span available
                    if rng.random() < 0.7:
                        v = candidates[0][1]  # shortest
                    else:
                        v = rng.choice(candidates)[1]
                    used.add(v)
                    path.append(v)
                    remaining_short -= 1
                    continue
            
            # Normal step: pick any unused vertex
            candidates = [v for v in range(M) if v not in used]
            if not candidates:
                break
            
            # Try to prefer longer spans (safe)
            if rng.random() < 0.6 and min_other > 2:
                candidates = [v for v in candidates if span_of(path[-1], v) >= min_other]
            if not candidates:
                candidates = [v for v in range(M) if v not in used]
            
            v = rng.choice(candidates)
            used.add(v)
            path.append(v)
        
        if len(path) < M:
            continue
        
        # Form edges from the cycle
        edges = []
        for k in range(M):
            a, b = path[k], path[(k + 1) % M]
            edges.append((a, b) if a <= b else (b, a))
        
        # Verify it's a valid 2-factor
        edges = sorted(set(edges))
        if len(edges) == M:
            # Check spans
            spans = [span_of(u, v) for u, v in edges]
            n_small = sum(1 for s in spans if s <= 4)
            if n_small >= n_short:
                return edges
    
    return None  # Failed to construct


def enumerate_clause_participation_by_edge(m, edges):
    """For each edge, count how many clause forbid patterns involving it."""
    n = 2 * m
    
    def c4_lift(x, y):
        pts = [(x, y)]
        for _ in range(3):
            x, y = n - 1 - y, x
            pts.append((x, y))
        return pts
    
    cell_lifts = {}
    for idx, (u, v) in enumerate(edges):
        p0 = c4_lift(u, v)
        cell_lifts[(idx, 0)] = p0
        if u != v:
            p1 = c4_lift(v, u)
            cell_lifts[(idx, 1)] = p1
        else:
            cell_lifts[(idx, 1)] = p0
    
    edge_clause_count = Counter()
    E = len(edges)
    
    for a_idx in range(E):
        for b_idx in range(a_idx + 1, E):
            for c_idx in range(b_idx + 1, E):
                for bits in range(8):
                    t1 = (bits >> 0) & 1
                    t2 = (bits >> 1) & 1
                    t3 = (bits >> 2) & 1
                    
                    all_12 = cell_lifts[(a_idx, t1)] + cell_lifts[(b_idx, t2)] + cell_lifts[(c_idx, t3)]
                    
                    line_counts = {}
                    Pf = _get_sat_pipeline()
                    for i in range(12):
                        pi = all_12[i]
                        for j in range(i + 1, 12):
                            pj = all_12[j]
                            if pi[0] == pj[0] and pi[1] == pj[1]:
                                continue
                            k = Pf.line_of(pi, pj)
                            line_counts[k] = line_counts.get(k, 0) + 1
                    
                    for cnt in line_counts.values():
                        s = (1 + math.isqrt(1 + 8 * cnt)) // 2
                        if s >= 3:
                            edge_clause_count[a_idx] += 1
                            edge_clause_count[b_idx] += 1
                            edge_clause_count[c_idx] += 1
                            break
    
    return edge_clause_count


def test_skewed():
    """Main test: generate skewed cycles and check with SAT pipeline."""
    rng = random.Random(20260716)
    results = []
    best = float('inf')
    best_edges = None
    
    for trial in range(300):
        for n_short in [2, 3, 4, 5]:
            for min_other in [6, 8, 10, 12]:
                edges = generate_skewed_cycle(rng, n_short=n_short, min_other=min_other)
                if edges is None:
                    continue
                
                nc = H.count_clauses_fast(M, edges)
                
                span_min = min(span_of(u,v) for u,v in edges)
                span_mean = sum(span_of(u,v) for u,v in edges) / M
                
                res = {
                    'trial': trial,
                    'n_short': n_short,
                    'min_other': min_other,
                    'n_clauses': nc,
                    'span_min': span_min,
                    'span_mean': round(span_mean, 1),
                }
                results.append(res)
                
                if nc < best:
                    best = nc
                    best_edges = list(edges)
                    # Clause distribution
                    ec = enumerate_clause_participation_by_edge(M, edges)
                    hot = ec.most_common(5)
                    print(f"*** NEW BEST: {nc} clauses (n_short={n_short}, min_other={min_other}) ***", flush=True)
                    print(f"    Span: min={span_min}, mean={span_mean:.1f}", flush=True)
                    print(f"    Top-5 hot edges: {hot}", flush=True)
                    
                    # Run full MaxSAT
                    if nc < 600 and nc > 0:
                        Pf = _get_sat_pipeline()
                        clauses, cmap = Pf.enumerate_clauses(M, best_edges, verbose=False)
                        sat_res = Pf.check_sat(M, best_edges, clauses, time_limit=60, verbose=False)
                        mv = sat_res.get('maxsat_min_violations', -1)
                        print(f"    SAT check: min_violations={mv} -> {4*mv} defects", flush=True)
                        if mv == 0:
                            print("  *** BREAKTHROUGH! ***")
                            return results, best, best_edges, {'found': True, 'edges': best_edges}
                
                if (trial*4 + n_short) % 50 == 0:
                    save(results, best, best_edges, 'results/skewed_sweep.json')
        
        if (trial+1) % 25 == 0:
            print(f"trial {trial+1}/300, best={best}", flush=True)
            save(results, best, best_edges, 'results/skewed_sweep.json')
    
    save(results, best, best_edges, 'results/skewed_sweep.json')
    return results, best, best_edges


def save(results, best, best_edges, path):
    with open(os.path.join(HERE, path), 'w') as f:
        json.dump({
            'best': best,
            'best_edges': best_edges,
            'results': results[:100],
            'n_trials': len(results)
        }, f, indent=2)


if __name__ == '__main__':
    print("Starting skewed 2-factor sweep for m=37...", flush=True)
    t0 = time.time()
    try:
        results, best, best_edges = test_skewed()
        print(f"\nDone. Best: {best} clauses in {time.time()-t0:.0f}s", flush=True)
        if best < 448:
            print(f"*** IMPROVED OVER 448! ***", flush=True)
    except KeyboardInterrupt:
        print("\nInterrupted", flush=True)
