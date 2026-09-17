"""
方向 A：先定取向，再搜 2-因子。

对 config_408 的最优取向（CP-SAT 证明最优），固定取向后用 SA 搜 2-因子。
评估仅需 1 次共线检查/三元组（而非 8 次），~0.2s 每 2-因子。
"""
import json, time, random, math, sys

M = 37; N = 74
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

# ── C4 lift ──────────────────────────────────────────────────────
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3): x, y = N - 1 - y, x; pts.append((x, y))
    return pts

# Precompute all lifts for each orientation
# For a given cell (u,v) and orientation o:
#   o=0: take (u,v) as seed
#   o=1: take (v,u) as seed (transpose)
# Lift always produces 4 points (0, 90, 180, 270 degree rotations)
all_lifts = {}
for u in range(M):
    for v in range(M):
        lift0 = c4_lift(u, v)
        lift1 = c4_lift(v, u) if u != v else c4_lift(u, v)
        all_lifts[(u, v, 0)] = lift0
        all_lifts[(u, v, 1)] = lift1

def is_collinear_12(lifts):
    """Check if ANY 3 points among the 12 (4 per cell × 3 cells) are collinear."""
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

def count_clauses_fixed(edges, orientation):
    """Count clause violations under FIXED orientation.
    For each triple, check if their specific orientation combo is collinear.
    This is 1 check per triple (not 8), so ~8x faster than full eval."""
    total = 0
    for a in range(M):
        ea = edges[a]
        la = all_lifts[(ea[0], ea[1], orientation[a])]
        for b in range(a + 1, M):
            eb = edges[b]
            lb = all_lifts[(eb[0], eb[1], orientation[b])]
            for c in range(b + 1, M):
                ec = edges[c]
                lc = all_lifts[(ec[0], ec[1], orientation[c])]
                if is_collinear_12(la + lb + lc):
                    total += 1
    return total

# ── 2-factor generators ─────────────────────────────────────────
def random_2regular(cycle_lengths, rng):
    vertices = list(range(M))
    rng.shuffle(vertices)
    edges = []
    pos = 0
    for clen in cycle_lengths:
        cycle = vertices[pos:pos+clen]
        pos += clen
        for k in range(clen):
            u = cycle[k]; v = cycle[(k + 1) % clen]
            edges.append((min(u, v), max(u, v)))
    return edges

def two_swap(edges, rng):
    existing = set(edges)
    for _ in range(100):
        a, b = rng.randint(0, M-1), rng.randint(0, M-1)
        if b == a: continue
        i1, j1 = edges[a]; i2, j2 = edges[b]
        if len({i1, j1, i2, j2}) < 4: continue
        e1 = (min(i1, i2), max(i1, i2))
        e2 = (min(j1, j2), max(j1, j2))
        if e1 in existing or e2 in existing: continue
        if e1 == e2: continue
        if e1 == edges[a] or e2 == edges[b]: continue
        new = list(edges)
        new[a] = e1; new[b] = e2
        return new, {a, b}
    return None, None

def incremental_clauses_fixed(edges, changed_indices, orientation, old_total=None):
    """Recompute only triples involving changed cells (faster than full count).
    If old_total is given, compute delta instead of total."""
    changed = set(changed_indices)
    if old_total is not None:
        # Remove old contribution of affected triples
        diff = 0
        for i in range(M):
            ei = edges[i]; li = all_lifts[(ei[0], ei[1], orientation[i])]
            for j in range(i+1, M):
                if i not in changed and j not in changed: continue
                ej = edges[j]; lj = all_lifts[(ej[0], ej[1], orientation[j])]
                for k in range(j+1, M):
                    if i not in changed and j not in changed and k not in changed: continue
                    ek = edges[k]; lk = all_lifts[(ek[0], ek[1], orientation[k])]
                    if is_collinear_12(li + lj + lk):
                        diff += 1
        return diff  # Return delta (but this isn't a true delta, just the affected subset)
    else:
        total = 0
        for i in range(M):
            ei = edges[i]; li = all_lifts[(ei[0], ei[1], orientation[i])]
            for j in range(i+1, M):
                if i not in changed and j not in changed: continue
                ej = edges[j]; lj = all_lifts[(ej[0], ej[1], orientation[j])]
                for k in range(j+1, M):
                    if i not in changed and j not in changed and k not in changed: continue
                    ek = edges[k]; lk = all_lifts[(ek[0], ek[1], orientation[k])]
                    if is_collinear_12(li + lj + lk):
                        total += 1
        return total

