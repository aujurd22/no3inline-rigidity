#!/usr/bin/env python3
"""
Constructive analysis of best72 Hamiltonian cycle for m=37.
1. Verify clause count matches 470 for best72
2. Reverse-engineer the permutation π
3. Test algebraic constructions
4. Find better cycles
"""

import sys, os, json, math, time, random
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H
import solver_2factor_sat_pipeline as P

M = 37

# ── best72 edges ──────────────────────────────────────────────────────────────
best72_edges = [
    (15,34), (10,24), (3,23), (7,28), (2,23), (8,25), (16,30),
    (7,18), (3,29), (9,35), (11,17), (9,32), (12,36), (6,15),
    (6,31), (14,36), (1,19), (8,24), (20,25), (4,19), (12,27),
    (21,33), (5,35), (13,29), (1,27), (5,22), (21,32), (20,26),
    (0,33), (16,28), (14,22), (13,26), (10,17), (11,18), (2,34),
    (0,30), (4,31)
]
best72_edges = sorted(best72_edges)

# ── Utilities ─────────────────────────────────────────────────────────────────
def c2_dist(a, b, m=M):
    d = abs(a - b) % m
    return min(d, m - d)

def edges_from_cycle(cycle):
    """Given a permutation/list ordering of vertices, return sorted edges."""
    m = len(cycle)
    edges = []
    for k in range(m):
        a, b = cycle[k], cycle[(k + 1) % m]
        u, v = (a, b) if a <= b else (b, a)
        edges.append((u, v))
    return sorted(edges)

def edges_from_perm(pi):
    """Given successor function pi: i -> next vertex, return sorted edges."""
    m = len(pi)
    edges = []
    for i in range(m):
        a, b = i, pi[i]
        u, v = (a, b) if a <= b else (b, a)
        edges.append((u, v))
    return sorted(edges)

def cycle_from_edges(edges):
    """Reconstruct cycle ordering from edge list."""
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
    
    assert len(cycle) == len(edges), f"Cycle length {len(cycle)} != {len(edges)}"
    return cycle

def pi_from_cycle(cycle):
    """Return successor function pi: i -> next vertex in cycle."""
    m = len(cycle)
    pi = {}
    for k in range(m):
        pi[cycle[k]] = cycle[(k + 1) % m]
    return pi

