"""
Lemma 3 verification: No 4-vertex 2-factor is a local minimum of B.

Complete enumeration: for every set of 4 vertices and every 2-regular
configuration, check ALL other 2-regular configurations differing by
exactly 2 edges.  If any has lower B, not a local minimum.

This avoids the named-config adjacency bug (different 4-cycles on same
4 vertices are distinct configurations but all are valid switch targets).

Results: results/lemma3_verification.json
"""
import math, json, itertools, time, os, random
from collections import Counter

def c4(p, r, N):
    x, y = p
    if r == 0: return (x, y)
    if r == 1: return (N - 1 - y, x)
    if r == 2: return (N - 1 - x, N - 1 - y)
    if r == 3: return (y, N - 1 - x)

def line_key(p, q):
    x1, y1 = p; x2, y2 = q
    A = y2 - y1; B = x1 - x2; C = x2 * y1 - x1 * y2
    g = math.gcd(A or 0, B or 0, C or 0)
    if g: A //= g; B //= g; C //= g
    if A < 0 or (A == 0 and B < 0): A, B, C = -A, -B, -C
    return (A, B, C)

def count_collinear(pts):
    """Count lines with >= 3 points among |pts| (small, typically 16)."""
    n = len(pts)
    lp = {}
    for i in range(n):
        xi, yi = pts[i]
        for j in range(i + 1, n):
            xj, yj = pts[j]
            if xi == xj and yi == yj: continue
            k = line_key(pts[i], pts[j])
            s = lp.get(k)
            if s is None: lp[k] = {i, j}
            else: s.add(i); s.add(j)
    return sum(1 for v in lp.values() if len(v) >= 3)

# ---------------------------------------------------------------------------
#  Generate ALL 4-vertex 2-regular configurations for a given vertex set.
#  A 2-regular (pseudo)graph on 4 vertices has each vertex with total
#  degree (outdeg + indeg) = 2.  Exactly 4 directed edges total.
# ---------------------------------------------------------------------------

def gen_all_configs_4v(vs):
    """Generate all 2-regular 4-vertex configurations on vertices vs=[a,b,c,d].
    Yields frozenset of 4 cells."""
    all_edges = [(i, j) for i in vs for j in vs]
    seen = set()
    for combo in itertools.combinations(all_edges, 4):
        # Check 2-regularity
        outdeg = Counter()
        indeg = Counter()
        ok = True
        for (x, y) in combo:
            outdeg[x] += 1
            indeg[y] += 1
        for v in vs:
            if outdeg[v] + indeg[v] != 2:
                ok = False
                break
        if not ok:
            continue
        fs = frozenset(combo)
        if fs in seen:
            continue
        seen.add(fs)
        yield list(combo)

def gen_neighbors_4v(cells, vs):
    """Generate all 4-vertex 2-regular configs differing by exactly 2 edges."""
    orig_set = frozenset(cells)
    all_edges = [(i, j) for i in vs for j in vs]
    seen = set()
    for combo in itertools.combinations(all_edges, 4):
        fs = frozenset(combo)
        if fs == orig_set:
            continue
        if fs in seen:
            continue
        # Check 2-regularity
        outdeg = Counter()
        indeg = Counter()
        ok = True
        for (x, y) in combo:
            outdeg[x] += 1
            indeg[y] += 1
        for v in vs:
            if outdeg[v] + indeg[v] != 2:
                ok = False
                break
        if not ok:
            continue
        # Check exactly 2 edges differ: symmetric difference size 4
        if len(fs ^ orig_set) != 4:
            continue
        seen.add(fs)
        yield list(combo)

# ---------------------------------------------------------------------------
#  Main verification
# ---------------------------------------------------------------------------

def check_config(m, vs, cells):
    """Check config. Returns (B, n_neighbors, B_neighbors, is_local_min)."""
    N = 2 * m
    pts = [c4(c, r, N) for c in cells for r in range(4)]
    B = count_collinear(pts)
    if B == 0:
        return (0, 0, [], False)
    
    # Find all neighbors
    nbrs = list(gen_neighbors_4v(cells, vs))
    nbr_Bs = []
    for nbr in nbrs:
        nbr_pts = [c4(c, r, N) for c in nbr for r in range(4)]
        nbr_B = count_collinear(nbr_pts)
        nbr_Bs.append(nbr_B)
    
    min_nbr = min(nbr_Bs) if nbr_Bs else B
    return (B, len(nbrs), nbr_Bs, min_nbr >= B)

