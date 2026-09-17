#!/usr/bin/env python3
"""
Deep analysis of best72 Hamiltonian cycle for m=37.
Reconstructs cycle ordering, analyzes span distribution,
compares with known solutions, and tests algebraic constructions.
"""

import json
import math
from collections import defaultdict, Counter

M = 37

# best72 edges from solver_theory_m37_long.json
best72_edges = [
    [15,34], [10,24], [3,23], [7,28], [2,23], [8,25], [16,30],
    [7,18], [3,29], [9,35], [11,17], [9,32], [12,36], [6,15],
    [6,31], [14,36], [1,19], [8,24], [20,25], [4,19], [12,27],
    [21,33], [5,35], [13,29], [1,27], [5,22], [21,32], [20,26],
    [0,33], [16,28], [14,22], [13,26], [10,17], [11,18], [2,34],
    [0,30], [4,31]
]

def c2_dist(a, b, m=M):
    """Circular distance in Z/mZ"""
    d = abs(a - b) % m
    return min(d, m - d)

def reconstruct_cycle(edges):
    """Reconstruct Hamiltonian cycle from edge list (sorted pairs)."""
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    
    # Verify all degree 2
    for v, nbs in adj.items():
        assert len(nbs) == 2, f"Vertex {v} has degree {len(nbs)}"
    
    # Trace cycle starting from vertex 0
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
    
    # Check all vertices
    assert len(cycle) == 37, f"Cycle length {len(cycle)}, expected 37"
    assert len(set(cycle)) == 37, "Not all vertices unique"
    return cycle

def cycle_spans(cycle, m=M):
    """Compute the span of each edge in the cycle (as circular distance)."""
    spans = []
    for i in range(len(cycle)):
        a = cycle[i]
        b = cycle[(i + 1) % len(cycle)]
        spans.append(c2_dist(a, b, m))
    return spans

def edge_differences(cycle, m=M):
    """Compute the signed difference d_i = (v_{i+1} - v_i) mod m,
    choosing the representation with |d_i| <= m//2."""
    diffs = []
    for i in range(len(cycle)):
        a = cycle[i]
        b = cycle[(i + 1) % len(cycle)]
        d = (b - a) % m
        if d > m // 2:
            d = d - m
        diffs.append(d)
    return diffs

# ============================================================
# 1. RECONSTRUCT CYCLE
# ============================================================
print("=" * 70)
print("1. BEST72 HAMILTONIAN CYCLE RECONSTRUCTION")
print("=" * 70)

cycle = reconstruct_cycle(best72_edges)
print(f"Cycle order: {cycle}")
print(f"Length: {len(cycle)}")

spans = cycle_spans(cycle)
print(f"\nEdge spans: {spans}")
print(f"Min span: {min(spans)}")
print(f"Max span: {max(spans)}")
print(f"Mean span: {sum(spans)/len(spans):.4f}")
print(f"Median span: {sorted(spans)[len(spans)//2]}")

# span histogram
span_hist = Counter(spans)
print(f"\nSpan histogram:")
for s in sorted(span_hist.keys()):
    print(f"  {s:2d}: {span_hist[s]}")

# Count how many spans are "small" (< threshold)
for t in [6, 7, 8, 9, 10, 11, 12, 13]:
    cnt = sum(1 for s in spans if s < t)
    print(f"  spans < {t:2d}: {cnt} ({100*cnt/37:.1f}%)")

# ============================================================
# 2. DIFFERENCES (signed steps)
# ============================================================
print("\n" + "=" * 70)
print("2. SIGNED EDGE DIFFERENCES (permutation steps)")
print("=" * 70)

diffs = edge_differences(cycle)
print(f"Signed diffs: {diffs}")
diff_hist = Counter(diffs)
print(f"Step histogram (step -> count):")
for d in sorted(diff_hist.keys()):
    print(f"  {d:+3d}: {diff_hist[d]}")

# What if we sort by absolute difference?
abs_diffs = [abs(d) for d in diffs]
print(f"\nAbsolute step sizes: {abs_diffs}")
abs_hist = Counter(abs_diffs)
print(f"Absolute step histogram:")
for d in sorted(abs_hist.keys()):
    print(f"  {d:2d}: {abs_hist[d]}")

# ============================================================
# 3. IS THERE A PATTERN IN THE CYCLE?
# ============================================================
print("\n" + "=" * 70)
print("3. PATTERN ANALYSIS")
print("=" * 70)

# Check if cycle ordering follows some function f(i) = cycle[i]
# Try to detect arithmetic or geometric patterns

# "Unwrap" by looking at the order in which vertices appear
positions = {v: i for i, v in enumerate(cycle)}
print(f"Linear positions (vertex -> index in cycle):")
for v in sorted(positions.keys()):
    print(f"  {v:2d} -> {positions[v]:2d}")

# Check if there's a pattern in the sequence of first differences
# diff[i] = (positions[(v+1)%37] - positions[v]) mod 37
# This tells us the "ordering" pattern in terms of vertex labels
print("\nOrder of edges when edges are sorted by vertex label:")
sorted_edges_by_u = sorted(best72_edges, key=lambda e: (e[0], e[1]))
for e in sorted_edges_by_u:
    print(f"  ({e[0]:2d}, {e[1]:2d})  span={c2_dist(*e):2d}")

# ============================================================
# 4. COMPARE WITH m <= 36 SOLUTIONS
# ============================================================
print("\n" + "=" * 70)
print("4. COMPARISON WITH m <= 36 SOLUTIONS")
print("=" * 70)

