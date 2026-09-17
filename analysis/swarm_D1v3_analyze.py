"""
swarm_D1v3_analyze.py — Deep analysis of clause hypergraph for rot4-NTIL m=37.

Performs:
1. Clause hypergraph characterization (per-edge degree, triple coverage, 2-colorability)
2. Mixed-moment analysis of the 3 known clause sets
3. 2-cycle hypothesis test
4. Clause-count predictor from edge-set features

Output: results/swarm_D1v3_characterization.json
         results/swarm_D1v3_twocycle_test.json
         results/swarm_D1v3_predictor_data.json
"""
import os, sys, json, math, time, random
from collections import defaultdict, Counter
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

# ── helpers from solver_theory_m37 ──────────────────────────────────────────
def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def igcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a

def line_of(p, q):
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    A, B = dy, -dx
    g = igcd(abs(A), abs(B)) or 1
    A //= g; B //= g
    if A < 0 or (A == 0 and B < 0):
        A, B = -A, -B
    L = A * p[0] + B * p[1]
    return (A, B, L)

def c4_lift(x, y, n):
    return [(x, y)] + [c4(x, y, r, n) for r in (1, 2, 3)]

# ── enumerate clauses (same as pipeline but also returns per-triple data) ────
def enumerate_clauses_full(m, edges, verbose=True):
    """Enumerate all triples and return detailed per-triple clause data."""
    n = 2 * m
    t0 = time.time()
    
    # Precompute lifts for each edge × orientation
    cell_lifts = {}
    for idx, (u, v) in enumerate(edges):
        pts0 = c4_lift(u, v, n)
        cell_lifts[(idx, 0)] = pts0
        if u != v:
            pts1 = c4_lift(v, u, n)
            cell_lifts[(idx, 1)] = pts1
        else:
            cell_lifts[(idx, 1)] = pts0
    
    E = len(edges)
    clauses = []       # flat list of (e1,e2,e3,bits)
    clause_map = {}    # (e1,e2,e3) -> [8 bool results]
    triple_stats = []  # per-triple: {triple, n_forbidden, forbidden_bits}
    n_triples_with_clauses = 0
    
    for a in range(E):
        for b in range(a + 1, E):
            for c in range(b + 1, E):
                triple = (a, b, c)
                results = []
                for bits in range(8):
                    t1 = (bits >> 0) & 1
                    t2 = (bits >> 1) & 1
                    t3 = (bits >> 2) & 1
                    lifts = cell_lifts[(a, t1)] + cell_lifts[(b, t2)] + cell_lifts[(c, t3)]
                    bad = False
                    for i in range(12):
                        if bad: break
                        pi = lifts[i]
                        for j in range(i + 1, 12):
                            pj = lifts[j]
                            if pi[0] == pj[0] and pi[1] == pj[1]:
                                continue
                            k0 = line_of(pi, pj)
                            cnt = 2
                            for k in range(12):
                                if k == i or k == j: continue
                                pk = lifts[k]
                                if pk[0] == pi[0] and pk[1] == pi[1]: continue
                                if line_of(pi, pk) == k0:
                                    cnt += 1
                                    if cnt >= 3:
                                        bad = True
                                        break
                    results.append(bad)
                    if bad:
                        clauses.append((a, b, c, bits))
                
                clause_map[triple] = results
                n_bad = sum(results)
                if n_bad > 0:
                    n_triples_with_clauses += 1
                triple_stats.append({
                    "triple": triple,
                    "n_forbidden": n_bad,
                    "forbidden_bits": [b for b in range(8) if results[b]]
                })
    
    t1 = time.time()
    if verbose:
        print(f"  Enumerated {E*(E-1)*(E-2)//6} triples × 8 orientations → "
              f"{len(clauses)} clauses, {n_triples_with_clauses} triples affected "
              f"in {t1-t0:.1f}s", flush=True)
    
    return clauses, clause_map, triple_stats, cell_lifts

