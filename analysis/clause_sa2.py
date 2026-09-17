"""Fixed clause-count SA — uses full evaluation at each step (1.5s/step).
500 steps = 12.5 min. Acceptable for a focused search from config_408."""
import json, sys, os, time, math, random
from collections import Counter

M = 37
N = 2 * M
HERE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"

# ── C4 lift ──────────────────────────────────────────────────────
def c4_lift(x, y):
    pts = [(x, y)]
    for _ in range(3):
        x, y = N - 1 - y, x
        pts.append((x, y))
    return pts

all_lifts = {(u, v): c4_lift(u, v) for u in range(M) for v in range(M)}

def is_collinear_12(lifts):
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

cell_data = {}
for u in range(M):
    for v in range(M):
        pts0 = all_lifts[(u, v)]
        pts1 = all_lifts[(v, u)] if u != v else all_lifts[(u, v)]
        cell_data[(u, v)] = (pts0, pts1)

def triple_clause_count(pa0, pa1, pb0, pb1, pc0, pc1):
    count = 0
    for oa in (0, 1):
        pa = pa0 if oa == 0 else pa1
        for ob in (0, 1):
            pb = pb0 if ob == 0 else pb1
            for oc in (0, 1):
                pc = pc0 if oc == 0 else pc1
                if is_collinear_12(pa + pb + pc):
                    count += 1
    return count

def total_clauses(edges):
    """Full evaluation, ~1.5s on M=37."""
    total = 0
    for a in range(M):
        pa = cell_data[edges[a]]
        for b in range(a + 1, M):
            pb = cell_data[edges[b]]
            for c in range(b + 1, M):
                total += triple_clause_count(pa[0], pa[1], pb[0], pb[1],
                                              cell_data[edges[c]][0], cell_data[edges[c]][1])
    return total

# ── Valid 2-edge swap ────────────────────────────────────────────
def two_swap(edges, rng):
    existing = set(edges)
    for _ in range(200):
        a, b = rng.randint(0, M-1), rng.randint(0, M-1)
        if b == a: continue
        i1, j1 = edges[a]
        i2, j2 = edges[b]
        if len({i1, j1, i2, j2}) < 4: continue
        e1 = (min(i1, i2), max(i1, i2))
        e2 = (min(j1, j2), max(j1, j2))
        # Check: e1 or e2 would duplicate an edge that ISN'T being replaced
        edges_set_without_ab = existing - {edges[a], edges[b]}
        if e1 in edges_set_without_ab or e2 in edges_set_without_ab:
            continue
        if e1 == e2: continue
        new = list(edges)
        new[a] = e1
        new[b] = e2
        return new
    return None

# ── SA ───────────────────────────────────────────────────────────
def run(n_steps=500, T0=200, alpha=0.97, rng_seed=42, seed_cycle_restart=100):
    rng = random.Random(rng_seed)
    
    with open(f"{HERE}/results/config_408_edges.json") as f:
        data = json.load(f)
    edges = [(min(u,v), max(u,v)) for u, v in data["edges"]]
    
    t0 = time.time()
    print(f"Computing seed clause count...", flush=True)
    best_cl = total_clauses(edges)
    best_edges = list(edges)
    current_cl = best_cl
    T = T0
    improvements = 0
    stalled = 0
    
    print(f"Start: clauses={best_cl} | T0={T0} steps={n_steps}", flush=True)
    
    for step in range(1, n_steps + 1):
        # Periodically restart from best config
        if step > 0 and step % seed_cycle_restart == 0:
            edges = list(best_edges)
            current_cl = best_cl
            T = min(T * 2, T0)  # Reheat
            stalled = 0
        
        new_edges = two_swap(edges, rng)
        if new_edges is None:
            stalled += 1
            if stalled > 50:
                # Random reset
                rng.shuffle(edges)
                current_cl = total_clauses(edges)
                stalled = 0
            continue
        
        new_cl = total_clauses(new_edges)
        delta = new_cl - current_cl
        
        if new_cl < best_cl or rng.random() < math.exp(-delta / T):
            edges = new_edges
            current_cl = new_cl
            if current_cl < best_cl:
                best_cl = current_cl
                best_edges = list(edges)
                improvements += 1
                print(f"  ★ {best_cl} cls @ step {step} [{time.time()-t0:.0f}s]", flush=True)
                # Save
                json.dump({"edges": best_edges, "clauses": best_cl, "step": step},
                          open(f"{HERE}/results/clause_sa_best_{step}.json", "w"))
        
        T = max(T * alpha, 1.0)
        
        if step % 50 == 0:
            rate = step / (time.time() - t0 + 1e-6)
            print(f"  [{step}] cur={current_cl} best={best_cl} T={T:.1f} {rate:.1f}/s", flush=True)
    
    elapsed = time.time() - t0
    print(f"\nDone: {n_steps} steps in {elapsed:.0f}s", flush=True)
    print(f"  Seed: from config_408", flush=True)
    print(f"  Best clauses: {best_cl} (Δ={best_cl-408})", flush=True)
    if best_cl < 408:
        print(f"  ★★★ BREAKTHROUGH: < 408 clauses!", flush=True)
    
    json.dump({"edges": best_edges, "clauses": best_cl, "steps": n_steps, "time": elapsed},
              open(f"{HERE}/results/clause_sa_final2.json", "w"))
    return best_cl

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    run(n)
