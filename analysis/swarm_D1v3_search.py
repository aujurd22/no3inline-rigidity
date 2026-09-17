"""
swarm_D1v3_search.py — Deep analysis of best72/best96 2-factors + targeted
search for better 2-factors. Key findings from D1v3:
- 2-cycles DON'T help (increase clause count from 470 to 600+)
- best72 is remarkably better than random (470 vs ~1800 avg clauses)
- What makes best72 special?

Strategy:
1. Analyze cycle structure, edge spans, and vertex adjacency of best72/best96
2. Search for 2-factors with similar properties (certain cycle lengths, edge spans)
3. Use targeted mutations: swap edges while preserving cycle structure

Output: results/swarm_D1v3_search_results.json
        results/swarm_D1v3_analysis.md
"""
import os, sys, json, time, math, random
from collections import defaultdict, Counter
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)

# ── load fast enumeration ──
sys.path.insert(0, HERE)
import swarm_D1v3_twocycle_test as T

# ── 2-factor analysis ──────────────────────────────────────────────────────
def analyze_2factor(edges, label=""):
    """Comprehensive analysis of a 2-factor's structure."""
    m = 37
    E = len(edges)
    
    # 1. Adjacency
    adj = defaultdict(list)
    for idx, (u, v) in enumerate(edges):
        if u == v:
            adj[u].append((u, idx))  # loop
        else:
            adj[u].append((v, idx))
            adj[v].append((u, idx))
    
    # 2. Cycle decomposition
    visited = set()
    cycles = []
    for start in range(m):
        if start in visited:
            continue
        # Walk the cycle
        cycle_verts = [start]
        visited.add(start)
        cur = start
        prev = -1
        while True:
            nbs = [(nb, eidx) for nb, eidx in adj[cur] if nb != prev]
            if not nbs:
                # Handle loops
                for nb, eidx in adj[cur]:
                    if nb == cur:
                        # loop edge
                        pass
                break
            nxt, eidx = nbs[0]
            if nxt == start and len(cycle_verts) > 2:
                break
            if nxt in visited:
                break
            visited.add(nxt)
            cycle_verts.append(nxt)
            prev = cur
            cur = nxt
            if len(cycle_verts) > m:
                break
        cycles.append(cycle_verts)
    
    # Better cycle detection: use edge-based traversal
    visited_edges = set()
    edge_to_verts = defaultdict(set)
    for idx, (u, v) in enumerate(edges):
        edge_to_verts[idx].add(u)
        edge_to_verts[idx].add(v)
    
    # Build graph: vertices = edges, edges connect if share a vertex
    edge_adj = defaultdict(set)
    for idx1, (u1, v1) in enumerate(edges):
        for idx2, (u2, v2) in enumerate(edges):
            if idx1 >= idx2:
                continue
            if len({u1, v1} & {u2, v2}) > 0:
                edge_adj[idx1].add(idx2)
                edge_adj[idx2].add(idx1)
    
    # Find cycles in edge adjacency graph
    visited_e = set()
    edge_cycles = []
    for start in range(E):
        if start in visited_e:
            continue
        # BFS
        comp = set()
        stack = [start]
        while stack:
            e = stack.pop()
            if e in visited_e:
                continue
            visited_e.add(e)
            comp.add(e)
            for nb in edge_adj[e]:
                if nb not in visited_e:
                    stack.append(nb)
        edge_cycles.append(comp)
    
    # 3. Loop count
    n_loops = sum(1 for u, v in edges if u == v)
    
    # 4. Edge spans
    spans = [abs(u - v) for u, v in edges if u != v]
    
    # 5. Duplicate edges (2-cycles)
    edge_counts = Counter(edges)
    n_2cycles = sum(1 for v in edge_counts.values() if v >= 2)
    
    # 6. Degree distribution (should all be 2)
    deg = Counter()
    for u, v in edges:
        deg[u] += 1
        if u != v:
            deg[v] += 1
    
    # 7. Vertex span histogram
    span_hist = Counter(spans)
    
    # 8. Adjacency structure: how many vertices are connected to each vertex
    vert_adj = defaultdict(set)
    for u, v in edges:
        if u != v:
            vert_adj[u].add(v)
            vert_adj[v].add(u)
    
    return {
        "label": label,
        "n_edges": E,
        "n_loops": n_loops,
        "n_2cycles": n_2cycles,
        "n_cycle_components": len(edge_cycles),
        "cycle_component_sizes": sorted([len(c) for c in edge_cycles], reverse=True),
        "edge_spans": {
            "min": min(spans) if spans else 0,
            "max": max(spans) if spans else 0,
            "mean": sum(spans) / len(spans) if spans else 0,
            "hist": {str(k): v for k, v in sorted(span_hist.items())},
        },
        "vertex_degrees": dict(deg),
        "edges": [list(e) for e in edges],
    }

