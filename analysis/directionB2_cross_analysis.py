"""
方向 B2：跨圈违例深度分析 — 8 个跨圈违例的 cell 组合模式
"""
import json, time
from collections import Counter, defaultdict

M = 37; N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3): x, y = N - 1 - y, x; pts.append((x, y))
    return pts

all_lifts = {}
for u in range(M):
    for v in range(M):
        all_lifts[(u, v, 0)] = c4_lift(u, v)
        all_lifts[(u, v, 1)] = c4_lift(v, u) if u != v else c4_lift(u, v)

def is_collinear_12(lifts):
    for i in range(12):
        xi, yi = lifts[i]
        for j in range(i + 1, 12):
            xj, yj = lifts[j]
            if xi == xj and yi == yj: continue
            dx, dy = xj - xi, yj - yi
            for k in range(j + 1, 12):
                xk, yk = lifts[k]
                if xk == xi and yk == yi: continue
                if dx * (yk - yi) == dy * (xk - xi): return True
    return False

# ── Load ─────────────────────────────────────────────────────────
with open(f"{HERE}/results/config_408_maxsat_result.json") as f:
    maxsat = json.load(f)
edges = [(min(u,v), max(u,v)) for u,v in maxsat["edges"]]
orientation = maxsat["orientation"]

# Build adjacency for cycle detection
adj = {i: [] for i in range(M)}
for u, v in edges:
    adj[u].append(v); adj[v].append(u)

visited = set()
cycles = []
for start in range(M):
    if start in visited: continue
    cycle = [start]; prev = -1; cur = start
    while True:
        nxt = [v for v in adj[cur] if v != prev][0]
        if nxt == start: break
        cycle.append(nxt); prev = cur; cur = nxt
    visited.update(cycle)
    cycles.append(cycle)

# Map cell index → cycle ID
cell_to_cycle = {}
for ci, cyc in enumerate(cycles):
    for v in cyc:
        cell_to_cycle[v] = ci

# Find violating triples
violating = []
for a in range(M):
    ea = edges[a]; la = all_lifts[(ea[0], ea[1], orientation[a])]
    for b in range(a+1, M):
        eb = edges[b]; lb = all_lifts[(eb[0], eb[1], orientation[b])]
        for c in range(b+1, M):
            ec = edges[c]; lc = all_lifts[(ec[0], ec[1], orientation[c])]
            if is_collinear_12(la + lb + lc):
                violating.append((a, b, c))

# Separate cross-cycle vs within-cycle
cross = [(a,b,c) for a,b,c in violating if len({cell_to_cycle[a], cell_to_cycle[b], cell_to_cycle[c]}) > 1]
within = [(a,b,c) for a,b,c in violating if len({cell_to_cycle[a], cell_to_cycle[b], cell_to_cycle[c]}) == 1]

print(f"Total violations: {len(violating)}", flush=True)
print(f"Cross-cycle: {len(cross)}", flush=True)
print(f"Within-cycle: {len(within)}", flush=True)

print(f"\n{'='*70}", flush=True)
print(f"    CROSS-CYCLE VIOLATIONS (8)", flush=True)
print(f"{'='*70}", flush=True)
for idx, (a,b,c) in enumerate(cross):
    cyc = [cell_to_cycle[x] for x in (a,b,c)]
    orient = [orientation[x] for x in (a,b,c)]
    ea, eb, ec = edges[a], edges[b], edges[c]
    # Count how many cells from each cycle
    from_cyc0 = sum(1 for x in (a,b,c) if cell_to_cycle[x]==0)
    from_cyc1 = sum(1 for x in (a,b,c) if cell_to_cycle[x]==1)
    
    # Which exact collinear points?
    lifts = []
    for cell_idx, (u,v) in [(a,ea), (b,eb), (c,ec)]:
        lifts.append(all_lifts[(u, v, orientation[cell_idx])])
    all_pts = lifts[0] + lifts[1] + lifts[2]
    
    # Find which 3 points are collinear
    coll_triple = None
    for i in range(12):
        xi, yi = all_pts[i]
        for j in range(i+1, 12):
            xj, yj = all_pts[j]
            if xi==xj and yi==yj: continue
            dx, dy = xj-xi, yj-yi
            for k in range(j+1, 12):
                xk, yk = all_pts[k]
                if xk==xi and yk==yi: continue
                if dx*(yk-yi)==dy*(xk-xi):
                    coll_triple = (all_pts[i], all_pts[j], all_pts[k])
                    break
            if coll_triple: break
        if coll_triple: break
    
    # Which cells (original vs rotated) produced the collinear points?
    point_sources = []
    for pt in coll_triple:
        for ci, pts in enumerate(lifts):
            for pi, p in enumerate(pts):
                if p == pt:
                    point_sources.append((ci, pi, f"cell{a if ci==0 else (b if ci==1 else c)}.rot{pi}"))
    
    print(f"\n  Violation {idx+1}: cells ({a},{b},{c})", flush=True)
    print(f"    Cycles: {cyc} ({from_cyc0} from cyc0, {from_cyc1} from cyc1)", flush=True)
    print(f"    Orients: {orient}", flush=True)
    print(f"    Edges: {ea}, {eb}, {ec}", flush=True)
    print(f"    Collinear pts: {coll_triple}", flush=True)
    for src in sorted(point_sources):
        print(f"      {src}", flush=True)

