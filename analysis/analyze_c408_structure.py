"""
Deep structural analysis of config_408: what makes its GV=70 special?
We compare its coordinate distribution against random [28,9] configs.
"""
import json, random, math
from collections import Counter
from itertools import combinations

M = 37
N = 74

def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return pts

all_orbits_0 = {}
for u in range(M):
    for v in range(M):
        all_orbits_0[(u, v)] = c4_lift(u, v)

def check_12_fast(lifts):
    for i in range(12):
        xi, yi = lifts[i]
        for j in range(i + 1, 12):
            xj, yj = lifts[j]
            if xi == xj and yi == yj:
                continue
            dx1, dy1 = xj - xi, yj - yi
            for k in range(j + 1, 12):
                xk, yk = lifts[k]
                if xk == xi and yk == yi:
                    continue
                if dx1 * (yk - yi) == dy1 * (xk - xi):
                    return True
    return False

def gv(edges):
    total = 0
    for a in range(M):
        la = all_orbits_0[edges[a]]
        for b in range(a + 1, M):
            lb = all_orbits_0[edges[b]]
            for c in range(b + 1, M):
                lifts = la + lb + all_orbits_0[edges[c]]
                if check_12_fast(lifts):
                    total += 1
    return total

# Load config_408
with open("D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results/config_408_edges.json") as f:
    data = json.load(f)
c408 = [(min(u,v), max(u,v)) for u,v in data["edges"]]

print("=" * 60)
print("CONFIG_408 STRUCTURAL ANALYSIS")
print("=" * 60)

# 1. Coordinate analysis
i_vals = [e[0] for e in c408]
j_vals = [e[1] for e in c408]
all_vals = i_vals + j_vals

print(f"\n1. Coordinate ranges:")
print(f"   i: min={min(i_vals)} max={max(i_vals)}")
print(f"   j: min={min(j_vals)} max={max(j_vals)}")

# 2. Vertex degree distribution
deg = Counter(all_vals)
print(f"\n2. Vertex degree (should all be 2):")
print(f"   min={min(deg.values())} max={max(deg.values())}")
non_2 = [v for v, d in deg.items() if d != 2]
if non_2:
    print(f"   VIOLATIONS: {non_2}")
else:
    print(f"   All 37 vertices appear exactly twice ✓")

# 3. Difference d = |i-j| distribution
diffs = [abs(e[0] - e[1]) for e in c408]
diff_cnt = Counter(diffs)
print(f"\n3. |i-j| distribution:")
for d in sorted(diff_cnt):
    print(f"   |i-j|={d}: {diff_cnt[d]} cells")

# 4. Distinct coordinate values used  
unique_i = sorted(set(i_vals))
unique_j = sorted(set(j_vals))
unique_all = sorted(set(all_vals))
print(f"\n4. Distinct coordinates:")
print(f"   unique i values: {len(unique_i)}/{M}")
print(f"   unique j values: {len(unique_j)}/{M}")
print(f"   unique total: {len(unique_all)}/{M}")
print(f"   i values: {unique_i}")
print(f"   j values: {unique_j}")
missing = [v for v in range(M) if v not in set(all_vals)]
if missing:
    print(f"   MISSING vertices: {missing}")

# 5. Cycle decomposition: trace the graph
adj = {i: [] for i in range(M)}
for u,v in c408:
    adj[u].append(v)
    adj[v].append(u)

visited = set()
cycles = []
for start in range(M):
    if start in visited: continue
    cycle = [start]
    visited.add(start)
    prev, curr = start, adj[start][0]
    while curr != start:
        cycle.append(curr)
        visited.add(curr)
        nxt = adj[curr][0] if adj[curr][0] != prev else adj[curr][1]
        prev, curr = curr, nxt
    cycles.append(cycle)

print(f"\n5. Cycle decomposition:")
for c in sorted(cycles, key=len, reverse=True):
    print(f"   length {len(c)}: {c}")

