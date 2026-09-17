"""
方向 B：违例模式解构
分析 config_408 在最优取向下哪 16 个三元组产生违例，
它们的结构共性、涉及的 cells、在 28-/9-圈中的分布。
"""
import json, time
from collections import Counter

M = 37; N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

# ── C4 lift ──────────────────────────────────────────────────────
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3): x, y = N - 1 - y, x; pts.append((x, y))
    return pts

all_lifts = {}
for u in range(M):
    for v in range(M):
        lift0 = c4_lift(u, v)
        lift1 = c4_lift(v, u) if u != v else c4_lift(u, v)
        all_lifts[(u, v, 0)] = lift0
        all_lifts[(u, v, 1)] = lift1

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

# ── Load config_408 ──────────────────────────────────────────────
with open(f"{HERE}/results/config_408_maxsat_result.json") as f:
    maxsat = json.load(f)
edges = [(min(u,v), max(u,v)) for u,v in maxsat["edges"]]
orientation = maxsat["orientation"]
print(f"config_408: {len(edges)} edges, min_viol={maxsat['min_violations']}", flush=True)
print(f"Orientation: {orientation}", flush=True)

# ── Identify the 16 violating triples ─────────────────────────────
violating_triples = []
for a in range(M):
    ea = edges[a]; la = all_lifts[(ea[0], ea[1], orientation[a])]
    for b in range(a+1, M):
        eb = edges[b]; lb = all_lifts[(eb[0], eb[1], orientation[b])]
        for c in range(b+1, M):
            ec = edges[c]; lc = all_lifts[(ec[0], ec[1], orientation[c])]
            if is_collinear_12(la + lb + lc):
                violating_triples.append((a, b, c))

print(f"\nFound {len(violating_triples)} violating triples", flush=True)
assert len(violating_triples) == maxsat["min_violations"], f"Mismatch: {len(violating_triples)} vs {maxsat['min_violations']}"

# ── Analysis 1: Which cells appear in how many violations? ────────
cell_violation_count = Counter()
for a, b, c in violating_triples:
    cell_violation_count[a] += 1
    cell_violation_count[b] += 1
    cell_violation_count[c] += 1

print(f"\n=== Cell violation frequency ===", flush=True)
print(f"  Total cell-occurrences in violations: {sum(cell_violation_count.values())}", flush=True)
print(f"  Cells with 0 violations: {M - len(cell_violation_count)}", flush=True)
print(f"  Top offenders:", flush=True)
for cell, count in cell_violation_count.most_common(15):
    i, j = edges[cell]
    print(f"    Cell {cell:2d} ({i:2d},{j:2d}): {count} violations", flush=True)

# ── Analysis 2: Which edges (i,j) appear in violations? ──────────
edge_violation_count = Counter()
for a, b, c in violating_triples:
    edge_violation_count[edges[a]] += 1
    edge_violation_count[edges[b]] += 1
    edge_violation_count[edges[c]] += 1

print(f"\n=== Edge (i,j) violation frequency ===", flush=True)
for (i,j), count in edge_violation_count.most_common(10):
    print(f"    ({i:2d},{j:2d}): {count} violations", flush=True)

# ── Analysis 3: Distribution of violations across cycles ──────────
# Determine which cells are in which cycle (28 vs 9)
# config_408_edges.json tells us the cycle structure
cycle_28 = set()  # cells in the 28-cycle
cycle_9 = set()   # cells in the 9-cycle

# From the analysis output: 28-cycle was [0,30,16,...] and 9-cycle was [2,20,26,...]
# Let me reconstruct from the edge structure
# We have 37 edges. Build adjacency to find cycles.
adj = {i: [] for i in range(M)}
for u, v in edges:
    adj[u].append(v)
    adj[v].append(u)

visited = set()
cycles = []
for start in range(M):
    if start in visited: continue
    # Walk the cycle
    cycle = [start]
    prev = -1
    cur = start
    while True:
        next_vert = [v for v in adj[cur] if v != prev][0]
        if next_vert == start:
            break
        cycle.append(next_vert)
        prev = cur
        cur = next_vert
    visited.update(cycle)
    cycles.append(cycle)

print(f"\n=== Cycle structure ===", flush=True)
for ci, cyc in enumerate(cycles):
    print(f"  Cycle {ci}: length {len(cyc)}, vertices {cyc}", flush=True)

# Count violations per cycle
viol_per_cycle = Counter()
viol_cross = 0
for a, b, c in violating_triples:
    # Check which cycles each cell belongs to
    cycles_of = [cycl for cyci, cyc in enumerate(cycles) for cycl in [cyci] if a in cyc or b in cyc or c in cyc]
    # Actually simpler:
    in_cycles = set()
    for ci, cyc in enumerate(cycles):
        for cell in (a,b,c):
            if cell in cyc:
                in_cycles.add(ci)
    
    if len(in_cycles) == 1:
        viol_per_cycle[list(in_cycles)[0]] += 1
    else:
        viol_cross += 1

