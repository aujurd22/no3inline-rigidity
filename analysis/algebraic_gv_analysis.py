"""
algebraic_gv_analysis.py — 分析 3 个 cell 的 C4 提升产生共线的条件。

对 m=37, n=74，C4 orbit of (u,v)：
  (u,v), (73-v,u), (73-u,73-v), (v,73-u)

三个 cell (u1,v1),(u2,v2),(u3,v3) 的 12 个提升点中，
3 点共线 ⇔ 行列式=0 在某旋转组合下。

分析：何时 (u1,v1) 的某个旋转与 (u2,v2) 的某个旋转、(u3,v3) 的某个旋转共线？
"""
import sys
from itertools import combinations, product

M = 37
N = 74

# The 4 C4 rotations
def rot(p, r, n=N):
    x, y = p
    for _ in range(r):
        x, y = n - 1 - y, x
    return (x, y)

# All 4 rotations
def orbit(u, v):
    return [(u, v), (N-1-v, u), (N-1-u, N-1-v), (v, N-1-u)]

# Collinearity check for 3 points
def collinear(p1, p2, p3):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    return (x2-x1)*(y3-y1) == (y2-y1)*(x3-x1)

# For a triple of cells, check which rotation combos produce collinearity
def analyze_triple(u1, v1, u2, v2, u3, v3):
    """Return list of (r1,r2,r3) combos that produce collinearity."""
    bad = []
    for r1, r2, r3 in product(range(4), range(4), range(4)):
        p1 = rot((u1, v1), r1)
        p2 = rot((u2, v2), r2)
        p3 = rot((u3, v3), r3)
        if collinear(p1, p2, p3):
            bad.append((r1, r2, r3))
    return bad

# For a given cell (u,v), what is the "signature" of its orbit?
# Check: slope between pairs of orbit points
def orbit_slopes(u, v):
    """Compute slopes between all pairs of orbit points."""
    pts = orbit(u, v)
    slopes = []
    for i, j in combinations(range(4), 2):
        x1, y1 = pts[i]
        x2, y2 = pts[j]
        dx, dy = x2-x1, y2-y1
        # Canonical slope representation
        if dx == 0:
            slopes.append(('v', x1))  # vertical line at x
        elif dy == 0:
            slopes.append(('h', y1))  # horizontal line at y
        else:
            from math import gcd
            g = gcd(abs(dx), abs(dy))
            dx //= g
            dy //= g
            if dx < 0:
                dx, dy = -dx, -dy
            slopes.append((dx, dy))
    return slopes

# Test: for a specific pair of cells, which cross-orbit lines exist?
def cross_lines(u1, v1, u2, v2):
    """Lines connecting a point from orbit 1 to a point from orbit 2."""
    pts1 = orbit(u1, v1)
    pts2 = orbit(u2, v2)
    lines = set()
    for i, p1 in enumerate(pts1):
        for j, p2 in enumerate(pts2):
            if p1 == p2:
                continue
            # Line equation: (p2-p1) as direction
            dx, dy = p2[0]-p1[0], p2[1]-p1[1]
            from math import gcd
            g = gcd(abs(dx), abs(dy))
            dx //= g
            dy //= g
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            # Offset (cross product with some origin point)
            offset = p1[0]*dy - p1[1]*dx
            lines.add((dx, dy, offset))
    return lines

# For config_408 cells, compute how many collinear triples exist
# with at least one point from each of 3 cells' orbits (not orientation-specific)
print("=== Algebraic GV Analysis ===")
print(f"\nConfig 408 cells: 37 points")

with open("D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis\\results\\config_408_edges.json") as f:
    import json
    data = json.load(f)
edges = [tuple(e) for e in data["edges"]]

# Count GV (any-rotation collinearity per triple)
gv = 0
for i, j, k in combinations(range(37), 3):
    u1, v1 = edges[i]
    u2, v2 = edges[j]
    u3, v3 = edges[k]
    # Check if ANY rotation combo produces collinearity
    found = False
    for r1, r2, r3 in product(range(4), range(4), range(4)):
        if collinear(rot((u1,v1),r1), rot((u2,v2),r2), rot((u3,v3),r3)):
            found = True
            break
    if found:
        gv += 1

print(f"  GV (any-rotation collinearity): {gv}")
print(f"  Out of {37*36*35//6} = 7770 triples")
print(f"  Clean triples: {7770 - gv} ({100*(7770-gv)/7770:.1f}%)")

# Now analyze: what geometric patterns cause collinearity?
print(f"\n=== Analyzing collinearity patterns ===")

# For each bad triple, determine WHICH rotation combos are bad
bad_patterns = {}
for i, j, k in combinations(range(37), 3):
    u1, v1 = edges[i]
    u2, v2 = edges[j]
    u3, v3 = edges[k]
    bad = analyze_triple(u1, v1, u2, v2, u3, v3)
    if bad:
        n_bad = len(bad)
        bad_patterns[n_bad] = bad_patterns.get(n_bad, 0) + 1

print(f"\nDistribution of bad rotation combos per triple:")
for n in sorted(bad_patterns):
    print(f"  {n:3d} bad combos: {bad_patterns[n]:4d} triples")

# Total clauses from this
total_clauses = sum(n * c for n, c in bad_patterns.items())
print(f"\n  Total clauses (all orientations): {total_clauses}")
print(f"  Expected: 408 (when counting only OR clause per combo)")
print(f"  (Full enumerate_clauses should give 408 for config_408)")

# Key analysis: what rotation (r1,r2,r3) patterns are most common?
print(f"\n=== Most common rotation patterns ===")
from collections import Counter
pattern_counts = Counter()
for i, j, k in combinations(range(37), 3):
    u1, v1 = edges[i]
    u2, v2 = edges[j]
    u3, v3 = edges[k]
    for r1, r2, r3 in product(range(4), range(4), range(4)):
        if collinear(rot((u1,v1),r1), rot((u2,v2),r2), rot((u3,v3),r3)):
            pattern_counts[(r1, r2, r3)] += 1

print(f"  Top 10 rotation combos causing collinearity:")
for (r1, r2, r3), cnt in pattern_counts.most_common(10):
    print(f"    ({r1},{r2},{r3}): {cnt} triples")

print(f"\n=== Analysis complete ===")
print(f"  Bad triples (GV): {gv}")
print(f"  Total bad combos: {total_clauses}")
print(f"  These will become {total_clauses} clauses in enumerate_clauses")
print(f"  Each triple with {n_bad} bad combos contributes {n_bad} clauses")
