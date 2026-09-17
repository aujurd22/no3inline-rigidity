"""
D5v2: Lower bound analysis for rot4-NTIL m=37 orientation subproblem.

We analyze the MaxSAT clause sets to find structural lower bounds on
the minimum number of violations for ANY 2-factor on Z/37Z.

Key questions:
1. Are there unavoidable clauses (edges that must appear in forbidden triples)?
2. Can we prove a lower bound using covering/rearrangement arguments?
3. Is there a graph-theoretic obstruction that forces ≥17 violations?
4. Do the clause patterns reveal a modular obstruction (×4 factor)?
"""

import json
import os
import itertools
from collections import defaultdict, Counter
import math
import sys

RESULTS_DIR = os.path.dirname(os.path.abspath(__file__)) + "/results"

def load_clauses(name):
    """Load clause data from JSON file."""
    fname = f"swarm_D1_2_{name}_clauses.json"
    path = os.path.join(RESULTS_DIR, fname)
    with open(path) as f:
        data = json.load(f)
    return data

def load_solution(name):
    """Load solution data."""
    fname = f"swarm_D1_2_{name}_solved.json"
    path = os.path.join(RESULTS_DIR, fname)
    with open(path) as f:
        data = json.load(f)
    return data

def load_mutation_448():
    """Load the 448-clause mutation result."""
    path = os.path.join(RESULTS_DIR, "mutation_448_maxsat_long.json")
    with open(path) as f:
        return json.load(f)

def analyze_bit_patterns(clauses):
    """Analyze the bit patterns in clauses to find structure."""
    # clauses are [e1, e2, e3, b1, b2, b3]
    triple_to_patterns = defaultdict(list)
    for c in clauses:
        key = tuple(sorted(c[:3]))  # canonical triple
        pattern = tuple(c[3:])
        triple_to_patterns[key].append(pattern)
    
    # Count how many patterns per triple
    pattern_count_dist = Counter()
    for triple, patterns in triple_to_patterns.items():
        pattern_count_dist[len(patterns)] += 1
    
    # Count which pattern pairs
    pair_counts = Counter()
    for triple, patterns in triple_to_patterns.items():
        if len(patterns) == 2:
            p1, p2 = patterns
            pair = tuple(sorted([p1, p2]))
            pair_counts[pair] += 1
        elif len(patterns) == 4:
            pair_counts[("2_pairs",)] += 1
    
    return {
        "unique_triples": len(triple_to_patterns),
        "pattern_count_dist": dict(pattern_count_dist),
        "pair_counts": dict(pair_counts),
    }

def analyze_edge_cooccurrence(clauses, n_edges=37):
    """Build edge co-occurrence graph from clauses."""
    # Build adjacency: edge a co-occurs with edge b in how many clauses?
    cooccur = defaultdict(lambda: defaultdict(int))
    edge_clause_count = defaultdict(int)  # how many clauses each edge appears in
    
    for c in clauses:
        e1, e2, e3 = c[:3]
        edge_clause_count[e1] += 1
        edge_clause_count[e2] += 1
        edge_clause_count[e3] += 1
        for pair in [(e1, e2), (e1, e3), (e2, e3)]:
            a, b = sorted(pair)
            cooccur[a][b] += 1
            cooccur[b][a] += 1
    
    return {
        "edge_clause_count": dict(edge_clause_count),
        "edge_cooccurrence": {str(k): dict(v) for k, v in cooccur.items()},
    }

def analyze_triple_graph(clauses, n_edges=37):
    """Build a graph where edges connect if they share a forbidden triple."""
    triple_hypergraph = defaultdict(list)
    for c in clauses:
        e1, e2, e3 = sorted(c[:3])
        triple_hypergraph[(e1, e2, e3)].append(tuple(c[3:]))
    
    # Build edge-edge incidence matrix
    edge_pairs = defaultdict(set)
    for triple in triple_hypergraph:
        e1, e2, e3 = triple
        edge_pairs[(e1, e2)].add(e3)
        edge_pairs[(e1, e3)].add(e2)
        edge_pairs[(e2, e3)].add(e1)
    
    return {
        "n_forbidden_triples": len(triple_hypergraph),
        "triples": list(triple_hypergraph.keys()),
    }

def find_min_vertex_cover_triples(triple_hypergraph, n_edges=37):
    """
    Find a minimal set of edges such that every forbidden triple contains at least one of them.
    This is a vertex cover of the 3-uniform hypergraph.
    Since it's NP-hard in general, we use a greedy approximation.
    """
    edges = list(range(n_edges))
    triples = list(triple_hypergraph.keys())
    
    covered = set()
    covered_triples = set()
    vertex_cover = []
    
    while len(covered_triples) < len(triples):
        # Find edge that covers most uncovered triples
        best_edge = None
        best_count = 0
        for e in edges:
            if e in vertex_cover:
                continue
            count = 0
            for i, t in enumerate(triples):
                if i in covered_triples:
                    continue
                if e in t:
                    count += 1
            if count > best_count:
                best_count = count
                best_edge = e
        
        if best_edge is None:
            break
        
        vertex_cover.append(best_edge)
        for i, t in enumerate(triples):
            if best_edge in t:
                covered_triples.add(i)
    
    return vertex_cover

