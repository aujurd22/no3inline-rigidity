#!/usr/bin/env python
"""
Deep structural analysis: compare clause structure and orientation constraints
between m=36 (SAT) and m=37 (UNSAT) 2-factors.
"""
import sys, json, math, time
from collections import defaultdict, Counter

HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"
sys.path.insert(0, HERE)
sys.path.insert(0, "C:/Users/djr82/.workbuddy/binaries/python/envs/default/Lib/site-packages")

def igcd(a, b):
    a, b = abs(a), abs(b)
    while b: a, b = b, a % b
    return a

def line_of(p, q):
    dx = q[0] - p[0]; dy = q[1] - p[1]
    if dx == 0 and dy == 0: return (0, 0, 0)
    g = igcd(abs(dx), abs(dy))
    A, B = dy // g, -dx // g
    if A < 0 or (A == 0 and B < 0): A, B = -A, -B
    return (A, B, A * p[0] + B * p[1])

def c4_lift(x, y, n):
    pts = [(x, y)]
    for _ in range(3):
        x, y = n - 1 - y, x
        pts.append((x, y))
    return pts

def enumerate_clauses_full(m, edges):
    n = 2 * m
    cell_lifts = {}
    for idx, (u, v) in enumerate(edges):
        cell_lifts[(idx, 0)] = c4_lift(u, v, n)
        cell_lifts[(idx, 1)] = c4_lift(v, u, n) if u != v else c4_lift(u, v, n)
    
    E = len(edges)
    # Per-edge violation stats
    edge_viol_count = Counter()
    triple_patterns = Counter()  # Which of the 8 combos trigger a clause?
    line_clause_count = Counter()  # Which line signatures cause clauses?
    orientation_combo_counts = Counter()
    
    clauses = []
    for a in range(E):
        for b in range(a + 1, E):
            for c in range(b + 1, E):
                for bits in range(8):
                    t1 = (bits >> 0) & 1; t2 = (bits >> 1) & 1; t3 = (bits >> 2) & 1
                    lifts = cell_lifts[(a, t1)] + cell_lifts[(b, t2)] + cell_lifts[(c, t3)]
                    bad = False
                    for i in range(12):
                        if bad: break
                        pi = lifts[i]
                        for j in range(i + 1, 12):
                            pj = lifts[j]
                            if pi[0] == pj[0] and pi[1] == pj[1]: continue
                            k0 = line_of(pi, pj)
                            cnt = 2
                            for k in range(12):
                                if k == i or k == j: continue
                                pk = lifts[k]
                                if pk[0] == pi[0] and pk[1] == pi[1]: continue
                                if line_of(pi, pk) == k0:
                                    cnt += 1
                                    if cnt >= 3: bad = True; break
                    if bad:
                        clauses.append((a, b, c, bits))
                        edge_viol_count[a] += 1
                        edge_viol_count[b] += 1
                        edge_viol_count[c] += 1
                        triple_patterns[bits] += 1
                        # Count what lines are involved
                        for i in range(12):
                            pi = lifts[i]
                            for j in range(i+1, 12):
                                pj = lifts[j]
                                if pi[0] == pj[0] and pi[1] == pj[1]: continue
                                k0 = line_of(pi, pj)
                                cnt = sum(1 for k in range(12) if line_of(pi, lifts[k]) == k0 and lifts[k] != pi)
                                if cnt >= 2:
                                    line_clause_count[k0] += 1
    return clauses, edge_viol_count, triple_patterns, line_clause_count

# Load data
with open(f"{HERE}/results/solutions/m36.json") as f:
    m36 = json.load(f)
cells_m36 = m36['cells']
edges_m36 = [tuple(sorted(c)) for c in cells_m36]

with open(f"{HERE}/results/swarm_D1_2_best72_clauses.json") as f:
    m37 = json.load(f)
edges_m37 = [tuple(e) for e in m37['edges']]

print("=== Enumerating m=36 (SAT solution) ===")
t0 = time.time()
cl_m36, ev_m36, tp_m36, lc_m36 = enumerate_clauses_full(36, edges_m36)
t1 = time.time()
print(f"  {len(cl_m36)} clauses in {t1-t0:.1f}s")

