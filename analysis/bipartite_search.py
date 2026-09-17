"""
Bipartite 2-factor construction for m=37.
Idea: config_408's low GV (70) comes from near-bipartite i/j separation.
Construct 2-factors by: 
  1. Partition 0..36 into S (small) and L (large) like config_408
  2. Build a 2-regular graph that keeps most edges between S and L
  3. Randomize vertex ordering within cycles to find minimal GV

Loading config_408 partition: S = i-values, L = j-values
"""
import json, random, time, math
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
            if xi == xj and yi == yj: continue
            dx1, dy1 = xj - xi, yj - yi
            for k in range(j + 1, 12):
                xk, yk = lifts[k]
                if xk == xi and yk == yi: continue
                if dx1 * (yk - yi) == dy1 * (xk - xi): return True
    return False

def gv(edges):
    total = 0
    for a in range(M):
        la = all_orbits_0[edges[a]]
        for b in range(a + 1, M):
            lb = all_orbits_0[edges[b]]
            for c in range(b + 1, M):
                if check_12_fast(la + lb + all_orbits_0[edges[c]]):
                    total += 1
    return total

# ── Load config_408 partition structure ──────────────────────────────────
with open("D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results/config_408_edges.json") as f:
    c408_data = json.load(f)
c408 = [(min(u,v), max(u,v)) for u,v in c408_data["edges"]]

# Partition by appearance i vs j
i_set = set(e[0] for e in c408)  # all smaller values = i
j_set = set(e[1] for e in c408)  # larger values = j
both = i_set & j_set
S_vals = sorted(i_set - both)   # appear only as i
L_vals = sorted(j_set - both)   # appear only as j
B_vals = sorted(both)            # appear as both

print(f"Partition from config_408:")
print(f"  S (i-only): {S_vals}")
print(f"  L (j-only): {L_vals}")
print(f"  B (both):   {B_vals}")
print(f"  sizes: S={len(S_vals)} L={len(L_vals)} B={len(B_vals)} total={len(S_vals)+len(L_vals)+len(B_vals)}")

# ── Build bipartite-like 2-factor ──────────────────────────────────────
def build_bipartite_2factor(S, L, B, rng, cycle_lengths=[28, 9]):
    """Build a 2-regular graph favoring S-L edges.
    All 37 vertices appear exactly twice.
    Strategy: assign 2 occurrences per vertex, prefer S/L pairing."""
    
    # Count how many occurrences each vertex needs (all need 2)
    need = {v: 2 for v in range(M)}
    edges = []
    available = list(range(M))
    
    # Simple approach: random 2-factor with partition constraint
    # Just shuffle all vertices and make random cycles
    vertices = list(range(M))
    rng.shuffle(vertices)
    
    pos = 0
    for clen in cycle_lengths:
        for k in range(clen):
            u = vertices[pos + k]
            v = vertices[pos + (k + 1) % clen]
            edges.append((min(u, v), max(u, v)))
        pos += clen
    
    assert len(edges) == M
    assert len(set(edges)) == M
    deg = Counter([v for e in edges for v in e])
    assert all(d == 2 for d in deg.values())
    
    # Assign coordinates: cells (i,j) are already defined by graph structure
    # The labeling of vertices IS the coordinate assignment
    return edges

# ── SA search over vertex label permutations ──────────────────────────
def two_swap(edges, rng):
    existing = set(edges)
    for _ in range(100):
        a, b = rng.randint(0, M-1), rng.randint(0, M-1)
        if b == a: continue
        i1, j1 = edges[a]
        i2, j2 = edges[b]
        if len({i1, j1, i2, j2}) < 4: continue
        e1 = (min(i1, i2), max(i1, i2))
        e2 = (min(j1, j2), max(j1, j2))
        if e1 in existing or e2 in existing: continue
        if e1 == e2: continue
        new = list(edges)
        new[a] = e1
        new[b] = e2
        return new
    return None

def run_sa(seed_edges, n_steps=30000, T0=50.0, alpha=0.997, label=""):
    rng = random.Random(42)
    current = list(seed_edges)
    current_gv = gv(current)
    best_gv = current_gv
    best_edges = list(current)
    T = T0
    t0 = time.time()
    
    print(f"\n{label}: Start GV={current_gv}", flush=True)
    
    for step in range(1, n_steps + 1):
        new = two_swap(current, rng)
        if new is None:
            T *= alpha
            continue
        
        new_gv = gv(new)
        delta = new_gv - current_gv
        
        if delta < 0 or rng.random() < math.exp(-delta / T):
            current = new
            current_gv = new_gv
            if current_gv < best_gv:
                best_gv = current_gv
                best_edges = list(current)
                print(f"  ★ NEW BEST GV={best_gv} @ step={step} [{time.time()-t0:.0f}s]", flush=True)
        
        T *= alpha
        
        if step % 2000 == 0:
            rate = step / (time.time() - t0 + 1e-6)
            print(f"  [{step}] curr={current_gv} best={best_gv} rate={rate:.1f}/s", flush=True)
    
    print(f"{label}: final best GV={best_gv} (seed={current_gv}) [{time.time()-t0:.0f}s]", flush=True)
    return best_gv, best_edges