# 6. GV analysis: count collinear triples by cycle membership
print(f"\n6. GV breakdown by triple type:")
gv_c408 = gv(c408)
print(f"   Total GV: {gv_c408}")

type_counts = Counter()
for a in range(M):
    for b in range(a+1, M):
        for c in range(b+1, M):
            la = all_orbits_0[c408[a]]
            lb = all_orbits_0[c408[b]]
            lc = all_orbits_0[c408[c]]
            if check_12_fast(la + lb + lc):
                # Classify by which cycles the cells belong to
                ca = 0 if a < 28 else 1  # 0=28-cycle, 1=9-cycle
                cb = 0 if b < 28 else 1
                cc = 0 if c < 28 else 1
                t = (ca + cb + cc)
                type_counts[t] = type_counts.get(t, 0) + 1

for t in sorted(type_counts):
    print(f"   {t} cells in 9-cycle: {type_counts[t]} collinear triples")

# 7. Compare with random [28,9] configs
print(f"\n7. Comparison with random [28,9] samples:")
rng = random.Random(999)
gv_samples = []
for s in range(50):
    vertices = list(range(M))
    rng.shuffle(vertices)
    edges = []
    for k in range(28):
        u = vertices[k]; v = vertices[(k+1)%28]
        edges.append((min(u,v), max(u,v)))
    for k in range(28, 37):
        u = vertices[k]; v = vertices[28 + (k-27)%9]
        edges.append((min(u,v), max(u,v)))
    gv_samples.append(gv(edges))

gv_samples.sort()
avg = sum(gv_samples) / len(gv_samples)
print(f"   Random [28,9] GV: min={gv_samples[0]} avg={avg:.1f} max={gv_samples[-1]}")
print(f"   config_408 GV: 70")
print(f"   Gap: {gv_samples[0] - 70} below best random")

# 8. Key question: co-occurrence of small coordinates
print(f"\n8. Coordinate co-occurrence analysis:")
from collections import defaultdict
coord_map = defaultdict(list)
for idx, (i,j) in enumerate(c408):
    coord_map[i].append(('i', idx, j))
    coord_map[j].append(('j', idx, i))

# Which vertices appear as i vs j
i_only = set(i_vals)
j_only = set(j_vals)
both = i_only & j_only
print(f"   Appear as i: {len(i_only)}")
print(f"   Appear as j: {len(j_only)}")
print(f"   Appear as both: {len(both)}")

# 9. Check: do cells with i≈j produce fewer collinearities?
print(f"\n9. Correlation between |i-j| and collinear participation:")
cell_collinear_count = Counter()
for a in range(M):
    la = all_orbits_0[c408[a]]
    for b in range(a+1, M):
        lb = all_orbits_0[c408[b]]
        for c in range(b+1, M):
            if check_12_fast(la + lb + all_orbits_0[c408[c]]):
                cell_collinear_count[a] += 1
                cell_collinear_count[b] += 1
                cell_collinear_count[c] += 1

# Top 10 most collinear cells
top_collinear = sorted(cell_collinear_count.items(), key=lambda x: -x[1])[:10]
print(f"   Top 10 most collinear cells:")
for idx, cnt in top_collinear:
    i, j = c408[idx]
    print(f"   cell {idx:2d}: ({i:2d},{j:2d}) |i-j|={abs(i-j):2d} participated in {cnt} collinear triples")

# Bottom 10 least collinear cells
bottom_collinear = sorted(cell_collinear_count.items(), key=lambda x: x[1])[:10]
print(f"\n   Bottom 10 least collinear cells:")
for idx, cnt in bottom_collinear:
    i, j = c408[idx]
    print(f"   cell {idx:2d}: ({i:2d},{j:2d}) |i-j|={abs(i-j):2d} participated in {cnt} collinear triples")

print("\n" + "=" * 60)
