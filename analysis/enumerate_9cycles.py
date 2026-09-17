"""
Fix config_408's 28-cycle, enumerate ALL 9-cycles on remaining 9 vertices.
Key optimization: precompute triple masks for all possible 9-cycle cells (36 options)
Then evaluate any 9-cycle in O(1).

Also compute clause_count (sum of all 8-bit masks) as an orientation-independent metric.
"""
import json, time, math, itertools, sys
from collections import Counter

M = 37
N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

# === C4 lifts ===
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return tuple(pts)

all_lifts = {(u, v): c4_lift(u, v) for u in range(M) for v in range(M)}
cell_lifts = {}
for u in range(M):
    for v in range(M):
        l0 = all_lifts[(u, v)]
        l1 = all_lifts[(v, u)] if u != v else l0
        cell_lifts[(u, v)] = (l0, l1)

def compute_triple_mask(cell_a, cell_b, cell_c):
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
                    if dx * (yk - yi) == dy * (xk - xi): coll = True; break
                if coll: break
            if coll: break
        if coll: mask |= (1 << bit)
    return mask

# === Load config_408 and trace cycles ===
with open(f"{HERE}/results/config_408_edges.json") as f:
    data = json.load(f)
config408 = [(min(u,v), max(u,v)) for u,v in data['edges']]

adj = {i: [] for i in range(M)}
for idx, (u, v) in enumerate(config408):
    adj[u].append((v, idx))
    adj[v].append((u, idx))

visited_edges = set()
cycles = []
for start in range(M):
    if start in visited_edges: continue
    curr, prev = start, -1
    cycle = []
    while True:
        visited_edges.add(curr)
        neighbors = [(n, eidx) for n, eidx in adj[curr] if n != prev]
        if not neighbors: break
        nxt, eidx = neighbors[0]
        cycle.append(eidx)
        visited_edges.add(eidx)
        prev, curr = curr, nxt
        if curr == start: break
    if len(cycle) >= 3: cycles.append(cycle)

c28 = set(cycles[0]) if len(cycles[0]) == 28 else set(cycles[1])
c9 = set(cycles[0]) if len(cycles[0]) == 9 else set(cycles[1])
c28_cells = [config408[i] for i in sorted(c28)]
c9_cells_orig = [config408[i] for i in sorted(c9)]
c9_verts = sorted(set(v for e in c9_cells_orig for v in e))

print(f"28-cycle: {len(c28_cells)} cells")
print(f"9-cycle: {len(c9_cells_orig)} cells on vertices {c9_verts}")
print(f"All possible 9-cycle edges: C(9,2) = {math.comb(9,2)} candidates")

# === Step 1: Precompute all possible 9-cycle cells ===
all_possible_9cells = []
for i in range(len(c9_verts)):
    for j in range(i+1, len(c9_verts)):
        all_possible_9cells.append((c9_verts[i], c9_verts[j]))
print(f"Total possible 9-cycle cells: {len(all_possible_9cells)}")

# Step 2: Precompute masks for all triples involving 9-cycle cells
t0 = time.time()
masks_cache = {}

# (28, 28, 9) triples
print("Computing (28,28,9) masks...")
for a in range(28):
    ca = c28_cells[a]
    for b in range(a+1, 28):
        cb = c28_cells[b]
        for c9cell in all_possible_9cells:
            key = tuple(sorted([ca, cb, c9cell]))
            masks_cache[key] = compute_triple_mask(ca, cb, c9cell)
    if (a+1) % 10 == 0:
        print(f"  {a+1}/28 ({time.time()-t0:.0f}s)", flush=True)
print(f"  Done: {len(masks_cache)}")

# (28, 9, 9) triples
print("Computing (28,9,9) masks...")
for a in range(28):
    ca = c28_cells[a]
    for bi in range(len(all_possible_9cells)):
        cb = all_possible_9cells[bi]
        for ci in range(bi+1, len(all_possible_9cells)):
            cc = all_possible_9cells[ci]
            key = tuple(sorted([ca, cb, cc]))
            masks_cache[key] = compute_triple_mask(ca, cb, cc)
    if (a+1) % 10 == 0:
        print(f"  {a+1}/28 ({time.time()-t0:.0f}s)", flush=True)
print(f"  Done: {len(masks_cache)}")