def lovasz_local_lemma_bound(clauses, n_edges=37):
    """
    Compute Lovász Local Lemma type bound.
    For 3-SAT with each clause having 3 variables and each variable appearing in d clauses,
    LLL says the formula is satisfiable if e * d * 2^(-3) < 1, i.e., d < 8/e ≈ 2.94.
    But with dependency graph, the criterion involves the degree.
    """
    # Count variable occurrences
    var_occurrences = defaultdict(int)
    for c in clauses:
        for i in range(3):
            var_occurrences[c[i]] += 1
    
    max_occurrence = max(var_occurrences.values())
    avg_occurrence = sum(var_occurrences.values()) / n_edges
    
    # Dependency graph degree: two clauses are dependent if they share a variable
    # Build clause dependency
    clause_var_map = []
    for c in clauses:
        clause_var_map.append(set(c[:3]))
    
    dependency_degrees = []
    for i in range(len(clauses)):
        deps = 0
        vars_i = clause_var_map[i]
        for j in range(len(clauses)):
            if i == j:
                continue
            if vars_i & clause_var_map[j]:
                deps += 1
        dependency_degrees.append(deps)
    
    max_dep = max(dependency_degrees) if dependency_degrees else 0
    avg_dep = sum(dependency_degrees) / len(clauses) if clauses else 0
    
    return {
        "max_var_occurrence": max_occurrence,
        "avg_var_occurrence": avg_occurrence,
        "max_dependency_degree": max_dep,
        "avg_dependency_degree": avg_dep,
        "lll_condition": f"Var-occurrence-based: need d < 8/e = 2.94, but max d = {max_occurrence}. LLL fails.",
    }

def independent_set_bound(clauses, n_edges=37):
    """
    Since each clause forbids exactly 1 of 8 patterns for a triple, and the orientation
    assignment must avoid all forbidden patterns, we can think of this as:
    
    For each triple (e1,e2,e3), at most 7 of 8 patterns are allowed.
    The problem is: does there exist an assignment t: [37] → {0,1} such that for each
    triple, the pattern is not the forbidden one?
    
    A simple lower bound: For any set of k edges, there are k*(k-1)*(k-2)/6 triples.
    If many of those triples have forbidden patterns, we might get a bound.
    """
    # Build triple->forbidden_patterns map
    triple_forbidden = defaultdict(set)
    for c in clauses:
        triple_forbidden[tuple(sorted(c[:3]))].add(tuple(c[3:]))
    
    # For each set of variables, count how many forbidden patterns constrain them
    # Focus on variable pairs
    pair_forbidden = defaultdict(set)
    for c in clauses:
        e1, e2, e3 = c[:3]
        b1, b2, b3 = c[3:]
        # For each pair in the triple, record the induced pattern
        pair_forbidden[(e1, e2)].add((b1, b2))
        pair_forbidden[(e1, e3)].add((b1, b3))
        pair_forbidden[(e2, e3)].add((b2, b3))
    
    max_pair_forbidden = max(len(v) for v in pair_forbidden.values())
    avg_pair_forbidden = sum(len(v) for v in pair_forbidden.values()) / len(pair_forbidden) if pair_forbidden else 0
    
    # Count how many pairs have all 4 patterns forbidden
    all_four_forbidden = sum(1 for v in pair_forbidden.values() if len(v) >= 4)
    three_forbidden = sum(1 for v in pair_forbidden.values() if len(v) >= 3)
    
    return {
        "max_pair_forbidden_patterns": max_pair_forbidden,
        "avg_pair_forbidden_patterns": avg_pair_forbidden,
        "pairs_all_4_forbidden": all_four_forbidden,
        "pairs_3_or_more_forbidden": three_forbidden,
    }

def analyze_forbidden_cores(clauses, n_edges=37):
    """
    Find minimal unsatisfiable cores. 
    For 3-SAT, a minimal UNSAT core would be a set of clauses that together are
    unsatisfiable but any proper subset is satisfiable.
    Since clauses come in complementary pairs, look for "impossible" patterns.
    """
    # For each edge e, consider its "type" based on patterns with other edges
    # If an edge e has property that certain assignment values always lead to violations,
    # this suggests unavoidable violations.
    
    # Count for each edge, how many clauses forbid t_e = 0 vs t_e = 1
    forbid_zero = defaultdict(int)
    forbid_one = defaultdict(int)
    for c in clauses:
        e1, e2, e3, b1, b2, b3 = c
        # For edge e1:
        if b1 == 0:
            forbid_zero[e1] += 1
        else:
            forbid_one[e1] += 1
        if b2 == 0:
            forbid_zero[e2] += 1
        else:
            forbid_one[e2] += 1
        if b3 == 0:
            forbid_zero[e3] += 1
        else:
            forbid_one[e3] += 1
    
    # For each edge, what fraction of its clauses require each bit value?
    edge_bias = {}
    for e in range(n_edges):
        total = forbid_zero.get(e, 0) + forbid_one.get(e, 0)
        if total > 0:
            edge_bias[e] = {
                "forbid_0": forbid_zero.get(e, 0),
                "forbid_1": forbid_one.get(e, 0),
                "ratio_0": forbid_zero.get(e, 0) / total,
            }
        else:
            edge_bias[e] = {"forbid_0": 0, "forbid_1": 0, "ratio_0": 0.5}
    
    return edge_bias