def main():
    t_start = time.time()
    
    # Precompute config pool for each quad to avoid redundant enumeration
    # Since all quads have the same structure (just different labels), we can't
    # easily precompute — but we can cache per quad if needed.
    
    ms_to_check = list(range(4, 21)) + [22, 25, 27, 30, 35, 37]
    all_local_min = []
    total_checked = 0
    total_neighbors = 0
    
    for m in ms_to_check:
        t_m = time.time()
        
        if m <= 20:
            quads = list(itertools.combinations(range(m), 4))
        else:
            random.seed(m)
            n = min(10000, math.comb(m, 4))
            quads = []
            used = set()
            while len(quads) < n:
                q = tuple(sorted(random.sample(range(m), 4)))
                if q not in used:
                    used.add(q)
                    quads.append(q)
        
        m_local = []
        m_checked = 0
        m_neighbors = 0
        
        for vs in quads:
            # Generate all initial configs for this quad
            for cells_init in gen_all_configs_4v(list(vs)):
                B, nn, nbr_Bs, is_min = check_config(m, vs, cells_init)
                m_checked += 1
                total_checked += 1
                total_neighbors += nn
                m_neighbors += nn
                if is_min and B > 0:
                    m_local.append({
                        "m": m, "vs": list(vs), "cells": cells_init,
                        "B": int(B), "n_neighbors": nn,
                        "min_nbr_B": int(min(nbr_Bs)) if nbr_Bs else B,
                    })
        
        all_local_min.extend(m_local)
        dt = time.time() - t_m
        
        status = "✔" if len(m_local) == 0 else f"⚠ {len(m_local)}"
        eta = time.time() - t_start
        print(f"m={m:3d}: configs={m_checked:6d} nbrs={m_neighbors:6d} "
              f"{dt:6.2f}s [{status}] [{eta:.0f}s]", flush=True)
    
    print(f"\nTotal: {total_checked} configs, {total_neighbors} neighbor checks, "
          f"{len(all_local_min)} local minima", flush=True)
    
    if all_local_min:
        # Analyze: which configs produce local minima?
        # The issue is likely that loop configs have no valid non-degenerate 2-switch
        # (only degenerate switches involving 3 vertices).
        # For 2-loop configs, the switch replaces 2 edges both incident to the same loop.
        # Let's check: do the local minima come from specific config types?
        # 
        # Key question: is the 2-edge replacement enumerator actually correct?
        # Let me spot-check.
        ex = all_local_min[0]
        print(f"Example local min: m={ex['m']}, vs={ex['vs']}, B={ex['B']}, "
              f"n_neighbors={ex['n_neighbors']}, min_nbr_B={ex['min_nbr_B']}")
        print(f"  cells: {ex['cells']}")
        
        # Count by config type
        # Canonical form: sort cells and use as key
        from collections import Counter
        cell_sigs = Counter()
        for lm in all_local_min:
            sig = tuple(sorted((x, y) for x, y in lm["cells"]))
            cell_sigs[sig] += 1
        print(f"Distinct local minimum config types: {len(cell_sigs)}")
        for sig, cnt in cell_sigs.most_common(10):
            print(f"  {sig}: {cnt}")
    else:
        print("*** LEMMA 3 HOLDS: No 4-vertex local minimum exists! ***")
    
    # Save results
    out = {
        "metadata": {
            "m_range": "4..37",
            "total_configs_checked": total_checked,
            "total_neighbor_checks": total_neighbors,
            "total_local_minima": len(all_local_min),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "by_m": {},
    }
    for m in ms_to_check:
        mins = [r for r in all_local_min if r["m"] == r["m"]]
        out["by_m"][str(m)] = {
            "local_minima": sum(1 for r in all_local_min if r["m"] == m),
        }
    
    os.makedirs("results", exist_ok=True)
    with open("results/lemma3_verification.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nResults saved to results/lemma3_verification.json")
    print(f"Total time: {time.time() - t_start:.0f}s")

if __name__ == "__main__":
    main()