# Look at existing solution files
import glob, os
sol_dir = os.path.join(os.path.dirname(__file__), "results", "solutions")
sol_files = sorted(glob.glob(os.path.join(sol_dir, "*.json")))

for sf in sol_files:
    try:
        with open(sf) as f:
            sol = json.load(f)
        m = sol.get('m', 0)
        if m >= 37:
            continue
        sol_edges = sol.get('edges', [])
        sol_cycle = reconstruct_cycle(sol_edges)
        sol_spans = cycle_spans(sol_cycle, m=m)
        sol_span_hist = Counter(sol_spans)
        min_s = min(sol_spans)
        
        # Compute adjacency count (edges that are adjacent in the cycle
        # whose vertex labels are also adjacent mod m)
        adj_count = sum(1 for s in sol_spans if s <= 2)
        
        print(f"  m={m:2d}: min_span={min_s:2d}, "
              f"adj_edges(span<=2)={adj_count:2d}, "
              f"span_hist={dict(sorted(sol_span_hist.items()))}")
    except Exception as e:
        print(f"  Error reading {sf}: {e}")

print("\n" + "=" * 70)
print("5. BEST72 VS m=35/36 span comparison")
print("=" * 70)

# ============================================================
# 5. RESTRICTION TO SUB-graphs
# ============================================================
print("\n" + "=" * 70)
print("5. EDGE COMPLEMENT ANALYSIS")
print("=" * 70)

# What are the MISSING spans? i.e., which C2 distances don't appear?
all_possible_spans = list(range(1, 19))  # 1..18 for m=37 (since 18 = 37//2)
present_spans = set(spans)
missing_spans = [s for s in all_possible_spans if s not in present_spans]
print(f"Present spans: {sorted(present_spans)}")
print(f"Missing spans: {missing_spans}")
print(f"Missing: {len(missing_spans)} of {len(all_possible_spans)} spans")

# ============================================================
# 6. DOES THE CYCLE SATISFY ANY NUMBER-THEORETIC PROPERTY?
# ============================================================
print("\n" + "=" * 70)
print("6. NUMBER-THEORETIC ANALYSIS")
print("=" * 70)

# Test if cycle corresponds to π(i) = i + k (mod 37) for some k
print("\n6a. Arithmetic progression tests (π(i) = i + k mod 37):")
for k in range(1, 19):
    # This would produce spans of size min(k, 37-k) = min(k, 37-k)
    # for ALL edges, resulting in a single span value
    span = min(k, M - k)
    # All edges have the same span
    # This can't match best72 which has varying spans
    print(f"    k={k:2d}: uniform span={span:2d} -- cannot match best72 (non-uniform)")

# Test if cycle is the image of a smaller solution under some mapping
print("\n6b. Checking if cycle is a 'good' Cayley graph cycle (generated by a set):")
# A cycle (spanning 1-factor) in a circulant graph C_m(S)
# where edges are {i, i+s} for s in S.
# Best72 uses multiple different spans, so it's not a pure circulant.
# But maybe it's {i, π(i)} where π is a permutation with special properties.

# Check: are the spans related to quadratic residues mod 37?
print("\n6c. Quadratic residues mod 37:")
qr = {i for i in range(1, 37) if pow(i, (37-1)//2, 37) == 1}
print(f"    QR: {sorted(qr)}")
qr_spans = [s for s in spans if s in qr or (M-s) in qr]
print(f"    Spans that are QR (or complement): {len(qr_spans)}/{len(spans)}")

# Non-residues
nqr = {i for i in range(1, 37) if pow(i, (37-1)//2, 37) == 36}
print(f"    Non-QR: {sorted(nqr)}")

# ============================================================
# 7. SPAN "COVERAGE" ANALYSIS
# ============================================================
print("\n" + "=" * 70)
print("7. SPAN COVERAGE PATTERN")
print("=" * 70)

# For each vertex, what spans does it participate in?
print("\nPer-vertex span participation:")
v_spans = defaultdict(list)
for i in range(len(cycle)):
    v = cycle[i]
    s = spans[i]
    v_spans[v].append(s)
for v in sorted(v_spans.keys()):
    print(f"  v={v:2d}: spans={v_spans[v]}")

# ============================================================
# 8. SUMMARY OF KEY PROPERTIES
# ============================================================
print("\n" + "=" * 70)
print("8. SUMMARY OF KEY PROPERTIES")
print("=" * 70)
print(f"""
best72 Hamiltonian cycle (m=37):
- Single cycle visiting all 37 vertices
- Min edge span: {min(spans)} (no adjacent or near-adjacent edges)
- Max edge span: {max(spans)}
- Mean edge span: {sum(spans)/len(spans):.2f}
- Number of distinct spans: {len(set(spans))}
- Missing spans (C2 distances not used): {missing_spans}
- Span distribution: {dict(sorted(Counter(spans).items()))}
""")

# ============================================================
# 9. ALGEBRAIC CONSTRUCTIONS
# ============================================================
print("=" * 70)
print("9. ALGEBRAIC CONSTRUCTIONS — PLACEHOLDER")
print("=" * 70)
print("""
Constructions will test:
  A) Arithmetic cycles: π(i) = i + k (mod 37)
  B) Affine cycles: π(i) = a*i + b (mod 37)  
  C) Permutation derived from QR structure
  D) Reverse-engineer π from best72 ordering
""")