def compute_total_possible_assignments(clauses, n_edges=37):
    """
    The clauses forbid certain orientation patterns. Count how many total assignments
    of 37 bits would be needed to avoid all forbidden patterns.
    
    Each clause forbids exactly 1/8 of assignments for those 3 edges.
    But clauses overlap, so the fraction of assignments ruled out is not just N/8.
    """
    # This is complex - the clauses form a CNF formula
    # For an exact count we'd need #SAT which is #P-complete
    # But we can get an estimate
    
    n_clauses = len(clauses)
    # If all clauses were on disjoint variable sets, fraction = (7/8)^n_clauses
    # But they overlap heavily
    
    # Try to estimate using maximum independent set of clauses (clauses on disjoint variables)
    # Greedy: pick clauses that share no variables
    selected = []
    used_vars = set()
    for c in clauses:
        vars_set = set(c[:3])
        if not (vars_set & used_vars):
            selected.append(c)
            used_vars |= vars_set
    
    # Bound: at most (7/8)^len(selected) * 2^(n_edges - len(disjoint_vars))
    # Actually: total assignments that avoid all selected clauses
    disjoint_vars = len(used_vars)
    fraction_allowed = (7/8)**len(selected)
    total_allowed = fraction_allowed * (2**(n_edges - disjoint_vars)) * (2**disjoint_vars)
    # Wait, this isn't right. Let me think again.
    
    # Better: The selected clauses are on disjoint variable sets.
    # For each selected clause on variables (e1,e2,e3), it forbids 1/8 of assignments.
    # So independently, fraction of assignments satisfying all selected = (7/8)^len(selected).
    # The remaining variables are unconstrained.
    
    total_possible = (7/8)**len(selected) * (2**n_edges)
    # But this overcounts because there are more clauses beyond the independent set.
    
    return {
        "n_independent_clauses": len(selected),
        "fraction_allowed_independent": (7/8)**len(selected),
        "estimated_total_valid_assignments": total_possible,
    }

def analyze_2factor_clause_edges(name, data):
    """Analyze the specific 2-factor's edge structure vs clause structure."""
    edges = data["edges"]
    clauses = data["clauses"]
    
    # For each edge, what's its incident vertex?
    edge_vertices = {}
    for i, (v1, v2) in enumerate(edges):
        edge_vertices[i] = (v1, v2)
    
    # Build vertex-to-edge mapping
    vertex_edges = defaultdict(list)
    for i, (v1, v2) in enumerate(edges):
        vertex_edges[v1].append(i)
        vertex_edges[v2].append(i)
    
    # For each edge, what's the set of edges it shares vertices with?
    edge_neighbors = {}
    for i in range(len(edges)):
        v1, v2 = edges[i]
        neigh = set()
        for v in (v1, v2):
            for other in vertex_edges[v]:
                if other != i:
                    neigh.add(other)
        edge_neighbors[i] = neigh
    
    # For each pair of edges, do they share a vertex? (adjacent)
    adjacent_pairs = set()
    for i in range(len(edges)):
        v1_i, v2_i = edges[i]
        for j in range(i+1, len(edges)):
            v1_j, v2_j = edges[j]
            if len({v1_i, v2_i} & {v1_j, v2_j}) > 0:
                adjacent_pairs.add((i, j))
    
    # What fraction of forbidden triples involve adjacent edges?
    triples_adjacent = 0
    triples_total = 0
    for c in clauses:
        e1, e2, e3 = c[:3]
        triples_total += 1
        # Check if all three edges are pairwise adjacent (share vertices)
        pairs = [(e1,e2), (e1,e3), (e2,e3)]
        is_all_adjacent = all(p in adjacent_pairs for p in pairs)
        if is_all_adjacent:
            triples_adjacent += 1
    
    # What about triples where exactly 2 edges are adjacent?
    triples_2_adjacent = 0
    triples_1_adjacent = 0
    triples_0_adjacent = 0
    for c in clauses:
        e1, e2, e3 = c[:3]
        pairs = [(e1,e2) if e1<e2 else (e2,e1), 
                 (e1,e3) if e1<e3 else (e3,e1),
                 (e2,e3) if e2<e3 else (e3,e2)]
        adj_count = sum(1 for p in pairs if p in adjacent_pairs)
        if adj_count == 3:
            triples_2_adjacent += 1  # All 3 share a common vertex? No, that's 3 adj pairs
        elif adj_count == 2:
            triples_2_adjacent += 1
        elif adj_count == 1:
            triples_1_adjacent += 1
        else:
            triples_0_adjacent += 1
    
    return {
        "n_adjacent_pairs": len(adjacent_pairs),
        "total_triples_with_adjacent_edges": triples_adjacent,
        "triples_by_adjacency": {
            "0_adjacent": triples_0_adjacent,
            "1_adjacent": triples_1_adjacent,
            "2+_adjacent": triples_2_adjacent,
        },
    }