print("\n=== Enumerating m=37 (best72, UNSAT) ===")
t0 = time.time()
cl_m37, ev_m37, tp_m37, lc_m37 = enumerate_clauses_full(37, edges_m37)
t1 = time.time()
print(f"  {len(cl_m37)} clauses in {t1-t0:.1f}s")

# 1. Per-edge violation heatmap
print("\n=== Per-edge clause involvement ===")
print("m=36: top 10 edges most involved in clauses:")
for e, cnt in ev_m36.most_common(10):
    u, v = edges_m36[e]
    print(f"  Edge {e}: ({u},{v}) span={min(abs(u-v), 36-abs(u-v))}: {cnt} clause mentions")
print("\nm=37: top 10 edges most involved in clauses:")
for e, cnt in ev_m37.most_common(10):
    u, v = edges_m37[e]
    print(f"  Edge {e}: ({u},{v}) span={min(abs(u-v), 37-abs(u-v))}: {cnt} clause mentions")

# 2. Pattern of orientation bits that cause clauses
print("\n=== Orientation bit patterns that trigger clauses ===")
print("m=36:")
for bits, cnt in sorted(tp_m36.items()):
    bits_str = f"{bits:03b}"
    print(f"  pattern {bits_str}: {cnt} clauses ({100*cnt/len(cl_m36):.1f}%)")
print("m=37:")
for bits, cnt in sorted(tp_m37.items()):
    bits_str = f"{bits:03b}"
    print(f"  pattern {bits_str}: {cnt} clauses ({100*cnt/len(cl_m37):.1f}%)")

# 3. Distribution of clause density across edges
print("\n=== Clause involvement distribution ===")
for label, ev, m in [("m=36", ev_m36, 36), ("m=37", ev_m37, 37)]:
    cnts = Counter(ev.values())
    print(f"{label}: {dict(sorted(cnts.items()))}")

# 4. Span vs clause involvement correlation
print("\n=== Span vs clause involvement ===")
for label, edges, ev, m in [("m=36", edges_m36, ev_m36, 36), ("m=37", edges_m37, ev_m37, 37)]:
    span_to_clauses = defaultdict(list)
    for e, cnt in ev.items():
        u, v = edges[e]
        s = min(abs(u-v), m - abs(u-v))
        span_to_clauses[s].append(cnt)
    print(f"\n{label}:")
    for s in sorted(span_to_clauses.keys()):
        vals = span_to_clauses[s]
        print(f"  span={s:2d}: avg={sum(vals)/len(vals):.1f}, max={max(vals)}, min={min(vals)}, n_edges={len(vals)}")

# 5. What if we restrict to only edges with specific mod patterns?
print("\n=== Mod 2 analysis of cell coordinates ===")
for label, cells, m in [("m=36", cells_m36, 36), ("m=37", [(u,v) if m37_ori[i]==0 else (v,u) for i,(u,v) in enumerate(edges_m37)], 37)]:
    pass

# Load m=37 orientation
with open(f"{HERE}/results/mutation_448_maxsat_long.json") as f:
    m37_448 = json.load(f)
m37_ori = m37_448.get("orientation", [])
m37_best_cells = []
for i, (u, v) in enumerate(edges_m37):
    if u == v:
        m37_best_cells.append((u, u))
    elif m37_ori[i] == 0:
        m37_best_cells.append((u, v))
    else:
        m37_best_cells.append((v, u))

# 5b. C4 lift parity analysis
print("\n=== C4 lift parity distribution ===")
for label, m, cells in [("m=36", 36, cells_m36), ("m=37", 37, m37_best_cells)]:
    n = 2*m
    parity_counts = Counter()
    for (u, v) in cells:
        pts = c4_lift(u, v, n)
        for (x, y) in pts:
            parity_counts[(x % 2, y % 2)] += 1
    print(f"{label} (n={n}): {dict(sorted(parity_counts.items()))}")

# 6. Triples analysis: which triples of edges co-appear in clauses?
print("\n=== Triple edge participation ===")
# Count how many times each unordered triple (a,b,c) has at least one clause
triple_partic_m36 = Counter()
triple_partic_m37 = Counter()
for (a, b, c, bits) in cl_m36:
    triple_partic_m36[(a, b, c)] += 1
for (a, b, c, bits) in cl_m37:
    triple_partic_m37[(a, b, c)] += 1

