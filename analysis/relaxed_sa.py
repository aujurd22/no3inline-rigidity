"""
Relaxed search: optimize GV + penalty for degree-2 violations.
Allows exploring cell sets that are "almost" 2-factors with much lower GV.
Then tighten degree constraint.
"""
import json, random, time, math
from collections import Counter
from itertools import combinations
import sys

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

def gv(cells):
    total = 0
    for a in range(M):
        la = all_orbits_0[cells[a]]
        for b in range(a + 1, M):
            lb = all_orbits_0[cells[b]]
            for c in range(b + 1, M):
                if check_12_fast(la + lb + all_orbits_0[cells[c]]):
                    total += 1
    return total

def degree_penalty(cells):
    """Sum of absolute deviations from degree=2."""
    deg = Counter([v for c in cells for v in c])
    return sum(abs(deg.get(i, 0) - 2) for i in range(M))

def total_cost(cells, lam=10):
    """Composite cost: GV + lambda * degree_penalty."""
    return gv(cells) + lam * degree_penalty(cells)

# Incremental cost function
def gv_incremental(cells, old_gv, changed_indices):
    """Recompute GV for a config where only specified indices changed.
    Only checks triples involving at least 1 changed cell."""
    total = 0
    changed = set(changed_indices)
    for a in range(M):
        for b in range(a + 1, M):
            if a not in changed and b not in changed:
                continue  # skip if neither is changed (triples with c also unchanged)
            for c in range(b + 1, M):
                if a not in changed and b not in changed and c not in changed:
                    continue
                if check_12_fast(all_orbits_0[cells[a]] + all_orbits_0[cells[b]] + all_orbits_0[cells[c]]):
                    total += 1
    return total

# SA with relaxed degree constraint
def run_relaxed_sa(n_steps=20000, T0=100, alpha=0.997, lam=20, rng_seed=42):
    rng = random.Random(rng_seed)
    
    # Start from config_408 (perfect 2-factor with GV=70)
    with open("D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results/config_408_edges.json") as f:
        c408 = json.load(f)
    cells = [(min(u,v), max(u,v)) for u,v in c408["edges"]]
    
    current_gv = gv(cells)
    current_pen = degree_penalty(cells)
    current_cost = current_gv + lam * current_pen
    best_gv = current_gv
    best_cells = list(cells)
    best_cost = current_cost
    T = T0
    t0 = time.time()
    steps_without_improvement = 0
    total_swaps = 0
    
    print(f"Relaxed SA Start: GV={current_gv} penalty={current_pen} cost={current_cost}", flush=True)
    print(f"  lambda={lam} T0={T0} alpha={alpha}", flush=True)
    
    for step in range(1, n_steps + 1):
        # Propose: either swap 2 cells (like 2-switch) or replace 1 cell
        if rng.random() < 0.7:  # 70%: swap 2 cells (2-switch style)
            a, b = rng.randint(0, M-1), rng.randint(0, M-1)
            if b == a: continue
            i1, j1 = cells[a]
            i2, j2 = cells[b]
            if len({i1, j1, i2, j2}) < 4: continue
            # Check for duplicate
            e1 = (min(i1, i2), max(i1, i2))
            e2 = (min(j1, j2), max(j1, j2))
            if e1 in cells or e2 in cells or e1 == e2: continue
            # Only allow if not creating duplicate
            old_set = set(cells)
            new_set = old_set - {cells[a], cells[b]} | {e1, e2}
            if len(new_set) != M: continue
            
            new_cells = list(cells)
            new_cells[a] = e1
            new_cells[b] = e2
            
            new_gv = gv(new_cells)
            new_pen = degree_penalty(new_cells)
            new_cost = new_gv + lam * new_pen
            total_swaps += 1
        else:  # 30%: replace 1 cell with a new one (can change degree!)
            old_set = set(cells)
            for _ in range(50):
                idx = rng.randint(0, M-1)
                new_cell = (rng.randint(0, M-1), rng.randint(0, M-1))
                if new_cell not in old_set:
                    break
            else:
                continue
            
            new_cells = list(cells)
            new_cells[idx] = new_cell
            
            new_gv = gv(new_cells)
            new_pen = degree_penalty(new_cells)
            new_cost = new_gv + lam * new_pen
            total_swaps += 1
        
        delta = new_cost - current_cost
        
        if delta < 0 or rng.random() < math.exp(-delta / T):
            cells = new_cells
            current_gv, current_pen, current_cost = new_gv, new_pen, new_cost
            if current_cost < best_cost:
                best_cost = current_cost
                best_gv = current_gv
                best_cells = list(cells)
                steps_without_improvement = 0
                if current_gv < 70:
                    print(f"  ★ GV={current_gv} pen={current_pen} cost={current_cost} @ {step} [{time.time()-t0:.0f}s]", flush=True)
            else:
                steps_without_improvement += 1
        else:
            steps_without_improvement += 1
        
        T *= alpha
        
        if step % 1000 == 0:
            rate = step / (time.time() - t0 + 1e-6)
            print(f"  [{step}] GV={current_gv} pen={current_pen} cost={current_cost} best_gv={best_gv} rate={rate:.1f}/s", flush=True)
        
        # Periodic save of best perfect 2-factor (penalty=0)
        if step % 2000 == 0 and best_cells and degree_penalty(best_cells) == 0 and best_gv < 70:
            out = {"edges": best_cells, "gv": best_gv}
            with open(f"D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results/relaxed_best_{step}.json", "w") as f:
                json.dump(out, f)
            print(f"  Saved perfect 2-factor with GV={best_gv}", flush=True)
    
    elapsed = time.time() - t0
    print(f"\nRelaxed SA Done: {n_steps} steps in {elapsed:.0f}s", flush=True)
    print(f"  Best: GV={best_gv} penalty={degree_penalty(best_cells)}", flush=True)
    print(f"  Total swaps: {total_swaps}", flush=True)
    
    # Save best configs
    result = {
        "best_gv": best_gv,
        "best_penalty": degree_penalty(best_cells),
        "best_cells": best_cells,
        "steps": n_steps,
        "time": elapsed,
        "lambda": lam,
    }
    with open("D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis/results/relaxed_sa_final.json", "w") as f:
        json.dump(result, f)
    
    # Also save all configs with penalty=0 and GV<70
    return result

if __name__ == "__main__":
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 15000
    lam = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    run_relaxed_sa(n_steps=n_steps, lam=lam)
