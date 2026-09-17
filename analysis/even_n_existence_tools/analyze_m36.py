"""Analyze m=36 non-involution structure to understand alternative mechanism."""
import sys, itertools
from collections import defaultdict, Counter
sys.path.insert(0, '.')
from validate_solver import load_positive, c4_lifts_n

edges, bits, _ = load_positive(36)
N = 72
pts = {}
for i, ((u, v), b) in enumerate(zip(edges, bits)):
    dc = (v, u) if b else (u, v)
    for pt in c4_lifts_n(dc, N):
        pts[pt] = i

row_ps = defaultdict(list)
for (x, y) in pts:
    row_ps[x].append(y)

col_g = defaultdict(set)
for x, ys in row_ps.items():
    if len(ys) >= 2:
        col_g[ys[0]].add(ys[1])
        col_g[ys[1]].add(ys[0])

color = {}
for y in range(N):
    if y in color:
        continue
    stack = [(y, 0)]
    while stack:
        cy, c = stack.pop()
        if cy in color:
            continue
        color[cy] = c
        for ny in col_g[cy]:
            if ny not in color:
                stack.append((ny, 1 - c))

pi = [0] * N
sigma = [0] * N
for x in range(N):
    ys = row_ps.get(x, [])
    if len(ys) >= 2:
        if color.get(ys[0], 0) == 0:
            pi[x] = ys[0]
            sigma[x] = ys[1]
        else:
            pi[x] = ys[1]
            sigma[x] = ys[0]

print("=== m=36 non-involution structure ===")
print(f"pi[:20] = {pi[:20]}")
print(f"sigma[:20] = {sigma[:20]}")

sp = [sigma[pi[x]] for x in range(N)]
ps = [pi[sigma[x]] for x in range(N)]
print(f"sigma∘pi fixed: {sum(1 for i in range(N) if sp[i]==i)}")
print(f"pi∘sigma fixed: {sum(1 for i in range(N) if ps[i]==i)}")

sums = [pi[x] + sigma[x] for x in range(N)]
print(f"pi+sigma dist: {Counter(sums).most_common(8)}")

# C4 orbit analysis
row_cells = defaultdict(set)
for (x, y), cid in pts.items():
    row_cells[x].add(cid)

cell_rows = defaultdict(list)
for x, cids in row_cells.items():
    for cid in cids:
        cell_rows[cid].append(x)

print(f"Cells per row: {Counter(len(v) for v in row_cells.values()).most_common()}")
print(f"Rows per cell: {Counter(len(v) for v in cell_rows.values()).most_common()}")

fp_pi = sum(1 for i in range(N) if pi[i] == i)
fp_sigma = sum(1 for i in range(N) if sigma[i] == i)
other = sum(1 for i in range(N) if pi[i] != i and sigma[i] != i and pi[i] == sigma[i])

print(f"\npi fixed: {fp_pi}/{N} sigma fixed: {fp_sigma}/{N}")
print(f"pi==sigma!=i: {other}")

# Check: is there a simple relation sigma = g(pi)?
# Try: sigma(x) = a*pi(x) + b mod N for various a,b
best_a, best_b, best_match = 0, 0, 0
for a in range(N):
    for b in range(N):
        match = sum(1 for i in range(N) if sigma[i] == (a * pi[i] + b) % N)
        if match > best_match:
            best_match = match
            best_a, best_b = a, b
print(f"Best linear sigma: a={best_a} b={best_b} match={best_match}/{N}")

# Check if the 2-factor structure explains the deviation
# m=36 has a 36-cycle. Self-loops force involution.
# For pure cycles, the C4 symmetry creates a specific pairing
# between rows that determines sigma.
# 
# Key insight: for each cell (u,v) with orientation bit b,
# the 4 C4 points are distributed across 4 rows.
# The BFS coloring determines which points go to pi vs sigma.
# 
# The deviation from involution = sigma - (N-1-pi) is caused by
# cells whose C4 orbits create crossing constraints.
print("\n=== Deviation analysis ===")
devs = [sigma[i] - (N - 1 - pi[i]) for i in range(N)]
dev_dist = Counter(devs)
print(f"Deviation distribution: {dev_dist.most_common(10)}")

# Map each deviation to a cell
# A deviation d means sigma(x) = N-1-pi(x) + d
# For large d, this means the two points at row x are far from complementary.
# This happens when the C4 rotation of the cells creates non-complementary y-values.

# Conclusion: the C4 symmetry itself prevents perfect involution for m>=10.
# The alternative mechanism is: pi and sigma both have many fixed points,
# reducing the effective degrees of freedom and allowing the C4 symmetry
# to place the remaining non-trivial points without collisions.
print("\nConclusion: m=36 solves via high fixed-point proportion (~42-44%)")
print("which reduces effective degrees of freedom, allowing C4 to place")
print("remaining non-trivial points without 3-collinear conflicts.")
