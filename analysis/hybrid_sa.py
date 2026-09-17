"""
Hybrid SA: single-layer search in (2-factor, orientation) combined space.
Each step: swap 2 cells + maybe flip some orientation bits → evaluate → accept/reject.
NO separate orientation optimization (too slow).
Uses clause counting (not violations counting) for speed — same as config_408 metric.
"""
import json, time, random, math
from collections import Counter, defaultdict

M = 37
N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

# === Precompute C4 lifts and collinearity cache ===
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return tuple(pts)

all_lifts = {(u, v): c4_lift(u, v) for u in range(M) for v in range(M)}

# For each cell (u,v), two orientations: orient=0 uses lifts[(u,v)], orient=1 uses lifts[(v,u)]
cell_lifts = {}
for u in range(M):
    for v in range(M):
        l0 = all_lifts[(u, v)]
        l1 = all_lifts[(v, u)] if u != v else l0
        cell_lifts[(u, v)] = (l0, l1)

# Precompute: for each triple of cells (a,b,c) and each of 8 orientation combos, 
# is it collinear? Store as bitmask.
# This is the PRE_COMPUTED clause list — build once, reuse in SA.
collinear_bits = {}
# a,b,c are cell indices 0..36, but we need cells tuple keys
# Actually, build on-the-fly: for each (cell_a, cell_b, cell_c) compute 8-bit mask
# We'll cache this lazily.

from functools import lru_cache

@lru_cache(maxsize=None)
def triple_mask(cell_a, cell_b, cell_c):
    """Return 8-bit mask: bit k = 1 if orientation combo k is collinear."""
    l_a0, l_a1 = cell_lifts[cell_a]
    l_b0, l_b1 = cell_lifts[cell_b]
    l_c0, l_c1 = cell_lifts[cell_c]
    mask = 0
    for bit in range(8):
        pa = l_a0 if (bit & 1) == 0 else l_a1
        pb = l_b0 if (bit & 2) == 0 else l_b1
        pc = l_c0 if (bit & 4) == 0 else l_c1
        lifts = pa + pb + pc
        coll = False
        for i in range(12):
            xi, yi = lifts[i]
            for j in range(i + 1, 12):
                xj, yj = lifts[j]
                if xi == xj and yi == yj: continue
                dx, dy = xj - xi, yj - yi
                for k in range(j + 1, 12):
                    xk, yk = lifts[k]
                    if xk == xi and yk == yi: continue
                    if dx * (yk - yi) == dy * (xk - xi):
                        coll = True
                        break
                if coll: break
            if coll: break
        if coll:
            mask |= (1 << bit)
    return mask

def count_clauses(cells, orient):
    """Count unfilled clauses for this (cells, orientation) pair."""
    total = 0
    for a in range(M):
        ca = cells[a]
        for b in range(a + 1, M):
            cb = cells[b]
            for c in range(b + 1, M):
                cc = cells[c]
                # Compute mask on the fly
                mask = triple_mask(ca, cb, cc)
                # This orientation combo's bit
                bit = (orient[a] & 1) | ((orient[b] & 1) << 1) | ((orient[c] & 1) << 2)
                if mask & (1 << bit):
                    total += 1
    return total

# === Fast bound: for a given cells array, compute min clauses via greedy orientation ===
def greedy_orient(cells, initial_orient, n_flips=50):
    """Quick orientation improvement via greedy flips."""
    orient = list(initial_orient)
    best_v = count_clauses(cells, orient)
    
    for _ in range(n_flips):
        # Find best single bit flip
        best_delta = 0
        best_idx = -1
        for idx in range(M):
            orient[idx] = 1 - orient[idx]
            v = count_clauses(cells, orient)
            delta = best_v - v  # positive = improvement
            orient[idx] = 1 - orient[idx]  # revert
            
            if delta > best_delta:
                best_delta = delta
                best_idx = idx
        
        if best_idx >= 0 and best_delta > 0:
            orient[best_idx] = 1 - orient[best_idx]
            best_v -= best_delta
        else:
            break
    
    return best_v, orient

# === Load config_408 ===
with open(f"{HERE}/results/config_408_edges.json") as f:
    data = json.load(f)
config408_cells = tuple(sorted((min(u,v), max(u,v)) for u,v in data['edges']))
with open(f"{HERE}/results/config_408_maxsat_result.json") as f:
    msat = json.load(f)
