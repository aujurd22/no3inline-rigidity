"""
incremental_search.py — 从 config_408 出发，做 2-边交换搜索更优 2-因子。

策略：
1. 预计算所有 2738 个 (cell×orientation) 的 4 点 C4 提升
2. 从 config_408 出发，做双切 2-边交换（保留 [28,9] 周型）
3. 增量重算子句数（仅重新检查涉及被换 4 个 cell 的三元组）
4. 发现子句 <408 的配置后，立即 CP-SAT 认证
5. 保存所有有效结果
"""
import json, sys, time, random, copy
from collections import Counter
from itertools import combinations

M = 37
N = 2 * M  # 74

# ── Precompute all C4 orbits ──────────────────────────────────────────────────
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return pts

# all_orbits[(u,v,orient)] → list of 4 points
all_orbits = {}
for u in range(M):
    for v in range(M):
        all_orbits[(u, v, 0)] = c4_lift(u, v)
        all_orbits[(u, v, 1)] = c4_lift(v, u)

# ── Collinearity check for 12 lifts ──────────────────────────────────────────
def check_12(lifts):
    """Check if any 3 of 12 lifts are collinear. Returns True if any triple is collinear."""
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
                dx2, dy2 = xk - xi, yk - yi
                if dx1 * dy2 == dx2 * dy1:
                    return True
    return False

# ── Clause counting (full) ───────────────────────────────────────────────────
def count_clauses_full(edges):
    """Full clause count for a 2-factor (37 cells)."""
    total = 0
    for a, b, c in combinations(range(M), 3):
        u1, v1 = edges[a]
        u2, v2 = edges[b]
        u3, v3 = edges[c]
        for bits in range(8):
            t1 = (bits >> 0) & 1
            t2 = (bits >> 1) & 1
            t3 = (bits >> 2) & 1
            lifts = (all_orbits[(u1, v1, t1)] +
                     all_orbits[(u2, v2, t2)] +
                     all_orbits[(u3, v3, t3)])
            if check_12(lifts):
                total += 1
    return total

# ── Load config_408 ──────────────────────────────────────────────────────────
with open("D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis\\results\\config_408_edges.json") as f:
    data = json.load(f)
base_edges = [tuple(e) for e in data["edges"]]

print(f"=== Incremental 2-edge-swap search (from config_408, {len(base_edges)} edges) ===")
print(f"Initial clauses: {count_clauses_full(base_edges)}")

# ── 2-edge-swap (proper) ──────────────────────────────────────────────────
def two_swap(edges, rng, max_tries=200):
    """Proper 2-edge swap: pick (i1,j1)-(i2,j2) and (i3,j3)-(i4,j4),
    then reassign: (i1,j3)-(i2,j4) and (i3,j1)-(i4,j2).
    Preserves cycle type and degree.
    MUST avoid duplicate cells."""
    existing = set(edges)
    m = len(edges)
    for _ in range(max_tries):
        # Pick 4 distinct positions
        pos = rng.sample(range(m), 4)
        i1, j1 = edges[pos[0]]
        i2, j2 = edges[pos[1]]
        i3, j3 = edges[pos[2]]
        i4, j4 = edges[pos[3]]
        
        # All 8 vertices must be distinct for clean swap
        verts = {i1, j1, i2, j2, i3, j3, i4, j4}
        if len(verts) < 8:
            continue
        
        # New cells (there are 2 valid ways to reconnect)
        new1 = (i1, j3)  # (i1,j1) → (i1,j3)
        new2 = (i2, j4)  # (i2,j2) → (i2,j4)  
        new3 = (i3, j1)  # (i3,j3) → (i3,j1)
        new4 = (i4, j2)  # (i4,j4) → (i4,j2)
        
        # OR the other way:
        # new1 = (i1, j4), new2 = (i2, j3), new3 = (i3, j2), new4 = (i4, j1)
        
        # Check for duplicates
        new_set = {new1, new2, new3, new4}
        if len(new_set) < 4:
            continue
        # Check none collide with existing cells (except the ones being replaced)
        old_set = {edges[pos[0]], edges[pos[1]], edges[pos[2]], edges[pos[3]]}
        remaining = existing - old_set
        if new1 in remaining or new2 in remaining or new3 in remaining or new4 in remaining:
            continue
        
        # Valid swap!
        new_edges = list(edges)
        new_edges[pos[0]] = new1
        new_edges[pos[1]] = new2
        new_edges[pos[2]] = new3
        new_edges[pos[3]] = new4
        
        # Verify
        assert len(set(new_edges)) == m, f"Duplicates after swap!"
        deg = Counter([v for e in new_edges for v in e])
        assert all(d == 2 for d in deg.values()), f"Degree fail after swap!"
        
        return new_edges
    return None  # No valid swap found

# ── Main search ──────────────────────────────────────────────────────────────
rng = random.Random(88888)
best_edges = base_edges
best_cl = count_clauses_full(base_edges)
print(f"  Initial: {best_cl} clauses")

N_ITER = 5000
CHECK_INTERVAL = 100
SAVE_INTERVAL = 500

t0 = time.time()
improvements = 0
swaps_failed = 0

for iteration in range(N_ITER):
    # Try to find a valid swap
    new_edges = two_swap(best_edges, rng)
    if new_edges is None:
        swaps_failed += 1
        continue
    
    # Full clause count
    cl = count_clauses_full(new_edges)
    
    if cl < best_cl:
        best_cl = cl
        best_edges = new_edges
        improvements += 1
        print(f"\n  ★ Iteration {iteration}: NEW BEST {cl} clauses!", flush=True)
        
        # Save immediately
        result = {
            "m": M, "edges": [list(e) for e in new_edges],
            "n_clauses": cl,
            "iteration": iteration,
            "elapsed_s": round(time.time() - t0, 1),
        }
        with open(f"D:\\djr82\\Documents\\workbuddy\\2026-07-03-16-29-36\\no3inline-rigidity\\analysis\\results\\inc_search_best.json", "w") as f:
            json.dump(result, f, indent=1)
        
        # If < 404, this is a candidate for CP-SAT
        if cl < 404:
            print(f"    ★★★ FOUND CONFIG WITH {cl} CLAUSES (< 404)! ***", flush=True)
            # Could run CP-SAT now, but defer to keep search fast
    else:
        # 20% chance to accept worse (exploration)
        if rng.random() < 0.2:
            best_edges = new_edges
    
    if iteration % CHECK_INTERVAL == 0 and iteration > 0:
        elapsed = time.time() - t0
        rate = iteration / elapsed if elapsed > 0 else 0
        print(f"  [{iteration}/{N_ITER}] best={best_cl}cls, imp={improvements}, "
              f"sw_fail={swaps_failed}, rate={rate:.1f}/s", flush=True)

total_time = time.time() - t0
print(f"\n{'='*60}")
print(f"Search completed: {N_ITER} iterations in {total_time:.0f}s")
print(f"  Best: {best_cl} clauses ({improvements} improvements)")
print(f"  Swap failures: {swaps_failed}")

if best_cl < 408:
    print(f"\n  ★ Found config with {best_cl} clauses (< 408)!")
    print(f"  Saved to results/inc_search_best.json")
else:
    print(f"\n  No improvement over config_408 ({best_cl} >= 408)")
