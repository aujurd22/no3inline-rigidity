"""
Cross-cycle violation attack on config_408.
Step 1: Deep analysis of the 16 violations
Step 2: Construct low-cross-violation [28,9] 2-factors
"""
import json, time, random, sys
from collections import Counter, defaultdict

M = 37
N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

# === C4 rotation lifts ===
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return pts

all_lifts = {(u, v): c4_lift(u, v) for u in range(M) for v in range(M)}

cell_data = {}
for u in range(M):
    for v in range(M):
        pts0 = all_lifts[(u, v)]
        pts1 = all_lifts[(v, u)] if u != v else all_lifts[(u, v)]
        cell_data[(u, v)] = (pts0, pts1)

def is_collinear_12(lifts):
    for i in range(12):
        xi, yi = lifts[i]
        for j in range(i + 1, 12):
            xj, yj = lifts[j]
            if xi == xj and yi == yj:
                continue
            dx, dy = xj - xi, yj - yi
            for k in range(j + 1, 12):
                xk, yk = lifts[k]
                if xk == xi and yk == yi:
                    continue
                if dx * (yk - yi) == dy * (xk - xi):
                    return True, (i, j, k, xi, yi, xj, yj, xk, yk)
    return False, None

def get_violation_details(cells, orientation):
    """Return list of (cell_idx_a, cell_idx_b, cell_idx_c, orient_a, orient_b, orient_c, pts) for each violation."""
    violations = []
    for a in range(M):
        pa0, pa1 = cell_data[cells[a]]
        pa = pa0 if orientation[a] == 0 else pa1
        for b in range(a + 1, M):
            pb0, pb1 = cell_data[cells[b]]
            pb = pb0 if orientation[b] == 0 else pb1
            for c in range(b + 1, M):
                pc0, pc1 = cell_data[cells[c]]
                pc = pc0 if orientation[c] == 0 else pc1
                coll, details = is_collinear_12(pa + pb + pc)
                if coll:
                    violations.append({
                        'cells': (a, b, c),
                        'orient': (orientation[a], orientation[b], orientation[c]),
                        'coords': (cells[a], cells[b], cells[c]),
                        'details': details
                    })
    return violations

# === Load config_408 ===
with open(f"{HERE}/results/config_408_edges.json") as f:
    data = json.load(f)
edges = data['edges']
cells = [(min(u, v), max(u, v)) for u, v in edges]

with open(f"{HERE}/results/config_408_maxsat_result.json") as f:
    maxsat = json.load(f)
orientation = maxsat['orientation']
print(f"Config_408: {len(cells)} cells, {maxsat['n_clauses']} clauses, {maxsat['min_violations']} violations (PROVEN OPTIMAL)")
print(f"Orientation: {orientation}")
print()

# === Step 1: Trace the 28-cycle and 9-cycle ===
# Build adjacency from cells
adj = {i: [] for i in range(M)}
for idx, (u, v) in enumerate(cells):
    adj[u].append((v, idx))
    adj[v].append((u, idx))

# Find cycles by following degree-2 graph
visited_edges = set()
cycles = []
for start in range(M):
    if start in visited_edges:
        continue
    # Follow the cycle
    curr = start
    prev = -1
    cycle = []
    while True:
        visited_edges.add(curr)
        neighbors = [(n, eidx) for n, eidx in adj[curr] if n != prev]
        if not neighbors:
            break
        next_v, eidx = neighbors[0]
        cycle.append(eidx)
        visited_edges.add(eidx)
        prev = curr
        curr = next_v
        if curr == start:
            break
    if len(cycle) >= 3:
        cycles.append(cycle)

print(f"Found {len(cycles)} cycles:")
for i, cyc in enumerate(cycles):
    print(f"  Cycle {i}: {len(cyc)} cells (edges)")
    # List cells in this cycle
    for eidx in cyc:
        print(f"    cell[{eidx}] = {cells[eidx]}", end="")
        if eidx in cyc[:3]:
            print(" [28-cycle]" if i == 0 else " [9-cycle]")
        else:
            print()
    assert len(cyc) in (9, 28), f"Unexpected cycle length: {len(cyc)}"

# Identify 28-cycle and 9-cycle cells
cycle_28_cells = set(cycles[0])
cycle_9_cells = set(cycles[1])
if len(cycles[1]) == 28:
    cycle_28_cells, cycle_9_cells = cycle_9_cells, cycle_28_cells

print(f"\n28-cycle: {len(cycle_28_cells)} cells = {[cells[i] for i in sorted(cycle_28_cells)]}")
print(f"9-cycle: {len(cycle_9_cells)} cells = {[cells[i] for i in sorted(cycle_9_cells)]}")
assert len(cycle_28_cells) == 28 and len(cycle_9_cells) == 9