opt_orient = tuple(msat['orientation'])

# Verify
ref_cl = count_clauses(config408_cells, opt_orient)
print(f"config_408: clauses={msat['n_clauses']}, violations={msat['min_violations']} (OPTIMAL)")
print(f"Reference violations: {ref_cl}")
assert ref_cl == msat['min_violations'], f"Mismatch: {ref_cl} vs {msat['min_violations']}"

# === 2-swap ===
def two_swap(cells, rng):
    existing = set(cells)
    for _ in range(200):
        a = rng.randint(0, M - 1)
        b = rng.randint(0, M - 1)
        while b == a: b = rng.randint(0, M - 1)
        i1, j1 = cells[a]
        i2, j2 = cells[b]
        if len({i1, j1, i2, j2}) < 4: continue
        for e1, e2 in [
            ((min(i1,i2),max(i1,i2)), (min(j1,j2),max(j1,j2))),
            ((min(i1,j2),max(i1,j2)), (min(j1,i2),max(j1,i2))),
        ]:
            if e1 in existing or e2 in existing or e1 == e2: continue
            new = list(cells)
            new[a], new[b] = e1, e2
            return tuple(new), a, b
    return None, None, None

# === Main loop: combined SA on (cells, orient) ===
rng = random.Random(777)
cells = list(config408_cells)
orient = list(opt_orient)
current_cl = ref_cl
best_cl = ref_cl
best_cells = list(cells)
best_orient = list(orient)

T = 2.0
n_steps = 200

print(f"\n=== Combined (2-factor, orientation) SA: {n_steps} steps ===")
t0 = time.time()

# Pre-populate the cache for config_408's cells
_warmup = count_clauses(cells, orient)
print(f"  Cache warmed: violations={_warmup}", flush=True)

for step in range(n_steps):
    new_cells, ca, cb = two_swap(cells, rng)
    if new_cells is None: continue
    
    deg = Counter()
    for u, v in new_cells:
        deg[u] += 1
        deg[v] += 1
    if min(deg.values()) != 2 or max(deg.values()) != 2: continue
    if len(set(new_cells)) != 37: continue
    
    # Fast evaluation: try original orientation + 1 bit flip
    final_cl = count_clauses(new_cells, orient)
    final_orient = orient
    
    # Try 5 random single-bit flips + greedy (cache is warm after first call)
    new_or = list(orient)
    for f in range(min(5, step + 1)):  # More aggressive later
        idx = rng.randint(0, M - 1)
        new_or[idx] = 1 - new_or[idx]
        trial_cl = count_clauses(new_cells, new_or)
        if trial_cl < final_cl:
            final_cl = trial_cl
            final_orient = list(new_or)
        new_or[idx] = 1 - new_or[idx]  # revert
    
    # Try greedy improvement for promising candidates
    if final_cl <= current_cl and step > 20:
        gcl, gor = greedy_orient(new_cells, final_orient, n_flips=5)
        if gcl < final_cl:
            final_cl = gcl
            final_orient = gor
    
    delta = final_cl - current_cl
    if delta < 0 or rng.random() < math.exp(-delta / (T * 5)):
        cells = list(new_cells)
        orient = list(final_orient)
        current_cl = final_cl
        
        if final_cl < best_cl:
            best_cl = final_cl
            best_cells = list(new_cells)
            best_orient = list(final_orient)
            print(f"  Step {step}: ★ NEW BEST violations={best_cl} (config_408=16)", flush=True)
            
            if best_cl < 16:
                print(f"    ★★★ BREAKTHROUGH: {best_cl} < 16! ★★★", flush=True)
                json.dump({"edges": best_cells, "orientation": best_orient, "violations": best_cl},
                          open(f"{HERE}/results/hybrid_brk.json", "w"))
    
    T *= 0.985
    
    if (step + 1) % 50 == 0:
        print(f"  [{step+1}/{n_steps}] best_viol={best_cl}, cur={current_cl} ({time.time()-t0:.0f}s)", flush=True)

elapsed = time.time() - t0
print(f"\nDone: {n_steps} steps in {elapsed:.0f}s")
print(f"Best violations: {best_cl} (config_408: 16)")
json.dump({"edges": best_cells, "orientation": best_orient, "violations": best_cl},
          open(f"{HERE}/results/hybrid_result.json", "w"))
