"""Direct clause-count SA with incremental updates.
Each 2-swap only re-evaluates ~1224 affected triples (out of 7770).
~0.3s/step (incremental) — 1000 steps ≈ 5 min."""
import json, sys, os, time, math, random
from collections import Counter
from itertools import combinations

M = 37
N = 2 * M

HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

# C4 lift
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return pts

all_lifts = {}
for u in range(M):
    for v in range(M):
        all_lifts[(u, v)] = c4_lift(u, v)

def is_collinear_12(lifts):
    """Check if any 3 of 12 points are collinear."""
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

# Precompute: for each cell (u,v), its 4 lifts at both orientations
cell_data = {}
for u in range(M):
    for v in range(M):
        pts0 = all_lifts[(u, v)]  # orientation 0: (u,v)
        pts1 = all_lifts[(v, u)] if u != v else all_lifts[(u, v)]  # orientation 1: (v,u)
        cell_data[(u, v)] = (pts0, pts1)

# Helper: check a single triple (a,b,c) under ALL 8 orientation combos
# Returns number of forbidden combos (0-8)
def triple_clause_count(pts_a0, pts_a1, pts_b0, pts_b1, pts_c0, pts_c1):
    count = 0
    for oa in (0, 1):
        pa = pts_a0 if oa == 0 else pts_a1
        for ob in (0, 1):
            pb = pts_b0 if ob == 0 else pts_b1
            for oc in (0, 1):
                pc = pts_c0 if oc == 0 else pts_c1
                # Check collinearity among 12 points
                lifts = pa + pb + pc
                if is_collinear_12(lifts):
                    count += 1
    return count

def total_clauses(edges):
    """Full clause count for a config (slow, ~18s)."""
    total = 0
    for a in range(M):
        pa = cell_data[edges[a]]
        for b in range(a + 1, M):
            pb = cell_data[edges[b]]
            for c in range(b + 1, M):
                pc = cell_data[edges[c]]
                total += triple_clause_count(pa[0], pa[1], pb[0], pb[1], pc[0], pc[1])
    return total

def changed_triple_clauses(edges, changed_indices):
    """Clause count for triples involving at least one changed cell."""
    total = 0
    changed = set(changed_indices)
    for a in range(M):
        pa = cell_data[edges[a]]
        for b in range(a + 1, M):
            pb = cell_data[edges[b]]
            if a not in changed and b not in changed:
                continue
            for c in range(b + 1, M):
                if a not in changed and b not in changed and c not in changed:
                    continue
                total += triple_clause_count(pa[0], pa[1], pb[0], pb[1], 
                                             cell_data[edges[c]][0], cell_data[edges[c]][1])
    return total

def two_swap(edges, rng):
    """Valid 2-edge swap preserving 2-factor property."""
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
        return new, {a, b}
    return None, None

# ── SA: directly optimize clause count ──────────────────────────────────
def run_clause_sa(seed_fn, n_steps=2000, T0=100, alpha=0.99, rng_seed=42):
    rng = random.Random(rng_seed)
    
    # Load seed
    with open(seed_fn) as f:
        data = json.load(f)
    edges = [(min(u,v), max(u,v)) for u,v in data.get("edges", data.get("cells", []))]
    
    # Compute initial clause count
    t0 = time.time()
    print(f"Computing initial clause count (~18s)...", flush=True)
    current_cl = total_clauses(edges)
    best_cl = current_cl
    best_edges = list(edges)
    T = T0
    t_init = time.time() - t0
    
    print(f"Start: clauses={current_cl} | T0={T0} alpha={alpha} steps={n_steps} [{t_init:.0f}s]", flush=True)
    total_time = t_init
    
    for step in range(1, n_steps + 1):
        t_step = time.time()
        new_edges, changed = two_swap(edges, rng)
        if new_edges is None:
            T *= alpha
            continue
        
        # Compute delta incrementally
        # Clause count = unchanged_triples + changed_triples
        # delta = changed_new - changed_old
        changed_cl_new = changed_triple_clauses(new_edges, changed)
        
        # To compute delta, we need the OLD clause count for the same triples
        # Total = base_total - old_changed + new_changed
        # delta = new_changed - old_changed
        
        # Compute old_changed (could cache, but let's compute fresh for accuracy)
        old_changed = changed_triple_clauses(edges, changed)
        delta = changed_cl_new - old_changed
        new_cl = current_cl + delta
        
        step_time = time.time() - t_step
        total_time += step_time
        
        if new_cl < best_cl or rng.random() < math.exp(-(new_cl - current_cl) / T):
            edges = new_edges
            current_cl = new_cl
            if current_cl < best_cl:
                best_cl = current_cl
                best_edges = list(edges)
                print(f"  ★ NEW BEST: {best_cl} clauses @ step {step} [{total_time:.0f}s]", flush=True)
        
        T *= alpha
        
        if step % 200 == 0:
            rate = step / (time.time() - t0 + 1e-6)
            remaining = (n_steps - step) / rate if rate > 0 else 0
            print(f"  [{step}] curr={current_cl} best={best_cl} T={T:.2f} rate={rate:.1f}/s rem={remaining:.0f}s", flush=True)
        
        if step % 500 == 0 and best_edges:
            out = {"edges": best_edges, "clauses": best_cl, "step": step}
            with open(f"{HERE}/results/clause_sa_best_{step}.json", "w") as f:
                json.dump(out, f)
    
    elapsed = time.time() - t0
    print(f"\nClause SA Done: {n_steps} steps in {elapsed:.0f}s", flush=True)
    print(f"  Seed: {current_cl} clauses | Best: {best_cl} clauses | Δ = {best_cl - current_cl}", flush=True)
    if best_cl < 408:
        print(f"  ★★★ BREAKTHROUGH: < 408 clauses! ★★★", flush=True)
        print(f"  Estimated violations: ~{best_cl / 25.5:.1f}", flush=True)
    
    result = {"edges": best_edges, "clauses": best_cl, 
              "seed_clauses": current_cl, "steps": n_steps, "time": elapsed}
    with open(f"{HERE}/results/clause_sa_final.json", "w") as f:
        json.dump(result, f)
    return result

if __name__ == "__main__":
    seed = f"{HERE}/results/config_408_edges.json"
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    run_clause_sa(seed, n_steps=n)
