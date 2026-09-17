"""
SA search for 2-factor with minimal zero-orient clause count (GV).
0.28s/eval on full 7770 triples. Target: < 70 GV.
Uses same logic as fast_screening.py.
"""
import json, time, random, math, sys
from collections import Counter
from itertools import combinations

M = 37
N = 2 * M

# ── C4 lift precomputation (orientation 0) ─────────────────────────────────
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
    """Check if any 3 of 12 points are collinear."""
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
    """Zero-orient clause count - same as zero_orient_clause_count()."""
    total = 0
    # Unroll: 37 choose 3 = 7770
    for a in range(M):
        lifts_a = all_orbits_0[edges[a]]
        for b in range(a + 1, M):
            lifts_b = all_orbits_0[edges[b]]
            for c in range(b + 1, M):
                lifts = lifts_a + lifts_b + all_orbits_0[edges[c]]
                if check_12_fast(lifts):
                    total += 1
    return total

# ── 2-factor operations ───────────────────────────────────────────────────
def random_2factor(rng, cycle_lengths=None):
    """Generate a random 2-factor with given cycle lengths. Default [28,9]."""
    if cycle_lengths is None:
        cycle_lengths = [28, 9]
    vertices = list(range(M))
    rng.shuffle(vertices)
    edges = []
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
    return edges

def two_swap(edges, rng):
    """2-edge swap: pick 2 edges (a,i1,j1), (b,i2,j2), replace with (i1,i2), (j1,j2).
    Must preserve degree=2, no duplicate edges, no loops."""
    existing = set(edges)
    for _ in range(100):
        a = rng.randint(0, M - 1)
        b = rng.randint(0, M - 1)
        if b == a:
            continue
        i1, j1 = edges[a]
        i2, j2 = edges[b]
        if len({i1, j1, i2, j2}) < 4:
            continue
        e1 = (min(i1, i2), max(i1, i2))
        e2 = (min(j1, j2), max(j1, j2))
        if e1 in existing or e2 in existing:
            continue
        if e1 == e2:
            continue
        new = list(edges)
        new[a] = e1
        new[b] = e2
        return new
    return None

# ── SA main ────────────────────────────────────────────────────────────────
def run_sa(seed_fn=None, n_steps=50000, T0=50.0, alpha=0.998, 
           report_every=500, save_every=2000, rng_seed=42):
    rng = random.Random(rng_seed)
    
    if seed_fn:
        with open(seed_fn) as f:
            data = json.load(f)
        seed_edges = [(min(u,v), max(u,v)) for u,v in data.get("edges", data.get("cells", []))]
        if len(seed_edges) != M:
            print(f"SEED ERROR: {len(seed_edges)} edges, need {M}")
            return
        print(f"Loaded seed from {seed_fn}")
    else:
        seed_edges = random_2factor(rng, [28, 9])
        print(f"Using random [28,9] seed")
    
    # Init
    current = list(seed_edges)
    current_gv = gv(current)
    best_gv = current_gv
    best_edges = list(current)
    T = T0
    t0 = time.time()
    improvements = 0
    
    print(f"SA Start: GV={current_gv} | T0={T0} alpha={alpha} steps={n_steps}", flush=True)
    
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
                improvements += 1
                print(f"  ★ NEW BEST: GV={best_gv} @ step={step} [{time.time()-t0:.0f}s]", flush=True)
        
        T *= alpha
        
        if step % report_every == 0:
            rate = step / (time.time() - t0 + 1e-6)
            remaining = (n_steps - step) / rate if rate > 0 else 0
            print(f"  [{step}] curr={current_gv} best={best_gv} T={T:.2f} rate={rate:.1f}/s rem={remaining:.0f}s", flush=True)
        
        if save_every and step % save_every == 0 and best_edges:
            out = {"edges": best_edges, "gv": best_gv, "step": step, "improvements": improvements}
            with open(f"{base}/results/sa_gv_best_{step}.json", "w") as f:
                json.dump(out, f)
    
    elapsed = time.time() - t0
    print(f"\nSA Done: best GV={best_gv} (seed={current_gv}) | {n_steps} steps in {elapsed:.0f}s", flush=True)
    print(f"Improvements: {improvements}", flush=True)
    
    # Compare with config_408
    print(f"config_408 GV=70 | SA best={best_gv} | diff={best_gv - 70}", flush=True)
    if best_gv < 70:
        print("*** BREAKTHROUGH: GV < 70! ***", flush=True)
    elif best_gv == 70:
        print("Matched config_408. CP-SAT validation needed!", flush=True)
    
    result = {"edges": best_edges, "gv": best_gv, "current_gv": current_gv, 
              "steps": n_steps, "time": elapsed, "seed_gv": current_gv}
    with open(f"{base}/results/sa_gv_final.json", "w") as f:
        json.dump(result, f)
    print("Saved results/sa_gv_final.json", flush=True)
    return result

if __name__ == "__main__":
    import sys
    base = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"
    seed_file = f"{base}/results/config_408_edges.json"
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    run_sa(seed_fn=seed_file, n_steps=n_steps)