print(f"\n=== Violation distribution ===", flush=True)
for ci in range(len(cycles)):
    print(f"  Within cycle {ci} (len={len(cycles[ci])}): {viol_per_cycle[ci]} violations", flush=True)
print(f"  Cross-cycle: {viol_cross} violations", flush=True)
print(f"  Total: {sum(viol_per_cycle.values()) + viol_cross}", flush=True)

# ── Analysis 4: Do violations cluster? ────────────────────────────
# Build a violation graph: cells are connected if they share a violation
# If this graph has cliques, violations are highly clustered
viol_adj = {i: set() for i in range(M)}
for a,b,c in violating_triples:
    viol_adj[a].add(b); viol_adj[a].add(c)
    viol_adj[b].add(a); viol_adj[b].add(c)
    viol_adj[c].add(a); viol_adj[c].add(b)

# Find connected components in violation graph
comp_visited = set()
components = []
for start in range(M):
    if start in comp_visited: continue
    if not viol_adj[start]: continue  # isolated (no violations)
    stack = [start]
    comp = []
    while stack:
        v = stack.pop()
        if v in comp_visited: continue
        comp_visited.add(v)
        comp.append(v)
        for nb in viol_adj[v]:
            if nb not in comp_visited:
                stack.append(nb)
    if comp:
        components.append(comp)

print(f"\n=== Violation graph components ===", flush=True)
print(f"  Number of components: {len(components)}", flush=True)
for ci, comp in enumerate(components):
    viol_count_in = sum(1 for a,b,c in violating_triples if a in comp or b in comp or c in comp)
    print(f"  Component {ci}: {len(comp)} cells, ~{viol_count_in} violations", flush=True)
    for cell in sorted(comp):
        i,j = edges[cell]
        print(f"    Cell {cell:2d} ({i:2d},{j:2d}) o={orientation[cell]}", flush=True)

# ── Analysis 5: Are violations from the same triple pattern? ──────
# For each violating triple, identify which coordinate pattern causes it
# Check: are the 3 collinear points always from the "original" C4 positions?
print(f"\n=== Triple patterns ===", flush=True)
# Check orientation combos: what fraction of viol triples have which orientation pattern?
orient_patterns = Counter()
for a,b,c in violating_triples:
    combo = (orientation[a], orientation[b], orientation[c])
    orient_patterns[combo] += 1
print(f"  Orientation combo distribution:", flush=True)
for combo, count in orient_patterns.most_common():
    print(f"    {combo}: {count} violations", flush=True)

# ── Analysis 6: How many unique i-values and j-values among viol cells? ──
viol_cells = set()
for a,b,c in violating_triples:
    viol_cells.add(a); viol_cells.add(b); viol_cells.add(c)

i_vals = Counter()
j_vals = Counter()
for cell in viol_cells:
    i,j = edges[cell]
    i_vals[i] += 1
    j_vals[j] += 1

print(f"\n=== Coordinate distribution in violating cells ===", flush=True)
print(f"  i-values ({len(i_vals)} unique):", flush=True)
for i_val, count in i_vals.most_common(10):
    print(f"    i={i_val:2d}: {count}x", flush=True)
print(f"  j-values ({len(j_vals)} unique):", flush=True)
for j_val, count in j_vals.most_common(10):
    print(f"    j={j_val:2d}: {count}x", flush=True)

# ── Analysis 7: Check if any cell is in ALL violations (unavoidable core) ──
print(f"\n=== Overlap analysis ===", flush=True)
for cell in sorted(cell_violation_count, key=lambda c: -cell_violation_count[c])[:5]:
    frac = cell_violation_count[cell] / len(violating_triples)
    print(f"  Cell {cell:2d}: {cell_violation_count[cell]}/{len(violating_triples)} = {frac:.1%}", flush=True)

# ── Summary ───────────────────────────────────────────────────────
print(f"\n{'='*60}", flush=True)
print(f"    Direction B Summary", flush=True)
print(f"{'='*60}", flush=True)
print(f"  Total violations: {len(violating_triples)}", flush=True)
print(f"  Cells involved: {len(viol_cells)}/{M}", flush=True)
print(f"  Violations clustered in {len(components)} connected components", flush=True)
print(f"  Cycles: {[len(c) for c in cycles]}", flush=True)

# Key metrics
print(f"\n  Key metrics:", flush=True)
print(f"  - Fraction of cells with 0 violations: {(M - len(cell_violation_count))/M:.0%}", flush=True)
print(f"  - Top 3 cells account for: {sum(v for _,v in cell_violation_count.most_common(3))}/{len(violating_triples)*3:.0%}", flush=True)

# Single-observation: is there a cell in ALL violations?
max_cell = cell_violation_count.most_common(1)[0]
print(f"  - Most involved cell: {max_cell[0]} (in {max_cell[1]}/{len(violating_triples)} violations)", flush=True)
