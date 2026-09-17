#!/usr/bin/env python3
"""
Compare best72 (470 clauses) with best mutated cycle (452 clauses).
Identify what structural changes improve the clause count.
Also capture the 448-clause cycle.
"""

import sys, os, json, math, time, random
from collections import defaultdict, Counter

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H
import solver_2factor_sat_pipeline as P

# ── best72 edges ──
best72_edges = sorted([
    (15,34), (10,24), (3,23), (7,28), (2,23), (8,25), (16,30),
    (7,18), (3,29), (9,35), (11,17), (9,32), (12,36), (6,15),
    (6,31), (14,36), (1,19), (8,24), (20,25), (4,19), (12,27),
    (21,33), (5,35), (13,29), (1,27), (5,22), (21,32), (20,26),
    (0,33), (16,28), (14,22), (13,26), (10,17), (11,18), (2,34),
    (0,30), (4,31)
])

# ── 452-clause mutated edges ──
mutated_452_edges = sorted([
    (0,30), (0,33), (1,19), (1,27), (2,23), (2,34), (3,23), (3,29),
    (4,7), (4,19), (5,22), (5,35), (6,15), (6,31), (7,18),
    (8,24), (8,25), (9,32), (9,35), (10,17), (10,24), (11,17), (11,18),
    (12,27), (12,36), (13,26), (13,29), (14,22), (14,36),
    (15,34), (16,28), (16,30), (20,25), (20,26), (21,32), (21,33), (28,31)
])

def c2_dist(a, b, m=M):
    d = abs(a - b) % m
    return min(d, m - d)

def cycle_from_edges(edges):
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    start = min(adj.keys())
    cycle = [start]
    prev = None
    current = start
    while True:
        nbs = adj[current]
        next_v = nbs[0] if nbs[0] != prev else nbs[1]
        if next_v == start:
            break
        cycle.append(next_v)
        prev = current
        current = next_v
    return cycle

def span_stats(edges, m=M):
    spans = [abs(u-v) for u,v in edges]
    c2_spans = [c2_dist(u, v, m) for u, v in edges]
    return {
        "min_abs": min(spans), "max_abs": max(spans), "mean_abs": sum(spans)/len(spans),
        "min_c2": min(c2_spans), "max_c2": max(c2_spans),
        "abs_spans": sorted(spans),
        "c2_spans": sorted(c2_spans),
        "n_adj_c2": sum(1 for s in c2_spans if s <= 2),
    }

# ══════════════════════════════════════════════════════════════════════════════
# 1. VERIFY CLAUSE COUNTS
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("1. VERIFY CLAUSE COUNTS")
print("=" * 70)

n72 = H.count_clauses_fast(M, best72_edges)
n452 = H.count_clauses_fast(M, mutated_452_edges)
print(f"best72:     {n72} clauses")
print(f"mutated452: {n452} clauses")
assert n72 == 470, f"Expected best72=470, got {n72}"
assert n452 == 452, f"Expected mutated=452, got {n452}"

# ══════════════════════════════════════════════════════════════════════════════
# 2. EDGE-BY-EDGE COMPARISON
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("2. EDGE-BY-EDGE COMPARISON")
print("=" * 70)

set72 = set(best72_edges)
set452 = set(mutated_452_edges)

shared = set72 & set452
only72 = set72 - set452
only452 = set452 - set72

print(f"Shared edges: {len(shared)}/37")
print(f"Only in best72: {len(only72)}")
print(f"Only in mutated452: {len(only452)}")

print("\nEdges only in best72 (removed by mutation):")
for e in sorted(only72):
    print(f"  {e}  span={abs(e[0]-e[1]):2d}  c2={c2_dist(*e)}")

print("\nEdges only in mutated452 (added by mutation):")
for e in sorted(only452):
    print(f"  {e}  span={abs(e[0]-e[1]):2d}  c2={c2_dist(*e)}")

# ══════════════════════════════════════════════════════════════════════════════
# 3. SPAN COMPARISON
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("3. SPAN DISTRIBUTION COMPARISON")
print("=" * 70)

s72 = span_stats(best72_edges)
s452 = span_stats(mutated_452_edges)

print(f"best72     - min_abs={s72['min_abs']} max_abs={s72['max_abs']} "
      f"mean={s72['mean_abs']:.2f} min_c2={s72['min_c2']} "
      f"c2_adj={s72['n_adj_c2']}")
print(f"mutated452 - min_abs={s452['min_abs']} max_abs={s452['max_abs']} "
      f"mean={s452['mean_abs']:.2f} min_c2={s452['min_c2']} "
      f"c2_adj={s452['n_adj_c2']}")