def span_stats(edges, m=M):
    """Compute span statistics (C2 distance)."""
    spans = []
    for u, v in edges:
        spans.append(c2_dist(u, v, m))
    span_hist = Counter(spans)
    return {
        "min": min(spans), "max": max(spans),
        "mean": sum(spans) / len(spans),
        "hist": dict(sorted(span_hist.items())),
        "n_span_1": sum(1 for s in spans if s == 1),
        "n_span_2": sum(1 for s in spans if s <= 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# PART 1: VERIFY best72
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("PART 1: VERIFY best72 CLAUSE COUNT")
print("=" * 70)

cycle_best72 = cycle_from_edges(best72_edges)
pi_best72 = pi_from_cycle(cycle_best72)

n72 = H.count_clauses_fast(M, best72_edges)
print(f"best72 clause count: {n72}")

s72 = span_stats(best72_edges)
print(f"best72 spans: min={s72['min']} max={s72['max']} mean={s72['mean']:.2f}")
print(f"  span=1 count: {s72['n_span_1']}")
print(f"  span<=2 count: {s72['n_span_2']}")
print(f"  hist: {s72['hist']}")

# Verify the 2factor_analysis claim of min=5
# Using ABSOLUTE difference, not circular
abs_spans = [abs(u-v) for u,v in best72_edges]
print(f"\nUsing ABSOLUTE difference |u-v|:")
print(f"  min={min(abs_spans)} max={max(abs_spans)} mean={sum(abs_spans)/len(abs_spans):.2f}")
print(f"  |u-v| values: {sorted(abs_spans)}")

print(f"\nCycle order: {cycle_best72}")
print(f"Cycle length: {len(cycle_best72)}")

# ══════════════════════════════════════════════════════════════════════════════
# PART 2: REVERSE ENGINEER π — check for algebraic patterns
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 2: REVERSE-ENGINEER THE PERMUTATION")
print("=" * 70)

# Compute π(i) - i (mod 37)
print("\nSuccessor differences π(i) - i (mod 37):")
pi_diffs = [(pi_best72[i] - i) % M for i in range(M)]
for i in range(M):
    d = pi_diffs[i]
    d_signed = d if d <= M//2 else d - M
    print(f"  π({i:2d}) = {pi_best72[i]:2d}   diff={d:2d}  signed={d_signed:+3d}")

diff_counts = Counter(pi_diffs)
print(f"\nDifference histogram (mod 37 value -> count):")
for d in sorted(diff_counts.keys()):
    print(f"  {d:2d} ({d if d <= M//2 else d-M:+3d}): {diff_counts[d]}")

# Check if best72's SIGNED differences follow a pattern
signed_diffs = [d if d <= M//2 else d - M for d in pi_diffs]
print(f"\nSigned differences (as array): {signed_diffs}")

# ══════════════════════════════════════════════════════════════════════════════
# PART 3: ALGEBRAIC CONSTRUCTIONS
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 3: ALGEBRAIC CONSTRUCTIONS")
print("=" * 70)

results = []

# 3a: Arithmetic cycles: π(i) = i + k (mod 37)
print("\n--- 3a: Arithmetic cycles π(i) = i + k (mod 37) ---")
for k in range(1, 19):
    pi = [(i + k) % M for i in range(M)]
    edges = edges_from_perm(pi)
    nc = H.count_clauses_fast(M, edges)
    ss = span_stats(edges)
    results.append(("arithmetic", k, nc, ss))
    print(f"  k={k:2d}: {nc:5d} clauses, min_span={ss['min']}, "
          f"span_1={ss['n_span_1']}, span<=2={ss['n_span_2']}")

# 3b: Affine cycles: π(i) = a*i + b (mod 37)
# Must be a permutation, so gcd(a, 37) = 1 (since 37 is prime, a ≠ 0)
print("\n--- 3b: Affine cycles π(i) = a*i + b (mod 37) ---")
for a in range(1, 37):
    if math.gcd(a, M) != 1:
        continue
    for b in range(1):
        # Try with b=0 first
        pi = [(a * i + b) % M for i in range(M)]
        edges = edges_from_perm(pi)
        nc = H.count_clauses_fast(M, edges)
        ss = span_stats(edges)
        results.append(("affine", f"a={a},b={b}", nc, ss))
        if nc < 2000:
            print(f"  a={a:2d},b={b}: {nc:5d} clauses, min_span={ss['min']}")
    # Only show best for each a
all_affine = [r for r in results if r[0] == "affine"]
best_affine = min(all_affine, key=lambda x: x[2])
print(f"\n  Best affine: {best_affine[1]} → {best_affine[2]} clauses")

# 3c: Multiplication cycles: π(i) = a*i (mod 37), then connect in order
# This gives edges {a^i, a^{i+1}} for a primitive root
print("\n--- 3c: Multiplicative cycles (primitive root) ---")
for a in range(2, M):
    if math.gcd(a, M) != 1:
        continue
    # Generate the orbit: [1, a, a^2, ..., a^36]
    orbit = [1]
    val = 1
    for _ in range(M - 1):
        val = (val * a) % M
        orbit.append(val)
    if len(set(orbit)) == M:
        # Full cycle
        edges = edges_from_cycle(orbit)
        nc = H.count_clauses_fast(M, edges)
        ss = span_stats(edges)
        results.append(("multiplicative", f"a={a}", nc, ss))
        print(f"  a={a:2d}: {nc:5d} clauses, min_span={ss['min']}")

# 3d: Quadratic residue based
print("\n--- 3d: Quadratic residue based cycles ---")
# QR set mod 37
qr = {i for i in range(1, M) if pow(i, (M-1)//2, M) == 1}
nqr = {i for i in range(1, M) if pow(i, (M-1)//2, M) == M-1}
print(f"  QR count: {len(qr)}, NQR count: {len(nqr)}")
# Could construct cycle by alternating QR/NQR or ordering by QR classes
qr_list = sorted(qr)
nqr_list = sorted(nqr)

# Cycle: all QR then all NQR
cycle_qr_first = qr_list + nqr_list + [0]
cycle_qr_first = cycle_qr_first[:M]  # trim
edges = edges_from_cycle(cycle_qr_first)
try:
    nc = H.count_clauses_fast(M, edges)
    results.append(("qr_ordered", "qr_first", nc, {}))
    print(f"  QR-first cycle: {nc} clauses")
except Exception as e:
    print(f"  QR-first cycle: ERROR {e}")

# 3e: Try to match best72's span distribution
# best72 has: span=4(1), 5(2), 6(2), 7(4), 8(1), 9(1), 10(1), 11(5), 12(3),
#             13(2), 14(3), 15(3), 16(4), 17(3), 18(2)
# Key insight: all spans >= 4, no span=1,2,3
print("\n--- 3e: Constrained random cycles (min_span=4,5,6) ---")
for min_span in [4, 5, 6]:
    rng = random.Random(42)
    best_nc = float("inf")
    best_e = None
    for trial in range(200):
        # Try to generate a cycle with min_span constraint
        for _ in range(1000):
            edges = H.random_hamiltonian_cycle(M, rng)
            ok = all(c2_dist(u, v) >= min_span for u, v in edges)
            if ok:
                break
        nc = H.count_clauses_fast(M, edges)
        if nc < best_nc:
            best_nc = nc
            best_e = edges
    ss = span_stats(best_e)
    results.append(("constrained_random", f"min_span={min_span}", best_nc, ss))
    print(f"  min_span={min_span}: best={best_nc} clauses (over 200 trials)")

# ══════════════════════════════════════════════════════════════════════════════
# PART 4: COMPOSITE CYCLES — combine two permutations with 2-switches
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("PART 4: MUTATION FROM best72")
print("=" * 70)

# Try mutating best72 with increasing number of 2-switches
rng = random.Random(12345)
for n_swaps in [1, 2, 3, 5, 10]:
    best_nc = float("inf")
    for trial in range(50):
        edges = H.mutate_cycle(best72_edges, rng, n_swaps=n_swaps)
        nc = H.count_clauses_fast(M, edges)
        if nc < best_nc:
            best_nc = nc
    print(f"  {n_swaps:2d} swaps: best={best_nc} clauses")

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("SUMMARY: ALL CONSTRUCTIONS TESTED")
print("=" * 70)

# Sort by clause count
results.sort(key=lambda x: x[2])
print(f"\n{'Rank':<5} {'Type':<18} {'Params':<20} {'Clauses':<8} {'MinSpan':<8}")
print("-" * 60)
for rank, (typ, params, nc, ss) in enumerate(results):
    ms = ss.get("min", "?")
    print(f"{rank+1:<5} {typ:<18} {str(params):<20} {nc:<8} {ms:<8}")

print(f"\nBest72 reference: {n72} clauses")

# Check if any construction beat best72
best_nc = min(r[2] for r in results)
if best_nc < n72:
    print(f"\n*** BREAKTHROUGH: Found cycle with {best_nc} clauses (best72 has {n72}) ***")
    best_result = min(results, key=lambda x: x[2])
    print(f"    Type: {best_result[0]}, Params: {best_result[1]}")
else:
    print(f"\nBest found: {best_nc} clauses (best72: {n72})")
    gap = best_nc - n72
    print(f"Gap: {gap} clauses above best72")