# ── Main ─────────────────────────────────────────────────────────
def run(seed_config="config_408", n_orientations=10, n_steps=500, rng_seed=42):
    rng = random.Random(rng_seed)
    
    # ── Load seed orientation ─────────────────────────────────────
    if seed_config == "config_408":
        # Load config_408 edges and its optimal orientation
        with open(f"{HERE}/results/config_408_edges.json") as f:
            data = json.load(f)
        seed_edges = [(min(u,v), max(u,v)) for u,v in data["edges"]]
        
        # Load the optimal orientation from config_408_maxsat_result
        with open(f"{HERE}/results/config_408_maxsat_result.json") as f:
            maxsat = json.load(f)
        seed_orientation = maxsat["orientation"]
        baseline_cl = maxsat["min_violations"]
    else:
        raise ValueError(f"Unknown seed: {seed_config}")
    
    print(f"config_408: {len(seed_edges)} edges, orientation from CP-SAT", flush=True)
    print(f"Known optimal: {baseline_cl} violations (CP-SAT proven)", flush=True)
    
    # Verify: config_408 under its optimal orientation
    t0 = time.time()
    c408_fixed = count_clauses_fixed(seed_edges, seed_orientation)
    print(f"config_408 under optimal orientation: {c408_fixed} clauses (should be {baseline_cl}) [{time.time()-t0:.1f}s]", flush=True)
    
    # ── Phase 1: Search for better 2-factor under seed orientation ──
    print("\n=== Phase 1: SA search under config_408's optimal orientation ===", flush=True)
    
    best_edges = list(seed_edges)
    best_cl = c408_fixed
    current_edges = list(seed_edges)
    current_cl = c408_fixed
    T = 200
    improvements = 0
    
    for step in range(1, n_steps + 1):
        result = two_swap(current_edges, rng)
        if result is None or result[0] is None:
            continue
        new_edges, changed = result
        
        # Full eval on new config (fast: ~0.2s since fixed orientation)
        new_cl = count_clauses_fixed(new_edges, seed_orientation)
        
        delta = new_cl - current_cl
        if new_cl < best_cl or rng.random() < math.exp(-delta / max(1, T)):
            current_edges = new_edges
            current_cl = new_cl
            if new_cl < best_cl:
                best_cl = new_cl
                best_edges = list(new_edges)
                improvements += 1
                print(f"  ★ Step {step}: {best_cl} clauses (T={T:.0f})", flush=True)
                if best_cl < baseline_cl:
                    print(f"  ★★★ BREAKTHROUGH: {best_cl} < {baseline_cl}! Saving...", flush=True)
                    json.dump({"edges": best_edges, "clauses": best_cl, "orientation": seed_orientation,
                               "step": step, "type": f"phase1_fixed_orient_{seed_config}"},
                              open(f"{HERE}/results/da_breakthrough.json", "w"))
        
        T = max(T * 0.98, 5.0)
        
        if step % 100 == 0:
            elapsed = time.time() - t0
            print(f"  [{step}/{n_steps}] best={best_cl} current={current_cl} T={T:.0f} {elapsed:.0f}s", flush=True)
    
    print(f"\nPhase 1 done: best={best_cl} (vs config_408's {c408_fixed})", flush=True)
    if best_cl < c408_fixed - 5:
        print("*** SIGNIFICANT IMPROVEMENT under seed orientation! ***", flush=True)
        # Need CP-SAT verify: the optimal under free orientation might be even lower
    
    # ── Phase 2: Try perturbed orientations ──────────────────────
    print(f"\n=== Phase 2: Try {n_orientations} perturbed orientations ===", flush=True)
    
    for trial in range(n_orientations):
        # Perturb orientation: flip 2 random bits
        orient = list(seed_orientation)
        for _ in range(2):
            idx = rng.randint(0, M-1)
            orient[idx] = 1 - orient[idx]
        
        # SA from config_408 under this orientation
        edges = list(seed_edges)
        cl = count_clauses_fixed(edges, orient)
        best_for_orient = cl
        best_edges_for_orient = list(edges)
        T = 100
        
        for step in range(200):
            result = two_swap(edges, rng)
            if result is None: continue
            new_edges, changed = result
            new_cl = count_clauses_fixed(new_edges, orient)
            delta = new_cl - cl
            if new_cl < best_for_orient or rng.random() < math.exp(-delta / max(1, T)):
                edges = new_edges; cl = new_cl
                if cl < best_for_orient:
                    best_for_orient = cl
                    best_edges_for_orient = list(edges)
            T = max(T * 0.97, 5.0)
        
        print(f"  Orient {trial}: best_SA={best_for_orient} (from config_408, {best_for_orient - baseline_cl:+d} vs baseline)", flush=True)
        
        if best_for_orient < baseline_cl:
            print(f"  ★★★ BREAKTHROUGH: {best_for_orient} < {baseline_cl}! Saving...", flush=True)
            json.dump({"edges": best_edges_for_orient, "clauses": best_for_orient,
                       "orientation": orient, "trial": trial, "type": "phase2_perturbed"},
                      open(f"{HERE}/results/da_breakthrough.json", "w"))
    
    # ── Save final best ───────────────────────────────────────────
    result = {"best_cl": best_cl, "config_408_baseline": baseline_cl,
              "phase1_improvement": c408_fixed - best_cl,
              "type": "directionA_final"}
    json.dump(result, open(f"{HERE}/results/directionA_result.json", "w"))
    print(f"\n=== Final: best_cl={best_cl} config_408={baseline_cl} ===", flush=True)
    
    if best_cl < baseline_cl:
        print("*** BREAKTHROUGH: Better 2-factor found! ***", flush=True)
        return True
    else:
        print("No breakthrough under seed orientation. Phase 2 perturbations also failed.", flush=True)
        return False

if __name__ == "__main__":
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    n_orient = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    run(n_steps=n_steps, n_orientations=n_orient)