# ── Edge-span-preserving mutation ─────────────────────────────────────────-
def mutate_2factor(edges, rng, swap_frac=0.3):
    """
    Mutate a 2-factor by swapping edge connections while preserving 
    degree-2 constraint.
    
    Strategy: pick 2 edges {a,b}, {c,d}, replace with {a,c}, {b,d}
    (standard 2-switch). Reject if creates duplicate or 2-cycle.
    """
    E = len(edges)
    edge_set = set(edges)
    
    # Try swaps
    n_swaps = max(1, int(E * swap_frac))
    new_edges = list(edges)
    
    for _ in range(n_swaps * 5):  # extra attempts
        if len(new_edges) < 2:
            break
        i = rng.randrange(len(new_edges))
        j = rng.randrange(len(new_edges))
        if i == j:
            continue
        
        a, b = new_edges[i]
        c, d = new_edges[j]
        
        if len({a, b, c, d}) < 4:
            continue
        
        # Try rewiring
        for (x1, y1), (x2, y2) in [((a, c), (b, d)), ((a, d), (b, c))]:
            e1 = (min(x1, y1), max(x1, y1))
            e2 = (min(x2, y2), max(x2, y2))
            
            if e1 == e2:
                continue
            
            other = set(new_edges)
            other.discard(new_edges[i])
            other.discard(new_edges[j])
            
            if e1 in other or e2 in other:
                continue
            
            # Apply mutation
            new_edges[i] = e1
            new_edges[j] = e2
            break
        else:
            continue
        break
    
    return sorted(new_edges)