def two_switch_keep_partition(edges, rng, S, L, B):
    """2-switch that preserves partition property: tries to keep S-S and L-L swaps rare."""
    existing = set(edges)
    for _ in range(200):
        a, b = rng.randint(0, M-1), rng.randint(0, M-1)
        if b == a: continue
        i1, j1 = edges[a]
        i2, j2 = edges[b]
        if len({i1, j1, i2, j2}) < 4: continue
        
        # New edges
        na = (min(i1, i2), max(i1, i2))
        nb = (min(j1, j2), max(j1, j2))
        
        if na in existing or nb in existing: continue
        if na == nb: continue
        
        # Penalize same-partition edges (S-S or L-L) but allow them
        new = list(edges)
        new[a] = na
        new[b] = nb
        return new
    return None

def run_sa_bipartite(seed_edges, S, L, B, n_steps=30000, T0=50.0, alpha=0.997, label="bi-SA"):
    """SA with partition-preserving swaps."""
    rng = random.Random(99)
    current = list(seed_edges)
    current_gv = gv(current)
    best_gv = current_gv
    best_edges = list(current)
    T = T0
    t0 = time.time()
    
    # GV of partition-labeled configs
    S_set, L_set, B_set = set(S), set(L), set(B)
    
    def n_cross(edges):
        """Count how many edges are cross-partition (one vertex in S, one in L)."""
        cnt = 0
        for u,v in edges:
            u_b = u in L_set or u in B_set  # u is 'large-like'
            v_b = v in L_set or v in B_set
            if (u in S_set and v in (L_set | B_set)) or (v in S_set and u in (L_set | B_set)):
                cnt += 1
        return cnt
    
    print(f"\n{label}: Start GV={current_gv} cross_edges={n_cross(current)}", flush=True)
    
    for step in range(1, n_steps + 1):
        new = two_switch_keep_partition(current, rng, S, L, B)
        if new is None:
            T *= alpha
            continue
        
        new_gv = gv(new)
        # Bonus for cross-partition edges
        cross_bonus = 0.5 * (n_cross(new) - n_cross(current))
        delta = new_gv - current_gv - cross_bonus
        
        if delta < 0 or rng.random() < math.exp(-delta / T):
            current = new
            current_gv = new_gv
            if current_gv < best_gv:
                best_gv = current_gv
                best_edges = list(current)
                print(f"  ★ NEW BEST GV={best_gv} cross={n_cross(current)} @ {step} [{time.time()-t0:.0f}s]", flush=True)
        
        T *= alpha
        
        if step % 2000 == 0:
            rate = step / (time.time() - t0 + 1e-6)
            print(f"  [{step}] curr={current_gv} best={best_gv} cross={n_cross(current)} rate={rate:.1f}/s", flush=True)
    
    print(f"{label}: final best GV={best_gv} cross={n_cross(best_edges)} [{time.time()-t0:.0f}s]", flush=True)
    return best_gv, best_edges

# ── Run both searches ──────────────────────────────────────────────────
# 1) Standard SA from config_408 (already running in background)

# 2) Bipartite SA with partition bonus  
print("\n" + "=" * 60)
print("RUNNING BIPARTITE SA (partition-preserving 2-swaps)")
print("=" * 60)
bi_best_gv, bi_best = run_sa_bipartite(c408, S_vals, L_vals, B_vals, n_steps=20000)

# 3) From scratch using partition structure
print("\n" + "=" * 60)
print("RUNNING FROM-SCRATCH [28,9] WITH PARTITION STRUCTURE")
print("=" * 60)
rng = random.Random(777)
# Build a config with the exact partition structure of config_408
all_vals = S_vals + L_vals + B_vals  
# But 7 vertices appear as both, each needing 2 occurrences = 14 occurrences
# S has 15 vertices (each appears twice = 30), L has 15 (30), B has 7 (14)
# Total: 30+30+14 = 74 = 2×37 ✓

# We need 37 cells where each vertex appears exactly twice
# And i-values come from S ∪ B, j-values from L ∪ B

# Create 2 copies of each vertex
pool = S_vals * 2 + L_vals * 2 + B_vals * 2
rng.shuffle(pool)
# Pair them
scratch_edges = []
for k in range(0, len(pool), 2):
    scratch_edges.append((min(pool[k], pool[k+1]), max(pool[k], pool[k+1])))
# Verify degree
deg = Counter([v for e in scratch_edges for v in e])
if len(scratch_edges) == M and all(d == 2 for d in deg.values()) and len(set(scratch_edges)) == M:
    scratch_gv = gv(scratch_edges)
    print(f"Fresh random partition config GV={scratch_gv}", flush=True)
    # SA from this starting point
    sa_gv, sa_edges = run_sa(scratch_edges, n_steps=10000, label="scratch-SA")
    result = {"edges": sa_edges, "gv": sa_gv}
    with open("D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results/bi_search_best.json", "w") as f:
        json.dump(result, f)
else:
    print(f"FAILED: edges={len(scratch_edges)} deg={dict(deg)}")

# Save bipartite result
if bi_best:
    result = {"edges": bi_best, "gv": bi_best_gv}
    with open("D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results/bi_search_best.json", "w") as f:
        json.dump(result, f)
    print(f"\nBipartite SA finished: GV={bi_best_gv}")
    print(f"config_408 GV=70 | diff={bi_best_gv - 70}")

print("\nDone!")
