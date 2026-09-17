"""
direction3_cycle_type.py — Direction 3: Cycle-type restricted search for m=37.

Key idea: Different 2-factor cycle structures have different violation counts.
If we can characterize which cycle types are "promising" (low violations),
we can restrict the search to those types and exhaust them.

Already known:
- best72 (Hamiltonian 37-cycle): 18 violations (SDP-proven optimal)
- config_408 (multi-cycle): 16 violations (best known)
- best96 (30+7 cycles): 24 violations (SDP-proven optimal)

Question: Can we find a 2-factor with < 16 violations by targeting specific
cycle decompositions not yet explored?

Approach:
1. Extract cycle structure of config_408 (best known).
2. Generate random 2-factors with SPECIFIC cycle decompositions.
3. For each, compute clause count (proxy for violation potential).
4. Report which cycle types are most promising.

Usage: python direction3_cycle_type.py
"""
import os, sys, json, math, random, time
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))

def load_edges(path):
    with open(path) as f:
        data = json.load(f)
    return [(e[0], e[1]) for e in data["edges"]]

def extract_cycle_structure(edges):
    """Given edges [(u,v),...] of a 2-factor on m=37 vertices,
    decompose into cycles. Returns list of cycle lengths."""
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    
    # Each vertex should have degree 2
    visited = set()
    cycles = []
    
    for start in range(37):
        if start in visited:
            continue
        # Follow the cycle
        cycle = []
        current = start
        prev = -1
        while current not in visited:
            visited.add(current)
            cycle.append(current)
            # Find next vertex (not the one we came from)
            neighbors = adj[current]
            if len(neighbors) != 2:
                # This shouldn't happen for a valid 2-factor
                break
            if neighbors[0] != prev:
                nxt = neighbors[0]
            else:
                nxt = neighbors[1]
            prev = current
            current = nxt
            if current == start:
                break
        cycles.append(len(cycle))
    
    return sorted(cycles)

def generate_2factor_with_cycles(m, cycle_lengths, rng, seed=None):
    """Generate a random 2-factor on m vertices with SPECIFIED cycle lengths.
    cycle_lengths: list of cycle lengths summing to m (e.g. [31, 6]).
    
    This generates a random permutation with the given cycle structure.
    A 2-factor on m vertices IS a permutation on m elements (each vertex
    maps to its successor in its cycle).
    """
    if seed is not None:
        rng = random.Random(seed)
    
    # Create vertex pool
    vertices = list(range(m))
    rng.shuffle(vertices)
    
    # Partition vertices into cycles
    edges = []
    pos = 0
    for clen in cycle_lengths:
        cycle_verts = vertices[pos:pos+clen]
        pos += clen
        for k in range(clen):
            u = cycle_verts[k]
            v = cycle_verts[(k + 1) % clen]
            edges.append(tuple(sorted((u, v))))
    
    edges = sorted(edges)
    
    # Verify 2-regularity
    deg = Counter()
    for u, v in edges:
        deg[u] += 1
        deg[v] += 1
    assert all(d == 2 for d in deg.values()), "Not 2-regular"
    assert len(edges) == m, f"Wrong edge count: {len(edges)} != {m}"
    
    return edges

def count_clauses(edges):
    """
    Approximate clause count for a given 2-factor.
    This counts the number of orientation combos (pairs of triples)
    that could potentially be violated. A lower clause count = fewer
    constraints = potentially fewer violations.
    
    NOTE: The actual clause count depends on specific orientations and
    the R8 constraint system. This approximation counts pairs of cells
    whose C4 lifts share a line with some third cell.
    """
    # For each pair of cells (edges), check if they create potential violations
    # with any third cell. This is a fast approximation.
    m = len(edges)
    n = 2 * m
    clause_estimate = 0
    
    from solver_theory_m37 import c4, line_of
    
    # Build cells with arbitrary orientation (u,v for each edge)
    cells = [(u, v) for (u, v) in edges]
    
    # Create C4 lifts
    lifts = {}
    for idx, (x, y) in enumerate(cells):
        lifts[idx] = [c4(x, y, r, n) for r in range(4)]
    
    # For each triple of distinct cells, count "lines" formed by their lifts
    # that have ≥3 points. Each such line indicates a potential clause.
    clauses = set()
    for i in range(m):
        for j in range(i + 1, m):
            for k in range(j + 1, m):
                # Check all 64 rotation patterns
                for ri in range(4):
                    for rj in range(4):
                        for rk in range(4):
                            pi = lifts[i][ri]
                            pj = lifts[j][rj]
                            pk = lifts[k][rk]
                            # Skip if any two points coincide
                            if pi == pj or pj == pk or pk == pi:
                                continue
                            # Check collinearity using area formula
                            det = (pj[0]-pi[0])*(pk[1]-pi[1]) - (pk[0]-pi[0])*(pj[1]-pi[1])
                            if det == 0:
                                # Collinear! This contributes to clauses.
                                clauses.add((i, j, k, ri, rj, rk))
                                break  # One violation per triple is enough
    
    return len(clauses)

def analyze_best_configs():
    m = 37
    print(f"=== Direction 3: Cycle-Type Analysis (m={m}) ===", flush=True)
    
    # Load config_408 and analyze its cycle structure
    edges_408 = load_edges(os.path.join(HERE, "results", "config_408_edges.json"))
    cycles_408 = extract_cycle_structure(edges_408)
    print(f"\nconfig_408: cycles = {cycles_408}", flush=True)
    print(f"  Cycle type: {dict(Counter(cycles_408))}", flush=True)
    print(f"  Number of cycles: {len(cycles_408)}", flush=True)
    print(f"  Max cycle length: {max(cycles_408)}", flush=True)
    
    # Build a simple Hamiltonian cycle (single 37-cycle)
    ham_edges = [(i, (i+1) % 37) for i in range(37)]
    ham_edges = [tuple(sorted(e)) for e in ham_edges]
    ham_cycles = extract_cycle_structure(ham_edges)
    print(f"\nHamiltonian 37-cycle: cycles = {ham_cycles}", flush=True)
    
    # Search for 2-factors with SPECIFIC cycle types and measure clause counts
    print(f"\nScanning cycle types for clause count proxy...", flush=True)
    
    candidate_cycle_types = [
        [37],                    # Hamiltonian
        [31, 6],                 # 31+6
        [28, 9],                 # 28+9
        [25, 12],                # 25+12
        [22, 15],                # 22+15
        [19, 18],                # 19+18
        [20, 17],                # 20+17
        [16, 15, 6],             # 16+15+6
        [14, 13, 10],            # 14+13+10
        [12, 11, 10, 4],         # 12+11+10+4
        [10, 9, 8, 6, 4],       # 10+9+8+6+4
        [8, 7, 6, 5, 4, 3, 4],  # 8+7+6+5+4+3+4
    ]
    
    rng = random.Random(42)
    
    for cycle_type in candidate_cycle_types:
        if sum(cycle_type) != m:
            continue
        
        # Generate a few instances of this cycle type
        best_clauses = float('inf')
        for trial in range(3):
            try:
                edges = generate_2factor_with_cycles(m, cycle_type, rng)
                cls = count_clauses(edges)
                best_clauses = min(best_clauses, cls)
            except Exception as e:
                continue
        
        if best_clauses < float('inf'):
            print(f"  Cycles {str(cycle_type):30s}: ~{best_clauses:5d} clauses (proxy)", flush=True)

if __name__ == "__main__":
    analyze_best_configs()