# ── Target search: try to beat 470 ─────────────────────────────────────────
def search_better_2factor(n_trials=200, seed=42):
    """Search for 2-factors with < 470 clauses using guided generation."""
    
    rng = random.Random(seed)
    
    print("=" * 70)
    print("swarm_D1v3_search: Systematic Search for Low-Clause 2-Factors")
    print("=" * 70)
    
    # Load known best
    with open(os.path.join(RESULTS, "swarm_D1_2_best72_clauses.json")) as f:
        d72 = json.load(f)
    best72_edges = [tuple(e) for e in d72["edges"]]
    
    with open(os.path.join(RESULTS, "swarm_D1_2_best96_clauses.json")) as f:
        d96 = json.load(f)
    best96_edges = [tuple(e) for e in d96["edges"]]
    
    print(f"\nKnown baselines:")
    print(f"  best72: 470 clauses (min_violations=18)")
    print(f"  best96: 538 clauses (min_violations=24)")
    
    # Analyze best72 structure
    a72 = analyze_2factor(best72_edges, "best72")
    a96 = analyze_2factor(best96_edges, "best96")
    
    print(f"\nbest72 analysis:")
    print(f"  cycles: {a72['cycle_component_sizes']}")
    print(f"  loops: {a72['n_loops']}")
    print(f"  edge spans: min={a72['edge_spans']['min']} max={a72['edge_spans']['max']} "
          f"mean={a72['edge_spans']['mean']:.1f}")
    print(f"  span hist: {dict(sorted(Counter(a72['edge_spans']['hist']).most_common(10)))}")
    
    print(f"\nbest96 analysis:")
    print(f"  cycles: {a96['cycle_component_sizes']}")
    print(f"  loops: {a96['n_loops']}")
    print(f"  edge spans: min={a96['edge_spans']['min']} max={a96['edge_spans']['max']} "
          f"mean={a96['edge_spans']['mean']:.1f}")
    
    # Save analysis
    with open(os.path.join(RESULTS, "swarm_D1v3_2factor_analysis.json"), "w") as f:
        json.dump({"best72": a72, "best96": a96}, f, indent=2)
    
    all_attempts = []
    best_clauses = 470
    best_edges = best72_edges
    
    # ── Search 1: Mutations of best72 ──
    print(f"\n--- Search 1: Mutations of best72 ({n_trials//2} trials) ---")
    for trial in range(n_trials // 2):
        parent = best72_edges if rng.random() < 0.5 else best96_edges
        mutated = mutate_2factor(parent, rng, swap_frac=rng.uniform(0.1, 0.5))
        
        # Fast skip: if too many duplicates or 2-cycles, skip
        n2, _ = T.count_2cycles(mutated)
        if n2 > 0:
            continue  # skip 2-cycles (they hurt)
        
        result = T.enumerate_clauses_fast(37, mutated)
        n_clauses = result["n_clauses"]
        
        all_attempts.append({
            "trial": trial, "n_clauses": n_clauses, 
            "generator": f"mutate_{'best72' if rng.random() < 0.5 else 'best96'}",
            "n_2cycles": n2, "time_s": result["time_s"],
        })
        
        if (trial + 1) % 20 == 0:
            print(f"  trial {trial+1}: best so far = {best_clauses}", flush=True)
        
        if n_clauses < best_clauses:
            best_clauses = n_clauses
            best_edges = mutated
            print(f"  ** NEW BEST: {best_clauses} clauses (trial {trial}) **", flush=True)
        
        if n_clauses == 0:
            print("  *** BREAKTHROUGH: 0 CLAUSES! ***")
            break
    
    # ── Search 2: Permutation-based with specific cycle structure ──
    print(f"\n--- Search 2: Cycle-structured 2-factors ({n_trials//4} trials) ---")
    for trial in range(n_trials // 4):
        # Generate 2-factor with specific cycle structure matching best72
        # best72 has ~18 cycle components (very fragmented)
        
        # Try generating a 2-factor with many small cycles
        # Method: divide 37 vertices into groups, form cycles within groups
        n_groups = rng.randint(15, 25)
        groups = [[] for _ in range(n_groups)]
        verts = list(range(37))
        rng.shuffle(verts)
        
        for i, v in enumerate(verts):
            groups[i % n_groups].append(v)
        
        # Filter to groups that can form cycles (size >= 3)
        cycle_groups = [g for g in groups if len(g) >= 3]
        
        edges = []
        for g in cycle_groups:
            for k in range(len(g)):
                a, b = g[k], g[(k + 1) % len(g)]
                edges.append((min(a, b), max(a, b)))
            if len(edges) >= 37:
                break
        
        # Pad with loops if needed
        used = set()
        for u, v in edges:
            used.add(u)
            used.add(v)
        for v in range(37):
            if v not in used and len(edges) < 37:
                edges.append((v, v))
        
        edges = sorted(edges[:37])
        
        n2, _ = T.count_2cycles(edges)
        if n2 > 0:
            continue
        
        result = T.enumerate_clauses_fast(37, edges)
        n_clauses = result["n_clauses"]
        
        all_attempts.append({
            "trial": trial, "n_clauses": n_clauses,
            "generator": "cycle_structured", "n_2cycles": n2,
            "n_groups": n_groups, "time_s": result["time_s"],
        })
        
        if n_clauses < best_clauses:
            best_clauses = n_clauses
            best_edges = edges
            print(f"  ** NEW BEST: {best_clauses} clauses (trial {trial}, groups={n_groups}) **", flush=True)
        
        if n_clauses == 0:
            print("  *** BREAKTHROUGH: 0 CLAUSES! ***")
            break
    
    # ── Search 3: Span-constrained 2-factors ──
    print(f"\n--- Search 3: Span-constrained 2-factors ({n_trials//4} trials) ---")
    # best72's edge spans: mean ~11, range 2-20
    # Generate edges with similar span distribution
    target_spans = [abs(u - v) for u, v in best72_edges if u != v]
    span_dist = Counter(target_spans)
    span_pool = list(span_dist.elements())  # list of spans matching best72
    
    for trial in range(n_trials // 4):
        # Generate random 2-factor, but bias toward best72-like spans
        perm = list(range(37))
        rng.shuffle(perm)
        
        # Use the permutation but filter/reroll edges with bad spans
        visited = [False] * 37
        edges = []
        for i in range(37):
            if visited[i]:
                continue
            # Build a cycle from the permutation
            cycle = []
            j = i
            while not visited[j]:
                visited[j] = True
                cycle.append(j)
                j = perm[j]
            
            for k in range(len(cycle)):
                a, b = cycle[k], cycle[(k + 1) % len(cycle)]
                span = abs(a - b)
                # Accept with probability proportional to best72 span distribution
                if span in span_dist:
                    prob = span_dist[span] / max(span_dist.values())
                else:
                    prob = 0.1
                
                if rng.random() < prob or len(edges) < 37:
                    edges.append((min(a, b), max(a, b)))
        
        edges = sorted(edges[:37])
        n2, _ = T.count_2cycles(edges)
        if n2 > 0:
            continue
        
        result = T.enumerate_clauses_fast(37, edges)
        n_clauses = result["n_clauses"]
        
        all_attempts.append({
            "trial": trial, "n_clauses": n_clauses,
            "generator": "span_constrained", "n_2cycles": n2, "time_s": result["time_s"],
        })
        
        if n_clauses < best_clauses:
            best_clauses = n_clauses
            best_edges = edges
            print(f"  ** NEW BEST: {best_clauses} clauses (trial {trial}) **", flush=True)
        
        if n_clauses == 0:
            print("  *** BREAKTHROUGH: 0 CLAUSES! ***")
            break
    
    # ── Results ──
    print("\n" + "=" * 70)
    print("SEARCH RESULTS")
    print("=" * 70)
    print(f"  Overall best: {best_clauses} clauses")
    print(f"  Best known before: 470 (best72)")
    
    by_gen = defaultdict(list)
    for a in all_attempts:
        by_gen[a["generator"]].append(a["n_clauses"])
    
    print("\n  By generator:")
    for gen, vals in sorted(by_gen.items()):
        print(f"    {gen}: min={min(vals)} max={max(vals)} mean={sum(vals)/len(vals):.1f} n={len(vals)}")
    
    if best_clauses < 470:
        print(f"\n  *** IMPROVEMENT! Found 2-factor with {best_clauses} clauses ***")
        print(f"  Edges: {best_edges}")
        
        # Run full SAT check on the best
        print("\n  Running full SAT check on best candidate...")
        # Use the pipeline's SAT check
        try:
            sys.path.insert(0, HERE)
            from solver_2factor_sat_pipeline import enumerate_clauses, check_sat
            clauses_full, _ = enumerate_clauses(37, best_edges, verbose=False)
            sat_result = check_sat(37, best_edges, clauses_full, time_limit=120, verbose=True)
            print(f"  SAT result: {json.dumps(sat_result, indent=2)}")
        except Exception as e:
            print(f"  SAT check error: {e}")
    else:
        print(f"\n  No improvement found. Best remains 470.")
    
    # Save results
    for a in all_attempts:
        if "edges" not in a:
            pass  # edges not stored for all (memory)
    
    output = {
        "best_clauses": best_clauses,
        "best_overall_edges": [list(e) for e in best_edges] if best_edges else None,
        "n_total_trials": len(all_attempts),
        "attempts": all_attempts,
    }
    
    with open(os.path.join(RESULTS, "swarm_D1v3_search_results.json"), "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSaved to results/swarm_D1v3_search_results.json")
    print("\n=== Done ===")

if __name__ == "__main__":
    search_better_2factor(n_trials=400, seed=20260715)
