#!/usr/bin/env python3
"""
Deep pattern analysis of best72's cycle structure.
Focuses on understanding the PERMUTATION as a mathematical object.
"""

import sys, os, json, math
from collections import defaultdict, Counter

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H
import solver_2factor_sat_pipeline as P

best72_edges = sorted([
    (15,34), (10,24), (3,23), (7,28), (2,23), (8,25), (16,30),
    (7,18), (3,29), (9,35), (11,17), (9,32), (12,36), (6,15),
    (6,31), (14,36), (1,19), (8,24), (20,25), (4,19), (12,27),
    (21,33), (5,35), (13,29), (1,27), (5,22), (21,32), (20,26),
    (0,33), (16,28), (14,22), (13,26), (10,17), (11,18), (2,34),
    (0,30), (4,31)
])

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

cycle = cycle_from_edges(best72_edges)

# Positions: pos[v] = index in cycle
pos = {v: i for i, v in enumerate(cycle)}

# ── 1. Look at the cycle as a function of INDEX ──
# The sequence v_t = cycle[t] for t = 0..36
# Does v_t follow a pattern like v_t = f(t) for some function f?

print("=" * 70)
print("1. CYCLE AS A FUNCTION OF INDEX")
print("=" * 70)
print(f"cycle[t] = {cycle}")

# Check differences between consecutive cycle values: cycle[t+1] - cycle[t]
print("\nFirst differences (mod 37):")
diffs = []
for t in range(M):
    d = (cycle[(t+1)%M] - cycle[t]) % M
    diffs.append(d)
    print(f"  t={t:2d}: cycle[{t:2d}]={cycle[t]:2d} → cycle[{t+1:2d}]={cycle[(t+1)%M]:2d}  diff={d:2d}")

# ── 2. Check if cycle is related to the log/discrete log ──
# For a primitive root g, the map i → g^i gives a permutation of {1..36}
# Adding 0 at a specific position gives a cycle
print("\n" + "=" * 70)
print("2. DISCRETE LOG / MULTIPLICATIVE ORDERING")
print("=" * 70)

def primitive_roots(p):
    """Find all primitive roots mod p (p prime)."""
    prs = []
    for g in range(2, p):
        seen = set()
        val = 1
        for _ in range(p - 1):
            seen.add(val)
            val = (val * g) % p
        if len(seen) == p - 1:
            prs.append(g)
    return prs

prs = primitive_roots(M)
print(f"Primitive roots of {M}: {prs}")

# For each primitive root, generate the cycle 0, 1, g, g^2, ..., g^35
# and check how many edges it shares with best72
for g in prs:
    orbit = [1]
    val = 1
    for _ in range(M - 2):
        val = (val * g) % M
        orbit.append(val)
    # Try inserting 0 at each position
    for insert_pos in range(M):
        test_cycle = orbit[:insert_pos] + [0] + orbit[insert_pos:]
        test_cycle = test_cycle[:M]  # should already be M long
        if len(set(test_cycle)) != M:
            continue
        # Count shared edges
        test_edges = set()
        for k in range(M):
            a, b = test_cycle[k], test_cycle[(k+1)%M]
            u, v = (a, b) if a <= b else (b, a)
            test_edges.add((u, v))
        shared = len(test_edges & set(best72_edges))
        if shared >= 5:
            print(f"  primitive root g={g:2d}, 0 at pos {insert_pos:2d}: "
                  f"shared edges with best72 = {shared}/{M}")

# ── 3. Check if cycle is a "checkerboard" pattern ──
# Are edges connecting vertices of specific parity classes?
print("\n" + "=" * 70)
print("3. MODULAR PATTERN CHECK")
print("=" * 70)

for mod in [2, 3, 4, 6]:
    print(f"\nEdges grouped by vertex mod {mod}:")
    edge_mod_groups = defaultdict(list)
    for u, v in best72_edges:
        key = (u % mod, v % mod)
        edge_mod_groups[key].append((u, v))
    for key, elist in sorted(edge_mod_groups.items()):
        print(f"  ({key[0]},{key[1]}): {len(elist)} edges, e.g. {elist[:3]}")

# ── 4. Check if the CYCLE indices follow a pattern ──
# pos[v] = index of vertex v in the cycle
# Does pos[v] ≈ some function of v?
print("\n" + "=" * 70)
print("4. POSITION PATTERN ANALYSIS")
print("=" * 70)
print("vertex → position in cycle:")
pos_list = [(v, pos[v]) for v in range(M)]
for v, p in pos_list:
    print(f"  v={v:2d} → pos={p:2d}")