# ── Pattern analysis: which 28-cycle cells pair with which 9-cycle cells? ──
print(f"\n{'='*70}", flush=True)
print(f"    CROSS-CYCLE CELL PAIRING PATTERNS", flush=True)
print(f"{'='*70}", flush=True)

cyc0_edges_in_cross = Counter()
cyc1_edges_in_cross = Counter()
cross_pairs = Counter()  # (cyc0_cell, cyc1_cell) pairs

for a,b,c in cross:
    cyc0_cells = [x for x in (a,b,c) if cell_to_cycle[x]==0]
    cyc1_cells = [x for x in (a,b,c) if cell_to_cycle[x]==1]
    for c0 in cyc0_cells:
        cyc0_edges_in_cross[edges[c0]] += 1
    for c1 in cyc1_cells:
        cyc1_edges_in_cross[edges[c1]] += 1
    for c0 in cyc0_cells:
        for c1 in cyc1_cells:
            cross_pairs[(c0, c1)] += 1

print("\n  9-cycle edges (cells) most active in cross violations:", flush=True)
for (i,j), cnt in cyc1_edges_in_cross.most_common(8):
    print(f"    ({i:2d},{j:2d}): {cnt} cross violations", flush=True)

print("\n  28-cycle edges most active in cross violations:", flush=True)
for (i,j), cnt in cyc0_edges_in_cross.most_common(10):
    print(f"    ({i:2d},{j:2d}): {cnt} cross violations", flush=True)

print(f"\n  Top cell pairs (cyc0, cyc1) in cross violations:", flush=True)
for (c0,c1), cnt in cross_pairs.most_common(10):
    print(f"    cyc0[{c0:2d}]({edges[c0]}) × cyc1[{c1:2d}]({edges[c1]}): {cnt}x", flush=True)

# ── Are cross violations concentrated on a subset of 9-cycle cells? ──
print(f"\n{'='*70}", flush=True)
print(f"    9-CYCLE CELLS INVOLVED IN CROSS VIOLATIONS", flush=True)
print(f"{'='*70}", flush=True)
cyc1_cells_involved = set()
for a,b,c in cross:
    for x in (a,b,c):
        if cell_to_cycle[x] == 1:
            cyc1_cells_involved.add(x)
print(f"  9-cycle has {len(cycles[1])} cells total, {len(cyc1_cells_involved)} involved in cross violations", flush=True)
# Which 9-cycle cells are involved?
cyc1_all = set(range(M))
# Actually, let me get the cell indices for cycle 1
cyc1_indices = [i for i in range(M) if cell_to_cycle[i]==1]
print(f"  9-cycle cell indices: {cyc1_indices}", flush=True)
print(f"  9-cycle cell edges:", flush=True)
for ci in cyc1_indices:
    viol = sum(1 for a,b,c in cross if ci in (a,b,c))
    marker = " ←" if viol > 0 else ""
    print(f"    cell {ci:2d} -> edge {edges[ci]} o={orientation[ci]} | {viol} cross-viol{marker}", flush=True)

# ── Same for 28-cycle ──
print(f"\n{'='*70}", flush=True)
print(f"    28-CYCLE CELLS INVOLVED IN CROSS VIOLATIONS", flush=True)
print(f"{'='*70}", flush=True)
cyc0_indices = [i for i in range(M) if cell_to_cycle[i]==0]
cyc0_involved = [ci for ci in cyc0_indices if any(ci in (a,b,c) for a,b,c in cross)]
print(f"  28-cycle has {len(cycles[0])} cells total, {len(cyc0_involved)} involved in cross violations", flush=True)
print(f"  Involved cells (sorted by involvement):", flush=True)
cyc0_counts = Counter()
for a,b,c in cross:
    for x in (a,b,c):
        if cell_to_cycle[x]==0:
            cyc0_counts[x] += 1
for ci, cnt in cyc0_counts.most_common():
    print(f"    cell {ci:2d} -> edge {edges[ci]} o={orientation[ci]} | {cnt} cross-viol", flush=True)

# ── Check the 7 within-cycle-0 violations ──
print(f"\n{'='*70}", flush=True)
print(f"    WITHIN-CYCLE-0 VIOLATIONS (7)", flush=True)
print(f"{'='*70}", flush=True)
within0 = [(a,b,c) for a,b,c in within if cell_to_cycle[a]==0]
print(f"  28-cycle internal violations: {len(within0)}", flush=True)
cell_within0 = Counter()
for a,b,c in within0:
    for x in (a,b,c):
        cell_within0[x] += 1
for ci, cnt in cell_within0.most_common():
    print(f"    cell {ci:2d} -> edge {edges[ci]} o={orientation[ci]} | {cnt} violations", flush=True)

# ── Summary ──
print(f"\n{'='*70}", flush=True)
print(f"    STRATEGIC INSIGHT", flush=True)
print(f"{'='*70}", flush=True)
print(f"""
If we can reduce cross-cycle violations from 8 to ~2:
  - Current: 7(cyc0) + 1(cyc1) + 8(cross) = 16
  - Target:  7(cyc0) + 1(cyc1) + 2(cross) = 10
  
Key question: what makes the 28-cycle cells and 9-cycle cells interact badly?
Look at the edges of the 9-cycle cells involved in cross violations.
If they share common i or j values with the 28-cycle cells they pair with,
that creates more collinearity opportunities.
""", flush=True)