# (9, 9, 9) triples
print("Computing (9,9,9) masks...")
for ai in range(len(all_possible_9cells)):
    ca = all_possible_9cells[ai]
    for bi in range(ai+1, len(all_possible_9cells)):
        cb = all_possible_9cells[bi]
        for ci in range(bi+1, len(all_possible_9cells)):
            cc = all_possible_9cells[ci]
            key = tuple(sorted([ca, cb, cc]))
            masks_cache[key] = compute_triple_mask(ca, cb, cc)
    if (ai+1) % 10 == 0:
        print(f"  {ai+1}/{len(all_possible_9cells)} ({time.time()-t0:.0f}s)", flush=True)

elapsed = time.time() - t0
print(f"\nPrecomputation done: {len(masks_cache)} masks in {elapsed:.0f}s")

# Also cache (28,28,28) triples
print("Caching (28,28,28) masks...")
t0 = time.time()
for a in range(28):
    ca = c28_cells[a]
    for b in range(a+1, 28):
        cb = c28_cells[b]
        for c in range(b+1, 28):
            cc = c28_cells[c]
            masks_cache[tuple(sorted([ca, cb, cc]))] = compute_triple_mask(ca, cb, cc)
    if (a+1) % 14 == 0:
        print(f"  {a+1}/28 done ({time.time()-t0:.0f}s)", flush=True)
print(f"  Done: {len(masks_cache)} total masks cached")

# === Step 3: Enumerate 9-cycles ===
print(f"\n=== Enumerating 9-cycles ===")
config408_mask_total = sum(v for v in masks_cache.values())  # doesn't include the 9-cycle ones yet
# Actually compute the full clause count for config_408
config408_full_cells = tuple(config408)
config408_clauses = 0
for a in range(M):
    for b in range(a+1, M):
        for c in range(b+1, M):
            ca, cb, cc = config408_full_cells[a], config408_full_cells[b], config408_full_cells[c]
            config408_clauses += bin(compute_triple_mask(ca, cb, cc)).count('1')
print(f"config_408 total clause count: {config408_clauses}")

def total_clauses(masks, c28_cells_tuple, c9_cells):
    """
    Compute total clause count (sum of bits in all masks) for a given 9-cycle.
    Uses precomputed masks where available.
    """
    num_c28 = len(c28_cells_tuple)
    total = 0
    
    # (28,28,28) triples — already cached from precomputation
    for a in range(num_c28):
        ca = c28_cells_tuple[a]
        for b in range(a+1, num_c28):
            cb = c28_cells_tuple[b]
            for c in range(b+1, num_c28):
                cc = c28_cells_tuple[c]
                total += bin(get_mask(masks, (ca, cb, cc))).count('1')
    
    # (28,28,9) triples
    for a in range(num_c28):
        ca = c28_cells_tuple[a]
        for b in range(a+1, num_c28):
            cb = c28_cells_tuple[b]
            for c9cell in c9_cells:
                total += bin(get_mask(masks, (ca, cb, c9cell))).count('1')
    
    # (28,9,9) triples
    for a in range(num_c28):
        ca = c28_cells_tuple[a]
        for bi in range(9):
            cb = c9_cells[bi]
            for ci in range(bi+1, 9):
                cc = c9_cells[ci]
                total += bin(get_mask(masks, (ca, cb, cc))).count('1')
    
    # (9,9,9) triples
    for ai in range(9):
        ca = c9_cells[ai]
        for bi in range(ai+1, 9):
            cb = c9_cells[bi]
            for ci in range(bi+1, 9):
                cc = c9_cells[ci]
                total += bin(get_mask(masks, (ca, cb, cc))).count('1')
    
    return total
    
    return total

def get_mask(masks, cells_triple):
    """Look up mask with sorted key to handle any cell ordering."""
    # Sort the triple lexicographically for consistent lookup
    s = tuple(sorted(cells_triple))
    return masks[s]

def violations_fast(c9_cells, orient, masks, c28_cells_tuple):
    """Fast violation count using precomputed masks."""
    num_c28 = len(c28_cells_tuple)
    v = 0
    full = list(c28_cells_tuple) + list(c9_cells)
    for a in range(M):
        ca = full[a]
        for b in range(a+1, M):
            cb = full[b]
            for c in range(b+1, M):
                cc = full[c]
                mask = get_mask(masks, (ca, cb, cc))
                bit = (orient[a]) | (orient[b] << 1) | (orient[c] << 2)
                if mask & (1 << bit):
                    v += 1
    return v