# === Step 2: Get all violations ===
violations = get_violation_details(cells, orientation)
print(f"\n=== {len(violations)} VIOLATIONS ===")

# Classify violations
vio_28only = []  # all 3 cells in 28-cycle
vio_9only = []   # all 3 cells in 9-cycle
vio_cross_28_28_9 = []  # 2 from 28-cycle, 1 from 9-cycle
vio_cross_28_9_9 = []   # 1 from 28-cycle, 2 from 9-cycle

for v in violations:
    a, b, c = v['cells']
    in28 = sum(1 for idx in (a, b, c) if idx in cycle_28_cells)
    in9 = sum(1 for idx in (a, b, c) if idx in cycle_9_cells)
    assert in28 + in9 == 3
    
    entry = {
        'cells': (a, b, c),
        'coords': v['coords'],
        'orient': v['orient'],
        'details': v['details']
    }
    
    if in28 == 3:
        vio_28only.append(entry)
    elif in9 == 3:
        vio_9only.append(entry)
    elif in28 == 2:
        vio_cross_28_28_9.append(entry)
    else:
        vio_cross_28_9_9.append(entry)

print(f"\n  28-cycle-only: {len(vio_28only)}")
for v in vio_28only:
    a, b, c = v['cells']
    print(f"    cells[{a}]={v['coords'][0]} + cells[{b}]={v['coords'][1]} + cells[{c}]={v['coords'][2]}  orient={v['orient']}")

print(f"\n  9-cycle-only: {len(vio_9only)}")
for v in vio_9only:
    a, b, c = v['cells']
    print(f"    cells[{a}]={v['coords'][0]} + cells[{b}]={v['coords'][1]} + cells[{c}]={v['coords'][2]}  orient={v['orient']}")

print(f"\n  Cross (28,28,9): {len(vio_cross_28_28_9)}")
for v in vio_cross_28_28_9:
    a, b, c = v['cells']
    # Which one is 9-cycle?
    nine_idx = [idx for idx in (a, b, c) if idx in cycle_9_cells][0]
    print(f"    cells[{a}]={v['coords'][0]} + cells[{b}]={v['coords'][1]} + cells[{c}]={v['coords'][2]}  9-cell=cell[{nine_idx}]={cells[nine_idx]}  orient={v['orient']}")
    # Show the collinear points
    det = v['details']
    print(f"      collinear at indices {det[0]},{det[1]},{det[2]} of 12 lifted points")

print(f"\n  Cross (28,9,9): {len(vio_cross_28_9_9)}")
for v in vio_cross_28_9_9:
    a, b, c = v['cells']
    print(f"    cells[{a}]={v['coords'][0]} + cells[{b}]={v['coords'][1]} + cells[{c}]={v['coords'][2]}  orient={v['orient']}")

# === Step 3: Track which cells are involved in violations ===
cell_violation_count = Counter()
for v in violations:
    for idx in v['cells']:
        cell_violation_count[idx] += 1

print(f"\n=== Cell violation frequency (out of {len(violations)} violations) ===")
for idx, count in cell_violation_count.most_common():
    cyc = "28" if idx in cycle_28_cells else "9"
    print(f"  cell[{idx}]={cells[idx]} ({cyc}-cycle): {count} violations")

print("\nCells with 0 violations:")
zero_vio = [i for i in range(M) if cell_violation_count.get(i, 0) == 0]
for idx in zero_vio:
    cyc = "28" if idx in cycle_28_cells else "9"
    print(f"  cell[{idx}]={cells[idx]} ({cyc}-cycle)")

# === Step 4: Cross-cycle coordinate pattern analysis ===
print("\n=== Cross-cycle coordinate analysis ===")
# Collect the coordinates involved in cross-cycle violations
all_cross_cells = set()
for v in vio_cross_28_28_9 + vio_cross_28_9_9:
    for idx in v['cells']:
        all_cross_cells.add(idx)

print(f"Cells involved in cross-cycle violations: {sorted(all_cross_cells)}")
for idx in sorted(all_cross_cells):
    cyc = "28" if idx in cycle_28_cells else "9"
    print(f"  cell[{idx}]={cells[idx]} ({cyc}-cycle): {cell_violation_count[idx]} total violations, "
          f"{sum(1 for v in violations if idx in v['cells'])} in cross")

# Analyze: what's special about cross-cycle violating cell pairs?
print("\n=== Cross-cycle pair analysis ===")
cross_pairs = defaultdict(int)
for v in vio_cross_28_28_9:
    a, b, c = v['cells']
    # Find the 9-cycle cell
    nine_idx = [idx for idx in (a, b, c) if idx in cycle_9_cells][0]
    twenty8_indices = [idx for idx in (a, b, c) if idx in cycle_28_cells]
    for t28 in twenty8_indices:
        cross_pairs[(t28, nine_idx)] += 1