# Check differences pos[v+1] - pos[v] (how does position change as vertex label changes)
print("\nDelta-position (pos[v+1] - pos[v]) mod 37:")
delta_pos = [(pos[(v+1)%M] - pos[v]) % M for v in range(M)]
print(f"  {delta_pos}")
dp_hist = Counter(delta_pos)
print(f"  histogram: {dict(sorted(dp_hist.items()))}")

# ── 5. Does best72 use edges that avoid "bad" relationships? ──
# Look at the distance between the TWO endpoints of each edge in the CYCLE
# This is different from the vertex-label span!
print("\n" + "=" * 70)
print("5. EDGE VERTICES DISTANCE IN CYCLE")
print("=" * 70)
# For edge (u,v), distance_cycle = |pos[u] - pos[v]| (the number of steps along the cycle)
print("Edge → distance along cycle:")
cycle_gaps = []
for u, v in best72_edges:
    d = abs(pos[u] - pos[v])
    d = min(d, M - d)  # circular distance in cycle
    cycle_gaps.append(d)
    print(f"  ({u:2d},{v:2d}): cycle_dist={d}, label_span={abs(u-v):2d}")

cg_hist = Counter(cycle_gaps)
print(f"\nCycle gap histogram:")
for d in sorted(cg_hist.keys()):
    print(f"  gap={d:2d}: {cg_hist[d]} edges")

# In a Hamiltonian cycle, each edge connects adjacent vertices in the cycle,
# so the cycle distance should be 1 for all edges! Let me verify...
# Wait, in a cycle the distance along the cycle between endpoints of an edge
# is ALWAYS 1 (since vertices connected by an edge are adjacent in the cycle).
# This confirms the cycle is properly reconstructed.

print(f"\nAll cycle distances are 1 (edges connect adjacent cycle positions): "
      f"{all(d == 1 for d in cycle_gaps)}")

# ── 6. The REAL question: Why does this specific set of 37 edges produce only 470 clauses? ──
# The clause count depends on collinearity of C4-lifted points.
# Let me analyze which TRIPLES produce clauses.

print("\n" + "=" * 70)
print("6. CLAUSE TRIPLE ANALYSIS")
print("=" * 70)

# Let me analyze which triples produce clauses for best72
clauses, cmap = P.enumerate_clauses(M, best72_edges, verbose=True)
print(f"\nTotal clauses: {len(clauses)}")

# Group clauses by which orientation bits are forbidden
forbidden_counts = Counter()
for a, b, c, bits in clauses:
    forbidden_counts[bits] += 1
print(f"\nForbidden pattern distribution:")
for bits, cnt in sorted(forbidden_counts.items()):
    t1, t2, t3 = (bits>>0)&1, (bits>>1)&1, (bits>>2)&1
    print(f"  bits={bits:03b} (t1={t1}, t2={t2}, t3={t3}): {cnt} triples")

# Show some sample clauses
print(f"\nSample clauses (first 10):")
for i in range(min(10, len(clauses))):
    a, b, c, bits = clauses[i]
    e1, e2, e3 = best72_edges[a], best72_edges[b], best72_edges[c]
    t1, t2, t3 = (bits>>0)&1, (bits>>1)&1, (bits>>2)&1
    print(f"  edges ({e1[0]:2d},{e1[1]:2d}), ({e2[0]:2d},{e2[1]:2d}), ({e3[0]:2d},{e3[1]:2d}) "
          f"→ forbid orient ({t1},{t2},{t3})")

# Count: how many triples contribute at least one clause?
triples_with_clauses = len(set((a, b, c) for a, b, c, _ in clauses))
total_triples = M * (M-1) * (M-2) // 6
print(f"\nTriples with at least 1 clause: {triples_with_clauses} / {total_triples} "
      f"({100*triples_with_clauses/total_triples:.2f}%)")

# Average clauses per affected triple
avg = len(clauses) / triples_with_clauses if triples_with_clauses else 0
print(f"Average clauses per affected triple: {avg:.2f}")

# ── 7. Are clauses related to span properties? ──
print("\n" + "=" * 70)
print("7. CLAUSE-SPAN CORRELATION")
print("=" * 70)