# ══════════════════════════════════════════════════════════════════════════════
# 4. CLAUSE ANALYSIS — which triples produce clauses
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("4. CLAUSE TRIPLE ANALYSIS")
print("=" * 70)

clauses72, cmap72 = P.enumerate_clauses(M, best72_edges, verbose=False)
clauses452, cmap452 = P.enumerate_clauses(M, mutated_452_edges, verbose=False)

n_clauses72 = len(clauses72)
n_clauses452 = len(clauses452)

# Which clause triples are shared?
set_clause_triples72 = set((a,b,c) for a,b,c,_ in clauses72)
set_clause_triples452 = set((a,b,c) for a,b,c,_ in clauses452)
shared_triples = set_clause_triples72 & set_clause_triples452
only72_triples = set_clause_triples72 - set_clause_triples452
only452_triples = set_clause_triples452 - set_clause_triples72

print(f"best72:     {n_clauses72} clauses from {len(set_clause_triples72)} triples")
print(f"mutated452: {n_clauses452} clauses from {len(set_clause_triples452)} triples")
print(f"Shared triples with clauses: {len(shared_triples)}")
print(f"Triples only in best72:      {len(only72_triples)}")
print(f"Triples only in mutated452:  {len(only452_triples)}")

# ══════════════════════════════════════════════════════════════════════════════
# 5. IDENTIFY KEY SWITCHES
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("5. 2-SWITCH ANALYSIS")
print("=" * 70)

# In a 2-switch, two edges are replaced by two others.
# (a,b) and (c,d) → (a,c) and (b,d) OR (a,d) and (b,c)
# The removed edges should be in only72 and the added edges in only452

# Since both are Hamiltonian cycles on the same vertex set,
# the transformation can be decomposed into 2-switches.
# Let's find one possible 2-switch that transforms best72 toward mutated452.

# Actually, let's compute how many 2-switches separate them.
# The symmetric difference has |only72| + |only452| edges.
# Since each 2-switch affects 2 edges (removes 2, adds 2),
# the number of 2-switches is len(only72) / 2.

print(f"Only in best72: {len(only72)} edges → {len(only72)//2} 2-switches")
print(f"Edges removed: {sorted(only72)}")
print(f"Edges added:   {sorted(only452)}")

# ══════════════════════════════════════════════════════════════════════════════
# 6. TRY TO FIND EVEN BETTER CYCLES WITH TARGETED MUTATION
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("6. EXTENDED MUTATION SEARCH (from mutated452)")
print("=" * 70)

rng = random.Random(9999)
best_nc = 452
best_e = mutated_452_edges
results_log = []

for trial in range(100):
    # Nested: try many mutations from current best
    for inner in range(20):
        n_swaps = rng.randint(1, 3)
        e2 = H.mutate_cycle(best_e, rng, n_swaps=n_swaps)
        nc = H.count_clauses_fast(M, e2)
        if nc < best_nc:
            best_nc = nc
            best_e = e2
            msg = f"  ** NEW BEST: trial {trial} inner={inner}: {nc} clauses **"
            print(msg, flush=True)
            results_log.append({"trial": trial, "inner": inner, "n_clauses": nc})
        if nc <= 420:
            break
    if best_nc <= 420:
        break

if best_nc < 452:
    print(f"\n*** BREAKTHROUGH: Found cycle with {best_nc} clauses! ***")
    print(f"Edges: {sorted(best_e)}")
else:
    print(f"\nBest from mutated452 parent: {best_nc} clauses (no improvement)")

# ══════════════════════════════════════════════════════════════════════════════
# 7. SAVE RESULTS
# ══════════════════════════════════════════════════════════════════════════════

output = {
    "best72_clauses": n_clauses72,
    "mutated452_clauses": n_clauses452,
    "best_found_clauses": best_nc,
    "best_found_edges": sorted(best_e),
    "comparison": {
        "shared_edges": sorted(shared),
        "only_best72": sorted(only72),
        "only_mutated452": sorted(only452),
    },
    "span_comparison": {
        "best72": s72,
        "mutated452": s452,
    },
    "clause_triple_counts": {
        "best72": n_clauses72,
        "mutated452": n_clauses452,
        "shared_triples": len(shared_triples),
        "only_best72_triples": len(only72_triples),
        "only_mutated452_triples": len(only452_triples),
    },
}

os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
with open(os.path.join(HERE, "results", "cycle_comparison.json"), "w") as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to results/cycle_comparison.json")
print(f"\n{'='*70}")
print(f"FINAL SUMMARY")
print(f"{'='*70}")
print(f"best72:     {n_clauses72} clauses")
print(f"mutated452: {n_clauses452} clauses")
print(f"best found: {best_nc} clauses")
print(f"Gap from best72: {n_clauses72 - best_nc}")
