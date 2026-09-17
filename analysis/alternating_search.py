"""
Targeted search: maximize bipartite structure of [28,9] 2-factors.
Key insight from config_408:
- 28-cycle mostly uses crossing pairs (i∈P1, j∈P2) — 24/28 cells crossing
- But 4 cells are internal to P2: (21,32),(21,33),(24,34),(27,36) 
- 9-cycle has 4/9 internal cells — (8,13),(20,26),(25,26) cause most cross violations

Strategy: Generate configs where ALL cells are crossing (P1↔P2).
For a 28-cycle (even) this is fully alternating.
For a 9-cycle (odd) minimum 1 internal edge.

Then search for minimal clause count using CP-SAT validation.
"""
import json, time, random, sys, math
from collections import Counter, defaultdict

M = 37
N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

# Partition: P1 = {0..16}, P2 = {17..36}
P1 = set(range(17))
P2 = set(range(17, 37))

def in_p(v):
    return 0 if v in P1 else 1

def is_crossing(u, v):
    return (u in P1 and v in P2) or (u in P2 and v in P1)

# === C4 lifts ===
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
                    return True
    return False

def count_clauses_fast(cells):
    """Zero-orientation clause count (fast proxy, ~0.3s)."""
    total = 0
    for a in range(M):
        pa0, _ = cell_data[cells[a]]
        for b in range(a + 1, M):
            pb0, _ = cell_data[cells[b]]
            for c in range(b + 1, M):
                pc0, _ = cell_data[cells[c]]
                if is_collinear_12(pa0 + pb0 + pc0):
                    total += 1
    return total

# === Generate alternating 2-factor ===
def generate_alternating(cycle_lengths, rng):
    """
    Generate a 2-factor where each cycle alternates between P1 and P2 as much as possible.
    For even-length cycles: fully alternating (P1,P2,P1,P2,...)
    For odd-length cycles: alternating with one adjacent P1-P1 or P2-P2 pair.
    """
    # Split available vertices by partition
    p1_verts = sorted(P1)
    p2_verts = sorted(P2)
    rng.shuffle(p1_verts)
    rng.shuffle(p2_verts)
    
    all_edges = []
    pos1 = 0  # position in p1_verts
    pos2 = 0  # position in p2_verts
    
    for clen in cycle_lengths:
        # Determine the alternation pattern
        half = clen // 2
        
        # For even cycles: we need half from P1, half from P2
        # For odd cycles: one partition gives one more vertex
        if clen % 2 == 0:
            needed_p1 = half
            needed_p2 = half
        else:
            # Odd cycle: can be (half+1 from P1, half from P2) or vice versa
            # Try to balance overall
            remaining_p1 = len(p1_verts) - pos1
            remaining_p2 = len(p2_verts) - pos2
            
            if remaining_p1 >= half + 1 and remaining_p2 >= half:
                # More from P1
                needed_p1 = half + 1
                needed_p2 = half
            elif remaining_p2 >= half + 1 and remaining_p1 >= half:
                needed_p1 = half
                needed_p2 = half + 1
            else:
                # Fallback: whatever fits
                needed_p1 = min(half + 1, remaining_p1)
                needed_p2 = clen - needed_p1
        
        # Take the needed vertices
        cycle_p1 = p1_verts[pos1:pos1 + needed_p1]
        cycle_p2 = p2_verts[pos2:pos2 + needed_p2]
        pos1 += needed_p1
        pos2 += needed_p2
        
        # Build alternating cycle
        # Pattern: P1,P2,P1,P2,... (or P2,P1,P2,P1,...)
        cycle_verts = []
        p1_idx, p2_idx = 0, 0
        
        # Start with whichever partition has more
        if needed_p1 >= needed_p2:
            # Start with P1
            for k in range(clen):
                if k % 2 == 0 and p1_idx < needed_p1:
                    cycle_verts.append(cycle_p1[p1_idx]); p1_idx += 1
                elif p2_idx < needed_p2:
                    cycle_verts.append(cycle_p2[p2_idx]); p2_idx += 1
                else:
                    cycle_verts.append(cycle_p1[p1_idx]); p1_idx += 1
        else:
            # Start with P2
            for k in range(clen):
                if k % 2 == 0 and p2_idx < needed_p2:
                    cycle_verts.append(cycle_p2[p2_idx]); p2_idx += 1
                elif p1_idx < needed_p1:
                    cycle_verts.append(cycle_p1[p1_idx]); p1_idx += 1
                else:
                    cycle_verts.append(cycle_p2[p2_idx]); p2_idx += 1
        
        # Add edges for this cycle
        for k in range(clen):
            u = cycle_verts[k]
            v = cycle_verts[(k + 1) % clen]
            all_edges.append((u, v) if u <= v else (v, u))
    
    # Deduplicate
    seen = set()
    unique = []
    for e in all_edges:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique

# === Main search ===
rng = random.Random(12345)
best_cl = 9999
best_cells = None

# Config 408 baseline
c408_cl = count_clauses_fast([(min(u,v), max(u,v)) for u,v in json.load(open(f"{HERE}/results/config_408_edges.json"))['edges']])
print(f"config_408 zero-orient clauses: {c408_cl}", flush=True)

print(f"\n{'='*60}")
print(f"Alternating [28,9] search (emphasizing config_408-like structure)")
print(f"{'='*60}")

# Strategy 1: Pure alternating [28,9]
print(f"\n--- Strategy 1: Pure alternating [28,9] ---")
for trial in range(300):
    cells = generate_alternating([28, 9], rng)
    if len(cells) != 37 or len(set(cells)) != 37:
        continue
    
    # Verify all cells are crossing
    crossing = sum(1 for u, v in cells if is_crossing(u, v))
    
    cl = count_clauses_fast(cells)
    if cl < best_cl:
        best_cl = cl
        best_cells = list(cells)
        print(f"  Trial {trial}: {cl} clauses (crossing={crossing}/37) ★ NEW BEST", flush=True)
        
        if cl < c408_cl - 5:
            print(f"  ★★★ BREAKTHROUGH: {cl} < {c408_cl}! ★★★", flush=True)
            json.dump({"edges": cells, "clauses": cl, "crossing": crossing},
                      open(f"{HERE}/results/alts_breakthrough.json", "w"))

print(f"\nStrategy 1 best: {best_cl} clauses")

# Strategy 2: Config-408-like with random vertex permutation
print(f"\n--- Strategy 2: Config-408 edge structure + permuted labels ---")
c408_raw = [(min(u,v), max(u,v)) for u,v in json.load(open(f"{HERE}/results/config_408_edges.json"))['edges']]

for trial in range(300):
    perm = list(range(M))
    rng.shuffle(perm)
    permuted = [(perm[u], perm[v]) for u, v in c408_raw]
    permuted = [(min(u,v), max(u,v)) for u,v in permuted]
    
    # Check degree
    deg = Counter()
    for u, v in permuted:
        deg[u] += 1
        deg[v] += 1
    if min(deg.values()) != 2 or max(deg.values()) != 2:
        continue
    
    cl = count_clauses_fast(permuted)
    if cl < best_cl:
        best_cl = cl
        best_cells = list(permuted)
        print(f"  Trial {trial}: {cl} clauses ★ NEW BEST", flush=True)
        
        if cl < c408_cl - 5:
            print(f"  ★★★ BREAKTHROUGH: {cl} < {c408_cl}! ★★★", flush=True)

print(f"\nOverall best: {best_cl} clauses (config_408 zero-orient: {c408_cl})")

if best_cells:
    json.dump({"edges": best_cells, "clauses": best_cl, "time": time.time()},
              open(f"{HERE}/results/alts_best.json", "w"))

# If best is close to config_408's zero-orient, CP-SAT validate it
if best_cl <= c408_cl + 5:
    print(f"\nBest is within 5 of config_408! CP-SAT validation recommended.", flush=True)
    print(f"Run: python quick_verify.py results/alts_best.json", flush=True)