def count_violations_for_assignment(clauses, assignment):
    """Count how many clauses are violated by an assignment."""
    violations = 0
    for c in clauses:
        e1, e2, e3, b1, b2, b3 = c
        if assignment[e1] == b1 and assignment[e2] == b2 and assignment[e3] == b3:
            violations += 1
    return violations

def analyze_hamiltonian_cycle_property(name, data):
    """
    For a Hamiltonian cycle (single 37-cycle), the edges form a cycle.
    Analyze whether the forbidden triples have a special structure related to
    the cycle order.
    """
    edges = data["edges"]
    clauses = data["clauses"]
    
    # Build cycle ordering
    # For Hamiltonian cycle, edges connect vertices in a cycle
    n = len(edges)
    
    # Build adjacency in the cycle
    cycle_order = {}
    for i, (v1, v2) in enumerate(edges):
        cycle_order[i] = (v1, v2)
    
    # For each clause (e1,e2,e3), compute the "span" in the cycle
    # How far apart are the edges in the cycle?
    # First, build vertex ordering
    vertex_order = {}
    current = 0
    visited = set()
    
    def build_cycle():
        """Build the cycle ordering of vertices."""
        adj = defaultdict(list)
        for v1, v2 in edges:
            adj[v1].append(v2)
            adj[v2].append(v1)
        
        # Follow the cycle
        order = []
        seen = set()
        start = edges[0][0]
        curr = start
        prev = None
        while len(order) < len(edges):
            order.append(curr)
            seen.add(curr)
            next_vert = [v for v in adj[curr] if v != prev][0]
            prev = curr
            curr = next_vert
        return order
    
    try:
        vert_order = build_cycle()
        # Map edges to their position in the cycle
        edge_to_pos = {}
        for i, (v1, v2) in enumerate(edges):
            # Position could be the minimum distance along the cycle
            pos1 = vert_order.index(v1)
            pos2 = vert_order.index(v2)
            # Edge connects two consecutive vertices in the cycle
            edge_to_pos[i] = min(pos1, pos2)
        
        # Now for each clause, compute the distances between edges in the cycle order
        span_stats = []
        for c in clauses:
            e1, e2, e3 = c[:3]
            if e1 in edge_to_pos and e2 in edge_to_pos and e3 in edge_to_pos:
                pos = sorted([edge_to_pos[e1], edge_to_pos[e2], edge_to_pos[e3]])
                span = pos[2] - pos[0]
                span_stats.append(span)
        
        return {
            "cycle_order_found": True,
            "mean_cycle_span": sum(span_stats) / len(span_stats) if span_stats else 0,
            "min_cycle_span": min(span_stats) if span_stats else 0,
            "max_cycle_span": max(span_stats) if span_stats else 0,
        }
    except:
        return {"cycle_order_found": False}

def modular_obstruction_analysis(clauses, n_edges=37):
    """
    Check if there's a modular obstruction: e.g., the sum of violations
    in any assignment must be ≡ something (mod 2, mod 4, mod 8).
    
    The ×4 factor (each violation = 4 collinear triples) suggests mod 4 structure.
    But the question is about CLAUSE violations (which are then multiplied by 4).
    
    Check: Are min_violations always ≡ 1 (mod something)?
    - best72: 18 ≡ 2 mod 4? No, 18 mod 4 = 2. 18 mod 3 = 0.
    - 448-cls: 17 ≡ 1 mod 4, 17 mod 8 = 1.
    - best96: 24 ≡ 0 mod 4, 24 mod 8 = 0.
    - random: 60 ≡ 0 mod 4, 60 mod 8 = 4.
    
    So min_violations can be 17, 18, 24, 60 — not constrained to a single residue class.
    """
    return {"note": "No modular obstruction found in min_violations values (17, 18, 24, 60)"}