for v in vio_cross_28_9_9:
    a, b, c = v['cells']
    twenty8_idx = [idx for idx in (a, b, c) if idx in cycle_28_cells][0]
    nine_indices = [idx for idx in (a, b, c) if idx in cycle_9_cells]
    for n9 in nine_indices:
        cross_pairs[(twenty8_idx, n9)] += 1

for (t28, n9), cnt in sorted(cross_pairs.items(), key=lambda x: -x[1]):
    print(f"  28-cell[{t28}]={cells[t28]} + 9-cell[{n9}]={cells[n9]}: {cnt} violations together")

# === Step 5: Try coordinate-preserving search ===
# Key insight: the cross-cycle violations occur between specific 28-cycle cells and 9-cycle cells.
# If we can find a [28,9] 2-factor where the 9-cycle avoids the "bad" 28-cycle coordinates, we may reduce violations.

print(f"\n\n{'='*60}")
print(f"STEP 5: Coordinate-avoidant [28,9] search")
print(f"{'='*60}")

# Which 28-cycle coordinates create the most cross-cycle trouble?
bad_28_coords = Counter()
for (t28, n9), cnt in cross_pairs.items():
    # The 28-cycle cell has coordinates (i,j)
    i, j = cells[t28]
    bad_28_coords[i] += cnt
    bad_28_coords[j] += cnt

print(f"\nMost troublesome 28-cycle coordinates (involved in cross-cycle violations):")
for coord, cnt in bad_28_coords.most_common(10):
    print(f"  vertex {coord}: {cnt} cross-cycle violations")

def random_2regular(cycle_lengths, rng):
    """Generate a random 2-factor with given cycle lengths on M vertices."""
    vertices = list(range(M))
    rng.shuffle(vertices)
    edges = []
    pos = 0
    for clen in cycle_lengths:
        cycle_verts = vertices[pos:pos + clen]
        pos += clen
        for k in range(clen):
            u = cycle_verts[k]
            v = cycle_verts[(k + 1) % clen]
            edges.append((u, v) if u <= v else (v, u))
    # Deduplicate properly (keep first occurrence)
    seen = set()
    unique = []
    for e in edges:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique

def total_clauses(cells):
    """Count clauses for a given set of cells (no orientation optimization)."""
    total = 0
    for a in range(M):
        pa0, pa1 = cell_data[cells[a]]
        for b in range(a + 1, M):
            pb0, pb1 = cell_data[cells[b]]
            for c in range(b + 1, M):
                pc0, pc1 = cell_data[cells[c]]
                # 8 orientation combos
                for oa in (0, 1):
                    pa = pa0 if oa == 0 else pa1
                    for ob in (0, 1):
                        pb = pb0 if ob == 0 else pb1
                        for oc in (0, 1):
                            pc = pc0 if oc == 0 else pc1
                            if is_collinear_12(pa + pb + pc)[0]:
                                total += 1
    return total

# Strategy: Generate [28,9] configs, try to avoid bad coordinate combinations
rng = random.Random(7777)
best_cl = 9999
best_cells = None

for trial in range(50):
    cells2 = random_2regular([28, 9], rng)
    if len(set(cells2)) != 37 or len(cells2) != 37:
        continue
    # Check degree
    deg = Counter()
    for u, v in cells2:
        deg[u] += 1
        deg[v] += 1
    if min(deg.values()) != 2 or max(deg.values()) != 2:
        continue
    
    cl = total_clauses(cells2)
    if cl < best_cl:
        best_cl = cl
        best_cells = list(cells2)
        print(f"  Trial {trial}: {cl} clauses (best so far)", flush=True)
        
        if cl < 408:
            print(f"  ★★★ BREAKTHROUGH: {cl} < 408! ★★★", flush=True)
            json.dump({"edges": cells2, "clauses": cl, "trial": trial, "type": "breakthrough"},
                      open(f"{HERE}/results/cc_breakthrough.json", "w"))

print(f"\nBest found: {best_cl} clauses (config_408: 408)")
if best_cl < 408:
    print("BREAKTHROUGH!")
    json.dump({"edges": best_cells, "clauses": best_cl},
              open(f"{HERE}/results/cc_best.json", "w"))
else:
    print("No improvement. Ready for CP-SAT validation of best config.")
    if best_cells:
        json.dump({"edges": best_cells, "clauses": best_cl},
                  open(f"{HERE}/results/cc_best.json", "w"))
