"""
triple_matching_bound.py — 验证每个 2-因子的违例下界

关键问题：是否存在 16 个"活性"且边不交的三元组？
如果存在，则最小违例 ≥ 16（每个违例只能覆盖一个三角形，而三角形是边不交的）。

对 config_408：
1. 找出所有有至少 1 个子句的三元组（"活性"三元组）
2. 在这些中找最大边不交匹配
3. 如果匹配大小 ≥ 16，则该 2-因子的最小违例必然 ≥ 16
"""

import sys, os, json
from collections import defaultdict

HERE = "D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis"
sys.path.insert(0, HERE)
from solver_2factor_sat_pipeline import enumerate_clauses

def max_edge_disjoint_matching(edges, active_triples):
    """
    Find largest set of edge-disjoint triples from active_triples.
    Greedy approximation (usually optimal for this type).
    """
    # Build: each edge → list of triples containing it
    edge_to_triples = defaultdict(list)
    for t in active_triples:
        for e in t:
            edge_to_triples[e].append(t)
    
    # Greedy: pick triple with smallest max-edge-degree first
    covered_edges = set()
    matching = []
    
    # Sort triples by how constrained they are
    remaining = set(active_triples)
    
    while remaining:
        # Find triple whose max edge is least constrained
        best_t = None
        best_score = 1e9
        for t in remaining:
            # Score = sum of degrees of edges in this triple
            score = sum(len(edge_to_triples[e]) for e in t if e not in covered_edges)
            if score < best_score:
                best_score = score
                best_t = t
        
        if best_t is None:
            break
        
        # Check: all 3 edges must be free
        if all(e not in covered_edges for e in best_t):
            matching.append(best_t)
            for e in best_t:
                covered_edges.add(e)
            # Remove all triples sharing an edge with best_t
            to_remove = set()
            for t in remaining:
                if any(e in covered_edges for e in t):
                    to_remove.add(t)
            remaining -= to_remove
        else:
            remaining.remove(best_t)
    
    return matching

# ===========================================================
# 对 config_408
# ===========================================================
print("=" * 60)
print("TRIPLE MATCHING BOUND — config_408")
print("=" * 60)

with open(f"{HERE}/results/config_408_edges.json") as f:
    data = json.load(f)
edges = [tuple(e) for e in data["edges"]]

clause_list, clause_map = enumerate_clauses(37, edges, verbose=False)
print(f"  Total clauses: {len(clause_list)}")
print(f"  Active triples: {len(clause_map)} (out of {37*36*35//6})")

# Get all triples that have at least 1 forbidden orientation
active_triples = {t for t, results in clause_map.items() if any(results)}
print(f"  Active: {len(active_triples)} triples")

# Max edge-disjoint matching
matching = max_edge_disjoint_matching(edges, active_triples)
print(f"  Max edge-disjoint matching: {len(matching)}")

print(f"\n  Matching triples ({len(matching)}):")
for t in matching[:20]:
    edges_in_triple = [edges[i] for i in t]
    print(f"    {t}: {edges_in_triple}")

# Also check: what's the distribution of active-triple degree per edge?
edge_degree = defaultdict(int)
for t in active_triples:
    for e in t:
        edge_degree[e] += 1

min_deg = min(edge_degree.values())
max_deg = max(edge_degree.values())
print(f"\n  Active-triple degree per edge: min={min_deg}, max={max_deg}")

# ===========================================================
# Also check: what if we use ALL triples, not just active ones?
# ===========================================================
print(f"\n{'='*60}")
print("MAX MATCHING — all triples")
print(f"{'='*60}")

all_triples = []
from itertools import combinations
for a, b, c in combinations(range(37), 3):
    all_triples.append((a,b,c))

# Edge-disjoint matching on ALL triples (this should be floor(37/3)=12)
all_matching = max_edge_disjoint_matching(edges, all_triples)
print(f"  Max edge-disjoint matching (all triples, any geometry): {len(all_matching)}")
print(f"  Theoretical maximum = floor(37/3) = 12")

# ===========================================================
# 结论
# ===========================================================
print(f"\n{'='*60}")
print("CONCLUSION")
print(f"{'='*60}")
print(f"  Edge-disjoint matching of active triples: {len(matching)}")
print(f"  Known min violations: 16 (CP-SAT proven)")
if len(matching) >= 16:
    print(f"  → Matching ≥ 16, so minimum violations ≥ 16 IS structural")
else:
    print(f"  → Matching = {len(matching)} < 16, so the 16 violations are NOT")
    print(f"     from a simple edge-disjoint matching bound")
    print(f"     The violation structure is more complex (shared edges)")