def linear_programming_bound(clauses, n_edges=37):
    """
    Formulate as Integer Linear Program and find LP relaxation bound.
    Variables x_e ∈ {0,1} for edge orientation.
    Each clause forbids a specific pattern. Variables y_c ∈ {0,1} for clause satisfaction.
    
    LP relaxation: 0 ≤ x_e ≤ 1, 0 ≤ y_c ≤ 1.
    
    For each clause c = (e1,e2,e3,b1,b2,b3), the constraint is:
    x_e1 = b1 AND x_e2 = b2 AND x_e3 = b3 → y_c = 1 (violated)
    Otherwise y_c = 0.
    
    This can be written as:
    y_c ≥ (1 - |x_e1 - b1|) + (1 - |x_e2 - b2|) + (1 - |x_e3 - b3|) - 2
    
    Which in LP form:
    y_c ≥ (x_e1*Δ + (1-x_e1)*(1-Δ)) + ... - 2
    where Δ = b1 means if b1=1, term = x_e1, if b1=0, term = (1-x_e1).
    
    But this is already linear! Let's write it directly.
    
    For b=1: x_e. For b=0: (1-x_e). Sum of three such terms minus 2 is the "not all satisfied" indicator.
    
    Actually, the 3-CNF clause l1 ∨ l2 ∨ l3 (where li = x_ei or ¬x_ei) is violated iff
    l1 = l2 = l3 = FALSE. In LP relaxation, we can write:
    
    For clause with li = x_ei (when bi=0): literal = x_ei
    For clause with li = ¬x_ei (when bi=1): literal = 1-x_ei
    
    The clause is satisfied if l1 + l2 + l3 ≥ 1.
    So in relaxation: y_c ≥ 1 - (l1 + l2 + l3)/3? No...
    
    Actually, y_c = 1 if the clause IS violated. The clause is violated when l1=l2=l3=0.
    So y_c ≤ 1 - (l1 + l2 + l3)/3? No, y_c should be 0 when at least one literal is true.
    
    Let me think about this differently. For the standard LP relaxation of MaxSAT:
    Each clause C with literals L1, L2, L3 is:
    y_C ≤ l1 + l2 + l3  (since y_C=1 only if all literals are 0 → 0)
    y_C ≥ 0, y_C ≤ 1
    0 ≤ li ≤ 1
    
    Wait, y_C is the indicator that clause is VIOLATED (unsatisfied).
    So y_C = 1 iff all literals are 0. The constraint is:
    y_C ≤ 1 - l1, y_C ≤ 1 - l2, y_C ≤ 1 - l3  (if any literal is 1, RHS ≤ 0, so y_C = 0)
    
    And we minimize Σ y_C.
    
    The LP relaxation solves this with real-valued x_e, y_c.
    """
    # For small n, we could solve the LP exactly using simplex.
    # But n=37, N=470 is medium-sized. Let's try with PuLP or just do a greedy LP.
    
    # Instead of full LP, let's compute a simple bound:
    # If we sum the constraints y_c ≤ 1 - l_i for each clause, we get:
    # Σ y_c ≤ Σ (1 - l_i for some literal)
    # But this is not very useful.
    
    # Better: For each edge e, consider all clauses where it appears with a specific polarity.
    # If edge e appears in d clauses where it must be 0 to violate, and D where it must be 1,
    # then at most max(d, D) of those clauses can be simultaneously violated...
    # No, that's not right either.
    
    # Let's compute the fractional covering bound instead.
    # For each variable x_e with value a ∈ {0,1}, the clauses that require x_e = a
    # are "activated" for violation. Each triple requires all 3 to match.
    
    # Fractionally: if we set x_e = 0.5 for all e (no preference), then each clause is
    # "violated fractionally" by (0.5)^3 = 0.125. So LP bound ≤ 0.125 * N.
    
    # For best72: 0.125 * 470 = 58.75 (fractional lower bound). 
    # The actual integer optimum is 18, much better.
    # So the LP bound is weak.
    
    frac_bound = len(clauses) / 8
    
    return {
        "lp_fractional_bound": frac_bound,
        "note": "LP relaxation gives trivial bound N/8",
    }

def analyze_variable_entanglement(clauses, n_edges=37):
    """
    Find variables (edges) that are "entangled" — where their orientations
    are forced by many clauses. If we fix all other variables, is a specific
    edge's value forced?
    """
    # For each edge, see if there's a clause that only involves that edge 
    # (which there isn't — all clauses involve 3 edges)
    
    # Instead, for each edge e, examine the set of clauses containing e.
    # In each such clause, the other two edges' assignment can force e's assignment 
    # if both match the forbidden pattern.
    
    # Build edge_to_clauses
    edge_to_clauses = defaultdict(list)
    for i, c in enumerate(clauses):
        e1, e2, e3, b1, b2, b3 = c
        edge_to_clauses[e1].append((i, e2, e3, b1, b2, b3))
        edge_to_clauses[e2].append((i, e1, e3, b2, b1, b3))
        edge_to_clauses[e3].append((i, e1, e2, b3, b1, b2))
    
    # For each edge, find "critical pairs" - pairs of other edges that together
    # force this edge to a specific value
    
    return {"edge_clause_counts": {k: len(v) for k, v in edge_to_clauses.items()}}