print(f"m=36: {len(triple_partic_m36)} distinct triples with clauses out of C(36,3)={36*35*34//6}")
print(f"m=37: {len(triple_partic_m37)} distinct triples with clauses out of C(37,3)={37*36*35//6}")

# How many bits are forbidden per triple?
for label, tp, m in [("m=36", triple_partic_m36, 36), ("m=37", triple_partic_m37, 37)]:
    bit_counts = Counter()
    for (a, b, c) in tp:
        n_cl = tp[(a, b, c)]
        bit_counts[n_cl] += 1
    print(f"{label}: per-triple clause count distribution: {dict(sorted(bit_counts.items()))}")

# 7. Graph invariants comparison
print("\n=== Graph invariant comparison ===")
for label, edges, m in [("m=36", edges_m36, 36), ("m=37", edges_m37, 37)]:
    adj = defaultdict(set)
    for u, v in edges:
        adj[u].add(v); adj[v].add(u)
    # Number of chordless cycles? Just check cycle lengths
    visited = [False]*m
    cycles = []
    for v in range(m):
        if not visited[v]:
            cyc = [v]; visited[v] = True
            prev = v; cur = list(adj[v])[0]
            while cur != v:
                cyc.append(cur); visited[cur] = True
                nxt = list(adj[cur])[0] if list(adj[cur])[0] != prev else list(adj[cur])[1]
                prev, cur = cur, nxt
            cycles.append(cyc)
    print(f"  {label}: {len(cycles)} cycle(s)")
    for i, cyc in enumerate(cycles):
        spans = [min(abs(cyc[k]-cyc[(k+1)%len(cyc)]), m-abs(cyc[k]-cyc[(k+1)%len(cyc)])) for k in range(len(cyc))]
        # Sum of spans
        print(f"    Cycle {i}: len={len(cyc)}, sum_spans={sum(spans)}, mean_span={sum(spans)/len(spans):.1f}")

# 8. What happens if we take the m=36 edges but on a 37-vertex grid? 
# (just for theoretical comparison)
print("\n=== Theoretical: m=36 edges on m=37 grid (same span pattern) ===")
# Scale the spans: if edge (a,b) has span s in m=36 grid, 
# the equivalent edge in m=37 would be at distance s (mod 37)
# This is a thought experiment to compare constraint structure
spans_m36 = [min(abs(u-v), 36-abs(u-v)) for u,v in edges_m36]
spans_m37 = [min(abs(u-v), 37-abs(u-v)) for u,v in edges_m37]
print(f"m=36 spans: min={min(spans_m36)}, max={max(spans_m36)}, mean={sum(spans_m36)/len(spans_m36):.1f}")
print(f"m=37 spans: min={min(spans_m37)}, max={max(spans_m37)}, mean={sum(spans_m37)/len(spans_m37):.1f}")

# Mutuality: are edges from m=36 forming pairs with complementary spans?
print("\n=== Span pair analysis (edges that share a vertex) ===")
for label, edges, m in [("m=36", edges_m36, 36), ("m=37", edges_m37, 37)]:
    adj = defaultdict(list)
    for eidx, (u, v) in enumerate(edges):
        adj[u].append((eidx, v)); adj[v].append((eidx, u))
    span_pairs = []
    for v in range(m):
        nbs = adj[v]
        if len(nbs) == 2:
            e1, nb1 = nbs[0]
            e2, nb2 = nbs[1]
            s1 = min(abs(v - nb1), m - abs(v - nb1))
            s2 = min(abs(v - nb2), m - abs(v - nb2))
            span_pairs.append((s1, s2))
    # Count span pair patterns
    pair_hist = Counter(span_pairs)
    print(f"  {label}: {len(pair_hist)} distinct span-pair types at vertices")
    for pair, cnt in sorted(pair_hist.items()):
        print(f"    ({pair[0]},{pair[1]}): {cnt} vertices")

# Summary
print("\n\n=== KEY FINDINGS ===")
print(f"m=36: {len(cl_m36)} clauses, SAT (found in 0.005s)")
print(f"m=37: {len(cl_m37)} clauses, UNSAT (proven optimal 17 violations)")
print(f"m=36 has span-1 edges (adjacent vertices in cycle)")
print(f"m=37 has no span-1 edges, min span = 4")
print(f"m=36 total triples forbidden: {len(triple_partic_m36)}")
print(f"m=37 total triples forbidden: {len(triple_partic_m37)}")