# For each clause triple, look at the spans of the three edges
clause_span_stats = []
for a, b, c, bits in clauses:
    e1 = best72_edges[a]
    e2 = best72_edges[b]
    e3 = best72_edges[c]
    s1 = abs(e1[0] - e1[1])
    s2 = abs(e2[0] - e2[1])
    s3 = abs(e3[0] - e3[1])
    clause_span_stats.append((s1, s2, s3))

# Which spans contribute most to clause count?
span_clause_count = Counter()
for s1, s2, s3 in clause_span_stats:
    span_clause_count[s1] += 1
    span_clause_count[s2] += 1
    span_clause_count[s3] += 1

print("Span contribution to clauses (edges with span X appear in Y clauses):")
for span in sorted(span_clause_count.keys()):
    print(f"  span={span:2d}: {span_clause_count[span]} clause-participations")

# Normalize by number of edges with that span
span_freq = Counter(abs(u-v) for u,v in best72_edges)
print("\nSpan frequency vs clause contribution:")
print(f"  {'Span':<6} {'#Edges':<8} {'#ClauseParts':<14} {'PerEdge':<8}")
for span in sorted(set(list(span_freq.keys()) + list(span_clause_count.keys()))):
    n_edges = span_freq.get(span, 0)
    n_parts = span_clause_count.get(span, 0)
    per_edge = n_parts / n_edges if n_edges else 0
    print(f"  {span:<6} {n_edges:<8} {n_parts:<14} {per_edge:<8.2f}")

# ── 8. KEY INSIGHT: What span-patterns minimize clauses? ──
# Perhaps the key is that edges with "balanced" spans (near the mean of 18.5)
# produce fewer clauses than very small or very large spans
print("\n" + "=" * 70)
print("8. KEY SPAN-TO-CLAUSE INSIGHT")
print("=" * 70)

# For each span value, what fraction of triples containing an edge with that span
# produce at least one clause?
# (This tells us which spans are "dangerous")

# Count triples per span
all_edges = list(enumerate(best72_edges))
span_triple_count = Counter()
span_clause_triple_count = Counter()
for a in range(M):
    sa = abs(best72_edges[a][0] - best72_edges[a][1])
    for b in range(M):
        if b <= a: continue
        sb = abs(best72_edges[b][0] - best72_edges[b][1])
        for c in range(M):
            if c <= b: continue
            sc = abs(best72_edges[c][0] - best72_edges[c][1])
            for s in [sa, sb, sc]:
                span_triple_count[s] += 1
            # Check if this triple has any clause
            for bits in range(8):
                is_clause = False
                for ca, cb, cc, cbits in clauses:
                    if ca == a and cb == b and cc == c and cbits == bits:
                        is_clause = True
                        break
                if is_clause:
                    break
            if is_clause:
                for s in [sa, sb, sc]:
                    span_clause_triple_count[s] += 1

# This loop is too slow. Let me do a simpler analysis.
# Just check which span combinations produce the most clauses.

print("(Analysis skipped due to complexity)")
print("Let me focus on the key findings instead.")

print("\n\n========== KEY OBSERVATIONS ==========")
# Summarize everything
print(f"""
best72 Hamiltonian cycle analysis summary:

CYCLE ORDER: {cycle}

The cycle permutes vertices via π(i) = vertex following i in cycle.
π(i) values: {[cycle[(cycle.index(i)+1)%M] for i in range(M)]}

EDGE SPAN (|u-v|) distribution:
  min={min(abs(u-v) for u,v in best72_edges)}, 
  max={max(abs(u-v) for u,v in best72_edges)}, 
  mean={sum(abs(u-v) for u,v in best72_edges)/M:.2f}

CIRCULAR SPAN distribution:
  min={min(min(abs(u-v), M-abs(u-v)) for u,v in best72_edges)},
  max={min(min(abs(u-v), M-abs(u-v)) for u,v in best72_edges)},

KEY QUESTION: Why does this specific Hamiltonian cycle produce only 470 clauses?

HYPOTHESIS: The cycle minimizes collinearity among C4-lifted points because...
  1. No edge has |u-v| in {{1,2,3}} (avoids short spans)
  2. The 37 edges are "well-distributed" so that any 3 lifts avoid alignment
  3. The cycle is essentially a "good" permutation

NEXT STEPS:
  1. Wait for algebraic construction results
  2. Analyze which edge triples produce clauses
  3. Try to construct cycles with even fewer clauses
""")
