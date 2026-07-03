#!/usr/bin/env python3
"""
Preparation for Direction 1: Extract common structure from n=12 solutions
and predict the threshold for even n.
"""
import csv
from collections import Counter, defaultdict

N = 12
cx_times2 = N - 1  # even
cy_times2 = N - 1

def get_dist(c, r):
    dx = 2*c - cx_times2
    dy = 2*r - cy_times2
    return dx*dx + dy*dy

# ============================================================================
# PART 1: Universal structure analysis of 28 n=12 solutions
# ============================================================================
print("=" * 70)
print("PART 1: Universal Structure of n=12 Missing-Center Solutions")
print("=" * 70)

# Read solutions
solutions = []
with open('sols_n12.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sol = {}
        for r in range(N):
            c1 = int(row[f'r{r}c1'])
            c2 = int(row[f'r{r}c2'])
            sol[r] = (c1, c2)
        solutions.append(sol)

print(f"\nLoaded {len(solutions)} base solutions (mirrored to 52)")

# 1.1 Universal points: which (row,col) appear in ALL solutions?
position_counts = Counter()
for sol in solutions:
    seen = set()
    for r, (c1, c2) in sol.items():
        seen.add((r, c1))
        seen.add((r, c2))
    for pos in seen:
        position_counts[pos] += 1

universal_positions = [p for p, c in position_counts.items() if c == len(solutions)]
print(f"\nPositions used in EVERY solution ({len(universal_positions)}):")
for r, c in sorted(universal_positions):
    d = get_dist(c, r)
    print(f"  ({r},{c})  d={d}")

# 1.2 Universal distance rings
ring_counts = defaultdict(Counter)  # d -> {(row,col): count}
for sol in solutions:
    seen_rings = defaultdict(set)
    for r, (c1, c2) in sol.items():
        d1, d2 = get_dist(c1, r), get_dist(c2, r)
        seen_rings[d1].add((r, c1))
        seen_rings[d2].add((r, c2))
    for d, pts in seen_rings.items():
        for pt in pts:
            ring_counts[d][pt] += 1

# Rings used in ALL solutions
universal_rings = []
for d in sorted(ring_counts.keys()):
    max_count = max(ring_counts[d].values())
    if max_count == len(solutions):
        pts_str = ", ".join(f"({r},{c})" for (r,c) in sorted(ring_counts[d].keys(), 
                          key=lambda x: (x[0],x[1])))
        universal_rings.append((d, pts_str))

print(f"\nDistance rings used in ALL {len(solutions)} solutions:")
for d, pts_str in universal_rings:
    print(f"  d={d:4d}: {pts_str}")

# 1.3 Universal column-cycle edges
edge_counts = Counter()
for sol in solutions:
    edges = []
    for r, (c1, c2) in sol.items():
        edges.append(tuple(sorted((c1, c2))))
    for e in set(edges):
        edge_counts[e] += 1

print(f"\nColumn pairs that appear in many solutions:")
for (c1, c2), count in edge_counts.most_common(15):
    d1a = get_dist(c1, [r for r in range(N) for (c1p,c2p) in [sol.get(r,(0,0))] 
                         if False][:1])  # quick hack
    print(f"  ({c1:2d},{c2:2d})  d-rows: unknown  appears in {count}/{len(solutions)} solutions")

# Better: show which solutions share which edges
print(f"\nColumn pair frequency distribution:")
freq_dist = Counter(edge_counts.values())
for freq, count in sorted(freq_dist.items()):
    print(f"  {count} pairs appear in exactly {freq}/{len(solutions)} solutions")

# 1.4 Row-to-column group mapping pattern
print(f"\n\nRow x² values for n={N}:")
for r in range(N):
    x2 = (2*r - (N-1))**2
    print(f"  row {r:2d}: x²={x2:4d}")

print(f"\nColumn x² values for n={N}:")
for c in range(N):
    x2 = (2*c - (N-1))**2
    print(f"  col {c:2d}: x²={x2:4d}")

# ============================================================================
# PART 2: Predict even-n threshold using ring analysis
# ============================================================================
print("\n" + "=" * 70)
print("PART 2: Even-n Threshold Prediction (n/R ratio analysis)")
print("=" * 70)

def even_ring_count(n):
    """Count distinct distance rings for even n"""
    sq = [(2*c - (n-1))**2 for c in range(n)]
    rings = set()
    for r in range(n):
        for c in range(n):
            rings.add(sq[r] + sq[c])
    return len(rings), sorted(set(sq))

print(f"\n{'n':>3} {'x² count':>10} {'Rings':>7} {'2n':>4} {'2R':>4} {'n/R':>7} {'Flex%':>7} {'New x²':>12}")
print("-" * 65)

prev_rings = 0
for n in range(2, 21, 2):
    n_rings, x2_vals = even_ring_count(n)
    max_cap = 2 * n_rings
    pts = 2 * n
    ratio = n / n_rings
    flexibility = (max_cap - pts) / max_cap * 100
    new_x2 = x2_vals[-1] if x2_vals else ""
    
    # Predict: is missing-center POSSIBLE?
    status = ""
    if ratio >= 1.0:
        status = "IMPOSSIBLE (n ≥ R)"
    elif ratio > 0.70:
        status = "likely IMPOSSIBLE (collinearity)"
    elif n <= 10 and ratio > 0.60:
        status = "n<12 threshold"
    elif n >= 12:
        status = "POSSIBLE ✓"
    
    print(f"{n:>3} {len(x2_vals):>10} {n_rings:>7} {pts:>4} {max_cap:>4} {ratio:>7.3f} {flexibility:>6.1f}% {f'+{new_x2}':>12}  {status}")

print()
print("PREDICTION: n=14 should have missing-center solutions")
print("            If n=14 has 0, then the threshold is EXACTLY at n=12")
print("            If n=14 has >0, then all even n≥12 may have missing-center")

# ============================================================================
# PART 3: The x² = 121 theory (why n=12)
# ============================================================================
print("\n" + "=" * 70)
print("PART 3: x²=121 — The 'Magic' Value That Enables n=12")
print("=" * 70)

print("""
For even n, distance rings are sums of odd squares: {1², 3², 5², ..., (n-1)²}.

n=10 has x² values: {1, 9, 25, 49, 81}  → 14 rings
n=12 adds  x²=121  →  5 new rings: 122, 146, 170, 202, 242
n=14 adds  x²=169  →  ~6 new rings

The key question: why does adding x²=121 suddenly enable missing-center,
while adding x²=169 at n=14 might not? The answer lies in how the new
rings interact with the collinearity constraint.

For x²=121 (n=12), the new rows/columns are at positions 0 and 11.
These are the outermost rows/columns. The new rings involve the corners
and edges of the grid, which may be less constrained by collinearity.

If n=14 also works, then the pattern is: every even n ≥ 12 works.
If n=14 doesn't work, then the n=12 threshold is a one-off fluke.
""")

# Show the distribution of the 5 new rings across the 28 solutions
print("Usage of n=12's 5 new rings (from x²=121) in the 28 solutions:")
new_rings = [122, 146, 170, 202, 242]
for d in new_rings:
    cnt_0, cnt_1, cnt_2 = 0, 0, 0
    for sol in solutions:
        pts_at_d = 0
        for r, (c1, c2) in sol.items():
            if get_dist(c1, r) == d: pts_at_d += 1
            if get_dist(c2, r) == d: pts_at_d += 1
        if pts_at_d == 0: cnt_0 += 1
        elif pts_at_d == 1: cnt_1 += 1
        else: cnt_2 += 1
    total_pts = sum(sum(1 for r,(c1,c2) in sol.items() if get_dist(c1,r)==d or get_dist(c2,r)==d) for sol in solutions)
    print(f"  d={d:4d}: 0pts×{cnt_0}, 1pt×{cnt_1}, 2pts×{cnt_2}  (total {total_pts} pts across all sols)")

# ============================================================================
# PART 4: Common row-pair template
# ============================================================================
print("\n" + "=" * 70)
print("PART 4: Row-pair template — which columns co-occur in each row?")
print("=" * 70)

# For each row, which other column does it pair with?
# Across all solutions, for each row, find the most common column partner
row_partners = defaultdict(Counter)
for sol in solutions:
    for r, (c1, c2) in sol.items():
        row_partners[r][c1] += 1
        row_partners[r][c2] += 1

# But that's not quite right — we need partners, not individual column counts
print(f"\nMost common column pairs per row across {len(solutions)} solutions:")
for r in range(N):
    pairs = Counter()
    for sol in solutions:
        c1, c2 = sol[r]
        pairs[tuple(sorted((c1, c2)))] += 1
    top = pairs.most_common(3)
    top_str = ", ".join(f"({a},{b})×{c}" for (a,b),c in top)
    print(f"  Row {r:2d}: {top_str}")