def combined_clause_counting_bound(clauses_by_factor):
    """
    Combine data from multiple 2-factors to find universally forbidden patterns.
    If a particular triple+pattern is forbidden across ALL tested 2-factors,
    it's likely universally forbidden.
    """
    # Build intersection of forbidden triples across all 2-factors
    all_forbidden = None
    for name, data in clauses_by_factor.items():
        forbidden_set = set()
        for c in data["clauses"]:
            forbidden_set.add(tuple(c))
        if all_forbidden is None:
            all_forbidden = forbidden_set
        else:
            all_forbidden &= forbidden_set
    
    return {
        "intersection_size": len(all_forbidden) if all_forbidden else 0,
        "universally_forbidden": list(all_forbidden)[:20] if all_forbidden else [],
    }

def main():
    print("=" * 72)
    print("D5v2: Lower Bound Analysis for rot4-NTIL m=37 Orientation Subproblem")
    print("=" * 72)
    
    # Load data
    print("\nLoading data...")
    best72 = load_clauses("best72")
    best96 = load_clauses("best96")
    random_data = load_clauses("random")
    mutation_448 = load_mutation_448()
    
    # Also load the 2-factor data
    with open(os.path.join(RESULTS_DIR, "swarm_D1v3_2factor_analysis.json")) as f:
        factor_analysis = json.load(f)
    
    print(f"  best72: {best72['n_clauses']} clauses")
    print(f"  best96: {best96['n_clauses']} clauses")
    print(f"  random: {random_data['n_clauses']} clauses")
    print(f"  mutation_448: {mutation_448['n_clauses']} clauses (min_violations={mutation_448['min_violations']})")
    
    # === Analysis 1: Bit pattern structure ===
    print("\n" + "=" * 72)
    print("1. BIT PATTERN ANALYSIS")
    print("=" * 72)
    
    for name, data in [("best72", best72), ("best96", best96), ("random", random_data)]:
        analysis = analyze_bit_patterns(data["clauses"])
        print(f"\n  {name}:")
        print(f"    Unique triples with forbidden patterns: {analysis['unique_triples']}")
        print(f"    Pattern count distribution: {analysis['pattern_count_dist']}")
    
    # === Analysis 2: Edge co-occurrence ===
    print("\n" + "=" * 72)
    print("2. EDGE CO-OCCURRENCE ANALYSIS")
    print("=" * 72)
    
    for name, data in [("best72", best72), ("random", random_data)]:
        analysis = analyze_edge_cooccurrence(data["clauses"])
        counts = list(analysis["edge_clause_count"].values())
        print(f"\n  {name}:")
        print(f"    Edge clause counts: min={min(counts)}, max={max(counts)}, avg={sum(counts)/len(counts):.1f}")
        print(f"    Top 5 busiest edges: {sorted(counts, reverse=True)[:5]}")
    
    # === Analysis 3: Independent Set Bound ===
    print("\n" + "=" * 72)
    print("3. INDEPENDENT CLAUSE BOUND")
    print("=" * 72)
    
    for name, data in [("best72", best72), ("best96", best96), ("random", random_data)]:
        bound = compute_total_possible_assignments(data["clauses"])
        print(f"\n  {name}:")
        print(f"    Independent clauses found: {bound['n_independent_clauses']}")
        print(f"    Fraction allowed (from independent set): {bound['fraction_allowed_independent']:.6e}")
        print(f"    Est. valid assignments: {bound['estimated_total_valid_assignments']:.2e}")
    
    # === Analysis 4: Variable Entanglement ===
    print("\n" + "=" * 72)
    print("4. VARIABLE ENTANGLEMENT ANALYSIS")
    print("=" * 72)
    
    for name, data in [("best72", best72)]:
        ent = analyze_variable_entanglement(data["clauses"])
        counts = list(ent["edge_clause_counts"].values())
        print(f"\n  {name}:")
        print(f"    Edge clause counts: min={min(counts)}, max={max(counts)}, avg={sum(counts)/len(counts):.1f}")
    
    # === Analysis 5: Forbidden cores / edge bias ===
    print("\n" + "=" * 72)
    print("5. EDGE BIAS ANALYSIS")
    print("=" * 72)
    
    for name, data in [("best72", best72), ("random", random_data)]:
        bias = analyze_forbidden_cores(data["clauses"])
        # Which edges are most biased?
        ratios = [(e, info["ratio_0"]) for e, info in bias.items()]
        ratios.sort(key=lambda x: abs(x[1] - 0.5), reverse=True)
        print(f"\n  {name}:")
        print(f"    Most biased edges (↑ deviation from 0.5):")
        for e, r in ratios[:5]:
            print(f"      Edge {e}: forbid-0 ratio = {r:.3f}")
        unbiased = sum(1 for _, r in ratios if 0.45 <= r <= 0.55)
        print(f"    Unbiased edges (ratio ∈ [0.45, 0.55]): {unbiased}/{len(ratios)}")
    
    # === Analysis 6: LP/Counting Bounds ===
    print("\n" + "=" * 72)
    print("6. LP AND COUNTING BOUNDS")
    print("=" * 72)
    
    for name, data in [("best72", best72), ("best96", best96), ("random", random_data)]:
        lp_bound = linear_programming_bound(data["clauses"])
        print(f"\n  {name}: N={data['n_clauses']}, LP bound (N/8) = {lp_bound['lp_fractional_bound']:.1f}")
    
    # === Analysis 7: Pair-based bounds ===
    print("\n" + "=" * 72)
    print("7. PAIR-BASED LOWER BOUND ANALYSIS")
    print("=" * 72)
    
    for name, data in [("best72", best72), ("best96", best96), ("random", random_data)]:
        pair_analysis = independent_set_bound(data["clauses"])
        print(f"\n  {name}:")
        print(f"    Max forbidden patterns for a variable pair: {pair_analysis['max_pair_forbidden_patterns']}")
        print(f"    Avg forbidden patterns for a variable pair: {pair_analysis['avg_pair_forbidden_patterns']:.3f}")
        print(f"    Pairs with all 4 patterns forbidden: {pair_analysis['pairs_all_4_forbidden']}")
        print(f"    Pairs with 3+ patterns forbidden: {pair_analysis['pairs_3_or_more_forbidden']}")
    
    # === Analysis 8: Intersection of forbidden patterns ===
    print("\n" + "=" * 72)
    print("8. INTERSECTION OF FORBIDDEN PATTERNS ACROSS 2-FACTORS")
    print("=" * 72)
    
    clauses_data = {"best72": best72, "best96": best96, "random": random_data}
    inter = combined_clause_counting_bound(clauses_data)
    print(f"  Forbidden patterns common to all three: {inter['intersection_size']}")
    if inter['intersection_size'] > 0:
        print(f"  Sample: {inter['universally_forbidden']}")
    else:
        print("  (No universal patterns — each 2-factor has different forbidden triples)")
    
    # === Analysis 9: Check for relationship between N and min violations ===
    print("\n" + "=" * 72)
    print("9. CLAUSE-COUNT VS VIOLATIONS RELATIONSHIP")
    print("=" * 72)
    
    results = [
        ("best72", 470, 18, 72),
        ("best96", 538, 24, 96),
        ("random", 1136, 60, 240),
        ("mutation_448", 448, 17, 68),
    ]
    
    print(f"\n  {'Name':<20} {'Clauses':<10} {'MinV':<8} {'TotalBad':<10} {'Ratio':<8} {'N/8':<8}")
    print(f"  {'-'*20} {'-'*10} {'-'*8} {'-'*10} {'-'*8} {'-'*8}")
    for name, n, mv, tb in results:
        ratio = mv / n if n > 0 else 0
        print(f"  {name:<20} {n:<10} {mv:<8} {tb:<10} {ratio:.4f}    {n/8:.1f}")
    
    # Check if minV/N is consistent
    ratios = [mv/n for _, n, mv, _ in results]
    print(f"\n  Ratio minV/N range: [{min(ratios):.4f}, {max(ratios):.4f}]")
    print(f"  MinV ≈ N × {sum(ratios)/len(ratios):.4f} (avg)")
    
    # Analyze: if minV ≈ N * 0.0384 (for current data), 
    # what N would give minV=0?
    avg_ratio = sum(mv/n for _, n, mv, _ in results) / len(results)
    print(f"  To get minV=0 with avg ratio {avg_ratio:.4f}: need N ≈ 0")
    print(f"  But ratio may not be linear.")
    
    # Hypothesis: min_violations ≈ N * (18/470) + offset?
    # For 448 clauses: proportional prediction = 18 * 448/470 = 17.15 -> 17 or 18
    # For 538 clauses: 18 * 538/470 = 20.6 -> but actual is 24
    # So the ratio changes with different 2-factor structures
    
    # Check: 448 / 470 = 0.953, 17 / 18 = 0.944 (close)
    # 538 / 470 = 1.145, 24 / 18 = 1.333 (not close - different 2-factor)
    
    print(f"\n  Extrapolation (same 2-factor family):")
    print(f"    From best72 (470→18): need N = 0 for minV=0")
    print(f"    From 448-cls (448→17): need N = 0 for minV=0")
    print(f"  Conclusion: clause count alone doesn't determine min violations.")
    print(f"  The structure of WHICH clauses matters more.")
    
    # === Analysis 10: Check for forced assignments ===
    print("\n" + "=" * 72)
    print("10. FORCED ASSIGNMENT ANALYSIS")
    print("=" * 72)
    
    for name, data, solved in [("best72", best72, load_solution("best72")),
                                ("best96", best96, load_solution("best96")),
                                ("random", random_data, load_solution("random"))]:
        orientation = solved["maxsat_solution"]
        violations = count_violations_for_assignment(data["clauses"], orientation)
        print(f"\n  {name}: verified violations = {violations} (expected {solved['maxsat_min_violations']})")
        
        # Count how many clauses each edge is involved in for violated clauses
        violated_clauses_idx = solved["maxsat_sample_violated"]
        edge_violations = defaultdict(int)
        for idx in violated_clauses_idx:
            c = data["clauses"][idx]
            for i in range(3):
                edge_violations[c[i]] += 1
        
        print(f"  Edge involvement in violations:")
        sorted_ev = sorted(edge_violations.items(), key=lambda x: -x[1])
        for e, count in sorted_ev[:10]:
            print(f"    Edge {e}: {count} violations")
    
    # === Analysis 11: Hypergraph density bound ===
    print("\n" + "=" * 72)
    print("11. HYPERGRAPH DENSITY AND TURÁN-TYPE BOUNDS")
    print("=" * 72)
    
    # The 3-uniform hypergraph of forbidden triples
    # If the hypergraph is "dense enough," any 2-coloring creates many monochromatic edges
    # which correspond to violations.
    
    for name, data in [("best72", best72), ("best96", best96), ("random", random_data)]:
        triples = set()
        for c in data["clauses"]:
            triples.add(tuple(sorted(c[:3])))
        
        n_triples = len(triples)
        # Total possible triples on 37 vertices: C(37,3) = 7770
        total_possible = 7770
        
        # What's the minimum number of edges in a 3-uniform hypergraph on 37 vertices
        # such that every 2-coloring of vertices creates a monochromatic edge?
        # This is the multicolor Ramsey number R_2(3,3) — but for 3-uniform hypergraphs!
        
        print(f"\n  {name}:")
        print(f"    Forbidden triples: {n_triples}/{total_possible} ({100*n_triples/total_possible:.2f}%)")
        
        # For 3-uniform hypergraphs, R_2(3,3) is very small
        # Actually, the standard Ramsey number R(3,3) = 6 for graphs.
        # For 3-uniform hypergraphs, R_3(3,3) ≤ ?
        
        # A trivial bound: if the hypergraph contains K_37^(3) (all triples),
        # then by Ramsey's theorem for hypergraphs, a monochromatic K_3^(3) exists.
        # But we need: every 2-coloring of V yields a monochromatic edge.
        # This is different from having a monochromatic K_3 in a 2-colored complete graph.
        
        # In our setting: edges are forbidden triples, variables are vertices.
        # A violation = a triple where all 3 vertices are assigned to match the forbidden pattern.
        # This is like: for each triple, the forbidden assignment is "color all 3 with specific bits."
        # So each triple defines a specific bad 2-coloring of its 3 vertices.
        
        # This is more like: we have a list of 3-sets, each with a forbidden {0,1}^3 assignment.
        # We want to avoid any 3-set having exactly that assignment.
        # This is a hypergraph 2-coloring avoidance problem.
        
        print(f"    Density: {n_triples/total_possible:.6f}")
        
        # If every vertex appears in at least d forbidden triples, 
        # and each triple forbids 1 of 8 patterns,
        # then by pigeonhole, there must be violations.
        
        vertex_counts = defaultdict(int)
        for t in triples:
            for v in t:
                vertex_counts[v] += 1
        
        min_v = min(vertex_counts.values())
        max_v = max(vertex_counts.values())
        avg_v = sum(vertex_counts.values()) / len(vertex_counts)
        
        print(f"    Vertex coverage: min={min_v}, max={max_v}, avg={avg_v:.1f}")
    
    # === Analysis 12: Comparison with random assignment ===
    print("\n" + "=" * 72)
    print("12. RANDOM ASSIGNMENT BENCHMARK")
    print("=" * 72)
    
    import random as rnd
    rnd.seed(12345)
    
    for name, data in [("best72", best72), ("best96", best96), ("random", random_data)]:
        clauses = data["clauses"]
        trials = 10000
        violations = []
        for _ in range(trials):
            assignment = [rnd.randint(0, 1) for _ in range(37)]
            v = count_violations_for_assignment(clauses, assignment)
            violations.append(v)
        
        avg_v = sum(violations) / len(violations)
        min_v = min(violations)
        max_v = max(violations)
        std_v = (sum((v - avg_v)**2 for v in violations) / len(violations))**0.5
        
        print(f"\n  {name} ({len(clauses)} clauses, 10000 trials):")
        print(f"    Random assignment: avg violations = {avg_v:.1f}, σ = {std_v:.1f}")
        print(f"    Min observed: {min_v}, Max observed: {max_v}")
        print(f"    Theoretical expectation: {len(clauses)/8:.1f}")
        best_known = mutation_448['min_violations'] if name == 'best72' else load_solution(name)['maxsat_min_violations'] if name in ('best96', 'random') else 0
        print(f"    Optimal violations (MaxSAT): {best_known}")
    
    print("\n" + "=" * 72)
    print("ANALYSIS COMPLETE")
    print("=" * 72)

if __name__ == "__main__":
    main()