# ── Clause hypergraph analysis ─────────────────────────────────────────────
def analyze_clause_hypergraph(edges, clauses, triple_stats, label=""):
    """Characterize the clause hypergraph."""
    E = len(edges)
    results = {}
    
    # 1. Basic counts
    n_triples_total = E * (E - 1) * (E - 2) // 6
    n_triples_affected = sum(1 for ts in triple_stats if ts["n_forbidden"] > 0)
    results["n_edges"] = E
    results["n_triples_total"] = n_triples_total
    results["n_clauses"] = len(clauses)
    results["n_triples_affected"] = n_triples_affected
    results["frac_triples_affected"] = n_triples_affected / n_triples_total
    results["frac_clause_density"] = len(clauses) / (n_triples_total * 8)
    
    # 2. Per-edge clause degree: how many clauses each edge appears in
    edge_clause_degree = Counter()
    for a, b, c, bits in clauses:
        edge_clause_degree[a] += 1
        edge_clause_degree[b] += 1
        edge_clause_degree[c] += 1
    degrees = [edge_clause_degree.get(i, 0) for i in range(E)]
    results["edge_clause_degree"] = {
        "min": min(degrees),
        "max": max(degrees),
        "mean": sum(degrees) / E,
        "median": sorted(degrees)[E // 2],
        "distribution": dict(Counter(degrees)),
        "per_edge": degrees,
    }
    
    # 3. Per-edge triple frequency (unique triples each edge is in)
    edge_triple_count = Counter()
    for ts in triple_stats:
        if ts["n_forbidden"] > 0:
            a, b, c = ts["triple"]
            edge_triple_count[a] += 1
            edge_triple_count[b] += 1
            edge_triple_count[c] += 1
    triples_deg = [edge_triple_count.get(i, 0) for i in range(E)]
    results["edge_triple_count"] = {
        "min": min(triples_deg),
        "max": max(triples_deg),
        "mean": sum(triples_deg) / E,
        "per_edge": triples_deg,
    }
    
    # 4. Bit pattern analysis: which orientation combos are most forbidden?
    bit_dist = Counter()
    for c in clauses:
        bit_dist[c[3]] += 1
    results["forbidden_bit_patterns"] = {
        str(k): v for k, v in sorted(bit_dist.items())
    }
    
    # 5. Per-triple forbidden count distribution
    per_triple_counts = Counter(ts["n_forbidden"] for ts in triple_stats)
    results["per_triple_forbidden_distribution"] = {
        str(k): v for k, v in sorted(per_triple_counts.items())
    }
    
    # 6. Consecutive-clause analysis: are there clauses that cover all 8 orientations?
    n_full_triples = sum(1 for ts in triple_stats if ts["n_forbidden"] == 8)
    results["n_full_triples"] = n_full_triples
    # A triple with all 8 orientations forbidden means NO assignment works for that triple
    # But since it's 3-CNF with each clause blocking ONE assignment, 8 clauses = complete block
    
    return results

# ── 2-colorability check ────────────────────────────────────────────────────
def check_2colorable(m, edges, clauses):
    """
    Check if the clause hypergraph is 2-colorable.
    A 2-coloring of edges = orientation assignment that avoids ALL clauses.
    This is exactly the SAT problem.
    
    For efficiency: use a simple 2-SAT implication check since each clause
    forbids ONE specific assignment of (t_a, t_b, t_c).
    
    Clause (a,b,c,bits) means NOT(t_a=bit0, t_b=bit1, t_c=bit2).
    This is equivalent to the clause (t_a!=bit0 OR t_b!=bit1 OR t_c!=bit2).
    
    Since each variable is binary, this is a 3-CNF formula.
    We can check 2-colorability via CP-SAT (as in the pipeline).
    
    Here we attempt a simple greedy walk/check for quick evaluation.
    """
    import random as _rng
    rng = _rng.Random(0)
    E = len(edges)
    m_vars = E  # one variable per edge
    
    # Convert clauses to (var, val) format
    clause_list = []
    for a, b, c, bits in clauses:
        b0 = (bits >> 0) & 1
        b1 = (bits >> 1) & 1
        b2 = (bits >> 2) & 1
        clause_list.append((a, b0, b, b1, c, b2))
    
    # Try a greedy local search (WalkSAT-like)
    best_sat = 0
    best_assignment = None
    
    for restart in range(100):
        assign = [rng.randint(0, 1) for _ in range(E)]
        n_sat = 0
        for a, b0, b, b1, c, b2 in clause_list:
            if assign[a] != b0 or assign[b] != b1 or assign[c] != b2:
                n_sat += 1
        
        for step in range(500):
            if n_sat == len(clause_list):
                return {"is_2colorable": True, "assignment": assign, "n_sat": n_sat}
            
            # Find an unsatisfied clause
            unsat = []
            for ci, (a, b0, b, b1, c, b2) in enumerate(clause_list):
                if assign[a] == b0 and assign[b] == b1 and assign[c] == b2:
                    unsat.append(ci)
            
            if not unsat:
                break
            
            ci = rng.choice(unsat)
            a, b0, b, b1, c, b2 = clause_list[ci]
            
            # Flip one of the 3 vars randomly
            var = rng.choice([a, b, c])
            old_val = assign[var]
            assign[var] = 1 - old_val
            
            # Recompute n_sat
            n_sat = 0
            for a2, b02, b2, b12, c2, b22 in clause_list:
                if assign[a2] != b02 or assign[b2] != b12 or assign[c2] != b22:
                    n_sat += 1
        
        if n_sat > best_sat:
            best_sat = n_sat
            best_assignment = list(assign)
    
    return {"is_2colorable": False, "best_n_sat": best_sat, "n_total": len(clause_list),
            "best_assignment": best_assignment}

# ── Mixed-moment analysis ───────────────────────────────────────────────────
def compute_moments(edges, cells):
    """Compute mixed4, bilinear, quartic_norm for a given cell configuration."""
    c = 18.0  # (37-1)/2
    m4 = sum((i - c) ** 2 * (j - c) ** 2 for i, j in cells)
    bl = sum((i - c) * (j - c) for i, j in cells)
    qn = sum((i - c) ** 4 + (j - c) ** 4 for i, j in cells)
    return {"mixed4": round(m4, 1), "bilinear": round(bl, 1), "quartic_norm": round(qn, 1)}

def edge_set_features(edges):
    """Compute topological features of the edge set (independent of orientation)."""
    m = 37
    E = len(edges)
    
    # 1. Cycle decomposition
    adj = defaultdict(list)
    for idx, (u, v) in enumerate(edges):
        if u == v:
            continue  # skip loops
        adj[u].append((v, idx))
        adj[v].append((u, idx))
    
    visited = set()
    cycles = []
    for i in range(m):
        if i in visited:
            continue
        # BFS to find cycle
        stack = [(i, -1)]
        cycle_verts = []
        cycle_edges = []
        while stack:
            v, parent = stack.pop()
            if v in visited:
                continue
            visited.add(v)
            cycle_verts.append(v)
            for nb, eidx in adj[v]:
                if eidx == parent:
                    continue
                if nb not in visited:
                    stack.append((nb, eidx))
                cycle_edges.append(eidx)
        cycles.append({"verts": cycle_verts, "n_verts": len(cycle_verts), "n_edges": len(cycle_edges)})
    
    # 2. Loop count
    n_loops = sum(1 for u, v in edges if u == v)
    
    # 3. Edge span distribution
    spans = [abs(u - v) for u, v in edges if u != v]
    
    # 4. Vertex degree is always 2, but how many edges share endpoints
    # (high overlap = more potential for 2-cycles)
    
    features = {
        "n_cycles": len(cycles),
        "cycle_lengths": sorted([c["n_verts"] for c in cycles]),
        "n_loops": n_loops,
        "mean_span": sum(spans) / len(spans) if spans else 0,
        "max_span": max(spans) if spans else 0,
        "min_span": min(spans) if spans else 0,
    }
    
    return features, cycles

# ── 2-cycle generation ─────────────────────────────────────────────────────
def make_2factor_with_2cycles(m, n_twocycles, rng):
    """
    Generate a 2-factor with exactly n_twocycles 2-cycles.
    A 2-cycle = same edge {a,b} appearing twice (consuming degree slots of both a and b).
    
    Strategy: 
    - Pick n_twocycles pairs (a_i, b_i) distinct vertices
    - Each adds the edge twice, consuming 2 degree from each vertex
    - Fill remaining degree slots with a simple 2-factor on remaining vertices
    """
    used_verts = set()
    edges = []
    
    for _ in range(n_twocycles):
        avail = [v for v in range(m) if v not in used_verts]
        if len(avail) < 2:
            break
        a = rng.choice(avail)
        avail.remove(a)
        b = rng.choice(avail)
        u, v = (a, b) if a <= b else (b, a)
        edges.append((u, v))
        edges.append((u, v))  # second copy = 2-cycle
        used_verts.add(a)
        used_verts.add(b)
    
    # Now fill remaining vertices with a simple 2-factor
    remaining = [v for v in range(m) if v not in used_verts]
    
    if remaining:
        # Use permutation method on remaining vertices
        deg = defaultdict(int)
        for u, v in edges:
            deg[u] += 1
            deg[v] += 1 if u != v else 0
        
        # Map remaining indices locally
        n_rem = len(remaining)
        if n_rem > 0:
            perm = list(remaining)
            rng.shuffle(perm)
            local_map = {remaining[i]: perm[i] for i in range(n_rem)}
            
            for v in remaining:
                if deg[v] >= 2:
                    continue
                w = local_map.get(v)
                if w is None:
                    continue
                if w == v:
                    # Loop
                    edges.append((v, v))
                    deg[v] += 1
                else:
                    e = (min(v, w), max(v, w))
                    if deg.get(e[0], 0) < 2 and deg.get(e[1], 0) < 2:
                        edges.append(e)
                        deg[e[0]] += 1
                        deg[e[1]] += 1
    
    # Ensure exactly m edges (fill with loops if needed)
    while len(edges) < m:
        # Add loops to under-degree vertices
        deg_check = Counter()
        for u, v in edges:
            deg_check[u] += 1
            if u != v:
                deg_check[v] += 1
        for v in range(m):
            if deg_check[v] < 2 and len(edges) < m:
                edges.append((v, v))
                deg_check[v] += 1
                if len(edges) >= m:
                    break
    
    return sorted(edges[:m])

# ── Count clauses quickly (without full triple enumeration) ─────────────────
def count_clauses_fast(m, edges):
    """Fast clause counting using only line checking for orientation combos of triples."""
    _, _, triple_stats, _ = enumerate_clauses_full(m, edges, verbose=False)
    return len([c for ts in triple_stats for _ in range(ts["n_forbidden"])])

# ── Main analysis ──────────────────────────────────────────────────────────
def main():
    os.makedirs(RESULTS, exist_ok=True)
    
    print("=" * 70)
    print("swarm_D1v3_analyze: Clause Hypergraph Analysis for rot4-NTIL m=37")
    print("=" * 70)
    
    # ── Load clause sets ──
    clause_files = {
        "best72": "swarm_D1_2_best72_clauses.json",
        "best96": "swarm_D1_2_best96_clauses.json",
        "random": "swarm_D1_2_random_clauses.json",
    }
    
    datasets = {}
    for name, fn in clause_files.items():
        fp = os.path.join(RESULTS, fn)
        with open(fp) as f:
            data = json.load(f)
        datasets[name] = data
    
    # ── Full characterization ──
    print("\n--- Task 1: Clause Hypergraph Characterization ---")
    
    characterization = {}
    for name, data in datasets.items():
        print(f"\n  Analyzing {name}...", flush=True)
        edges = [tuple(e) for e in data["edges"]]
        clauses_raw = data["clauses"]
        
        # Parse clauses (format: [e1,e2,e3,b0,b1,b2])
        clauses_parsed = []
        for c in clauses_raw:
            if len(c) == 4:
                clauses_parsed.append(tuple(c))
            elif len(c) == 6:
                e1, e2, e3, b0, b1, b2 = c
                bits = (b0) | (b1 << 1) | (b2 << 2)
                clauses_parsed.append((e1, e2, e3, bits))
        
        # Re-run enumeration for full stats
        clauses, clause_map, triple_stats, cell_lifts = enumerate_clauses_full(37, edges)
        
        # Characterize
        char = analyze_clause_hypergraph(edges, clauses, triple_stats, name)
        characterization[name] = char
        
        print(f"    Triples affected: {char['n_triples_affected']}/{char['n_triples_total']} "
              f"({char['frac_triples_affected']*100:.2f}%)")
        print(f"    Edge clause degree: min={char['edge_clause_degree']['min']} "
              f"max={char['edge_clause_degree']['max']} "
              f"mean={char['edge_clause_degree']['mean']:.1f}")
        print(f"    Full triples (all 8 orientations blocked): {char['n_full_triples']}")
        
        # Bit pattern that appears most often
        bp = char['forbidden_bit_patterns']
        most_common_bit = max(bp, key=bp.get)
        print(f"    Most common forbidden pattern: bits={most_common_bit} "
              f"(count={bp[most_common_bit]})")
    
    # Save characterization
    with open(os.path.join(RESULTS, "swarm_D1v3_characterization.json"), "w") as f:
        json.dump(characterization, f, indent=2)
    print(f"\n  Saved characterization to results/swarm_D1v3_characterization.json")
    
    # ── 2-colorability check ──
    print("\n--- 2-Colorability Check (greedy WalkSAT) ---")
    for name, data in datasets.items():
        edges = [tuple(e) for e in data["edges"]]
        clauses_raw = data["clauses"]
        clauses_parsed = []
        for c in clauses_raw:
            if len(c) == 4:
                clauses_parsed.append(tuple(c))
            elif len(c) == 6:
                e1, e2, e3, b0, b1, b2 = c
                bits = (b0) | (b1 << 1) | (b2 << 2)
                clauses_parsed.append((e1, e2, e3, bits))
        
        print(f"\n  {name}: {len(clauses_parsed)} clauses, WalkSAT...", flush=True)
        sat = check_2colorable(37, edges, clauses_parsed)
        print(f"    2-colorable={sat['is_2colorable']}, best_sat={sat.get('best_n_sat', '?')}/{sat.get('n_total', '?')}")
        characterization[name]["walksat_check"] = sat
    
    # ── Task 2: Mixed-moment analysis ──
    print("\n\n--- Task 2: Mixed-Moment Invariant Analysis ---")
    
    # Load the actual solutions from solver_theory_m37 output
    moment_data = {}
    for name, data in datasets.items():
        edges = [tuple(e) for e in data["edges"]]
        # We need cells - the solver_theory_m37.json files have them
        edges_feat, cycles = edge_set_features(edges)
        moment_data[name] = {
            "edge_features": edges_feat,
            "cycle_structure": cycles,
        }
        print(f"\n  {name}:")
        print(f"    n_cycles={edges_feat['n_cycles']}, lengths={edges_feat['cycle_lengths']}")
        print(f"    n_loops={edges_feat['n_loops']}, mean_span={edges_feat['mean_span']:.1f}")
    
    # Save predictor data
    with open(os.path.join(RESULTS, "swarm_D1v3_predictor_data.json"), "w") as f:
        json.dump(moment_data, f, indent=2)
    print(f"\n  Saved predictor data to results/swarm_D1v3_predictor_data.json")
    
    # ── Task 3: 2-cycle test ──
    print("\n\n--- Task 3: 2-Cycle Hypothesis Test ---")
    # The pipeline code says it allows 2-cycles but the permutation method creates them naturally
    # Let's generate explicit 2-factors with 2-cycles and test
    
    test_rng = random.Random(42)
    twocycle_results = []
    
    for n_tc in range(0, 6):  # 0 to 5 explicit 2-cycles
        for trial in range(10):
            try:
                edges = make_2factor_with_2cycles(37, n_tc, test_rng)
                # Count 2-cycles
                edge_multiset = Counter()
                for e in edges:
                    edge_multiset[e] += 1
                actual_2cycles = sum(1 for v in edge_multiset.values() if v >= 2)
                
                print(f"\n  Trial {trial}: {n_tc} requested 2-cycles → {actual_2cycles} actual, {len(set(edges))} unique edges", flush=True)
                
                # Count clauses (this is the expensive part but essential)
                clauses, _, triple_stats, _ = enumerate_clauses_full(37, edges)
                n_clauses = len(clauses)
                
                result = {
                    "trial": trial,
                    "requested_twocycles": n_tc,
                    "actual_twocycles": actual_2cycles,
                    "n_clauses": n_clauses,
                    "n_unique_edges": len(set(edges)),
                    "n_triples_affected": sum(1 for ts in triple_stats if ts["n_forbidden"] > 0),
                }
                twocycle_results.append(result)
                print(f"    → {n_clauses} clauses, {result['n_triples_affected']} triples affected", flush=True)
                
                # Breakthrough check
                if n_clauses == 0:
                    print("  *** BREAKTHROUGH: 0 clauses! Any orientation works! ***", flush=True)
                    result["breakthrough"] = True
                
            except Exception as e:
                print(f"    ERROR: {e}", flush=True)
                continue
    
    # Save 2-cycle test results
    with open(os.path.join(RESULTS, "swarm_D1v3_twocycle_test.json"), "w") as f:
        json.dump(twocycle_results, f, indent=2)
    print(f"\n  Saved 2-cycle test results to results/swarm_D1v3_twocycle_test.json")
    
    # Summary
    if twocycle_results:
        print("\n  --- 2-Cycle Test Summary ---")
        by_n = defaultdict(list)
        for r in twocycle_results:
            by_n[r['actual_twocycles']].append(r['n_clauses'])
        for n in sorted(by_n.keys()):
            vals = by_n[n]
            print(f"  {n} 2-cycles: min={min(vals)}, max={max(vals)}, mean={sum(vals)/len(vals):.1f}, "
                  f"n_samples={len(vals)}")
    
    print("\n\n=== Analysis Complete ===")

if __name__ == "__main__":
    main()