def greedy_violations(c9_cells, masks, c28_cells_tuple, n_flips=20):
    """Greedy orientation optimization using precomputed masks."""
    M_total = 37
    orient = [0] * M_total
    full = list(c28_cells_tuple) + list(c9_cells)
    
    # First compute baseline
    v = 0
    for a in range(M_total):
        ca = full[a]
        for b in range(a+1, M_total):
            cb = full[b]
            for c in range(b+1, M_total):
                cc = full[c]
                mask = get_mask(masks, (ca, cb, cc))
                bit = (orient[a]) | (orient[b] << 1) | (orient[c] << 2)
                if mask & (1 << bit): v += 1
    best_v = v
    
    for _ in range(n_flips):
        best_idx = -1
        best_delta = 0
        for idx in range(M_total):
            orient[idx] = 1 - orient[idx]
            v = 0
            for a in range(M_total):
                ca = full[a]
                for b in range(a+1, M_total):
                    cb = full[b]
                    for c in range(b+1, M_total):
                        cc = full[c]
                        mask = get_mask(masks, (ca, cb, cc))
                        bit = (orient[a]) | (orient[b] << 1) | (orient[c] << 2)
                        if mask & (1 << bit): v += 1
            delta = best_v - v
            orient[idx] = 1 - orient[idx]
            if delta > best_delta:
                best_delta, best_idx = delta, idx
        if best_idx >= 0 and best_delta > 0:
            orient[best_idx] = 1 - orient[best_idx]
            best_v -= best_delta
        else:
            break
    return best_v, orient

# Build lookup for 9-cycle enumeration
c28_tuple = tuple(c28_cells)
n_verts = len(c9_verts)

best_clauses = 999999
best_violations = 9999
best_9cells = None
tested = 0

# Enumerate: fix first vertex, iterate over permutations of rest
first_v = c9_verts[0]
rest_v = list(c9_verts[1:])
total_possible = math.factorial(n_verts - 1) // 2

t0 = time.time()
for idx_inner, perm in enumerate(itertools.permutations(rest_v)):
    cycle = [first_v] + list(perm)
    if cycle[1] > cycle[-1]:  # Skip reverse duplicates
        continue
    
    # Build 9 cells from cycle
    cells = []
    for k in range(n_verts):
        u, v = cycle[k], cycle[(k+1) % n_verts]
        cells.append((u, v) if u <= v else (v, u))
    
    deg = Counter()
    for u, v in cells: deg[u] += 1; deg[v] += 1
    if min(deg.values()) != 2 or max(deg.values()) != 2: continue
    if len(set(cells)) != 9: continue
    
    tested += 1
    c9t = tuple(cells)
    
    # Compute total clause count (orientation-independent)
    cl = total_clauses(masks_cache, c28_tuple, c9t)
    
    if cl < best_clauses:
        best_clauses = cl
        best_9cells = c9t
        
        # Also compute greedy violations
        gv, gor = greedy_violations(c9t, masks_cache, c28_tuple, n_flips=10)
        best_violations = gv
        
        full_cells = list(c28_tuple) + list(c9t)
        print(f"  ★ New best: clauses={cl}, greedy_violations={gv} (config_408: clauses=408, viol=16)", flush=True)
        
        if cl < 408:
            print(f"    ★★★ CLAUSE BREAKTHROUGH: {cl} < 408! ★★★", flush=True)
            json.dump({"edges": full_cells, "clauses": cl, "greedy_violations": gv,
                       "nine_cells": list(c9t)},
                      open(f"{HERE}/results/enum9_brk.json", "w"))
    
    if tested % 500 == 0:
        elapsed = time.time() - t0
        print(f"  [{tested}/{total_possible}] best_cl={best_clauses}, best_v={best_violations}, {elapsed:.0f}s", flush=True)

elapsed = time.time() - t0
print(f"\n=== Enumeration complete ===")
print(f"Tested: {tested}/{total_possible} valid 9-cycles")
print(f"Best clause count: {best_clauses} (config_408: 408)")
print(f"Best greedy violations: {best_violations}")
print(f"Time: {elapsed:.0f}s")

if best_9cells:
    full_best = list(c28_tuple) + list(best_9cells)
    json.dump({"edges": full_best, "clauses": best_clauses,
               "greedy_violations": best_violations},
              open(f"{HERE}/results/enum9_result.json", "w"))
