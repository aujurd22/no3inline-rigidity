#!/usr/bin/env python3
"""
Deep mutation search from best72 and mutated452 to find
Hamiltonian cycles with minimal clause count for m=37.
Uses aggressive mutation with early saving.
"""

import sys, os, json, math, time, random
from collections import defaultdict, Counter

M = 37
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hamiltonian_sweep as H
import solver_2factor_sat_pipeline as P

# ── Seeds ──
best72_edges = sorted([
    (15,34), (10,24), (3,23), (7,28), (2,23), (8,25), (16,30),
    (7,18), (3,29), (9,35), (11,17), (9,32), (12,36), (6,15),
    (6,31), (14,36), (1,19), (8,24), (20,25), (4,19), (12,27),
    (21,33), (5,35), (13,29), (1,27), (5,22), (21,32), (20,26),
    (0,33), (16,28), (14,22), (13,26), (10,17), (11,18), (2,34),
    (0,30), (4,31)
])

# Initial best: 448 or 446 from mutation
# Let's start from 452 and walk down
seeds = [
    ("best72", best72_edges, 470),
]

# Parse the 452 edges
mutated452 = sorted([
    (0,30), (0,33), (1,19), (1,27), (2,23), (2,34), (3,23), (3,29),
    (4,7), (4,19), (5,22), (5,35), (6,15), (6,31), (7,18),
    (8,24), (8,25), (9,32), (9,35), (10,17), (10,24), (11,17), (11,18),
    (12,27), (12,36), (13,26), (13,29), (14,22), (14,36),
    (15,34), (16,28), (16,30), (20,25), (20,26), (21,32), (21,33), (28,31)
])
seeds.append(("mutated452", mutated452, 452))

def fast_count(edges):
    return H.count_clauses_fast(M, edges)

def exhaustive_local_search(initial_edges, n_outer, n_inner, rng, verbose=True):
    """Exhaustive local search: at each step, try many 2-switches, accept improvements."""
    best_edges = initial_edges
    best_nc = fast_count(initial_edges)
    history = [(0, best_nc)]
    
    for outer in range(n_outer):
        improved = False
        # Try many 2-switches
        for inner in range(n_inner):
            # Pick 2 edges to swap
            e = list(best_edges)
            i, j = rng.sample(range(len(e)), 2)
            u1, v1 = e[i]
            u2, v2 = e[j]
            if len({u1, v1, u2, v2}) < 4:
                continue
            
            # Two possible new edge pairs
            candidates = []
            for (nu1, nv1, nu2, nv2) in [
                (u1, u2, v1, v2),
                (u1, v2, v1, u2),
            ]:
                if nu1 == nv1 or nu2 == nv2:
                    continue
                cand = list(e)
                cand[i] = (nu1, nv1) if nu1 <= nv1 else (nv1, nu1)
                cand[j] = (nu2, nv2) if nu2 <= nv2 else (nv2, nu2)
                candidates.append(sorted(cand))
            
            for cand in candidates:
                nc = fast_count(cand)
                if nc < best_nc:
                    best_nc = nc
                    best_edges = cand
                    improved = True
                    if verbose:
                        print(f"  outer={outer} inner={inner}: NEW BEST {nc} clauses", flush=True)
                    history.append((outer * n_inner + inner, nc))
                    break
            if improved:
                break
        
        if not improved:
            if verbose:
                print(f"  outer={outer}: no improvement (best={best_nc})", flush=True)
            break
    
    return best_edges, best_nc, history

def simulated_annealing(initial_edges, n_steps, rng, temp_start=20, temp_end=0.5, verbose=True):
    """Simulated annealing for clause minimization."""
    current_edges = initial_edges
    current_nc = fast_count(initial_edges)
    best_edges = current_edges
    best_nc = current_nc
    history = [(0, current_nc)]
    
    for step in range(n_steps):
        temp = temp_start * (temp_end / temp_start) ** (step / n_steps)
        
        # Random 2-switch
        e = list(current_edges)
        i, j = rng.sample(range(len(e)), 2)
        u1, v1 = e[i]
        u2, v2 = e[j]
        if len({u1, v1, u2, v2}) < 4:
            continue
        
        # Pick one of the two possible switches
        if rng.random() < 0.5:
            cand = list(e)
            cand[i] = (u1, u2) if u1 <= u2 else (u2, u1)
            cand[j] = (v1, v2) if v1 <= v2 else (v2, u1)
            # Fix: need to maintain edge ordering
            if (u1 <= u2):
                cand[i] = (u1, u2) 
            else:
                cand[i] = (u2, u1)
            if (v1 <= v2):
                cand[j] = (v1, v2)
            else:
                cand[j] = (v2, v1)
        else:
            cand = list(e)
            if (u1 <= v2):
                cand[i] = (u1, v2)
            else:
                cand[i] = (v2, u1)
            if (v1 <= u2):
                cand[j] = (v1, u2)
            else:
                cand[j] = (u2, v1)
        
        cand = sorted(cand)
        if len(set(cand)) != M:  # dedup check
            continue
        
        nc = fast_count(cand)
        delta = nc - current_nc
        
        if delta < 0 or rng.random() < math.exp(-delta / max(temp, 0.1)):
            current_nc = nc
            current_edges = cand
            if nc < best_nc:
                best_nc = nc
                best_edges = cand
                if verbose:
                    print(f"  step {step}: NEW BEST {nc} clauses", flush=True)
                history.append((step, nc))
    
    return best_edges, best_nc, history


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SEARCH
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 70, flush=True)
print("DEEP MUTATION SEARCH FOR m=37", flush=True)
print("=" * 70, flush=True)

all_results = {}

for name, seed_edges, baseline in seeds:
    print(f"\n{'='*70}", flush=True)
    print(f"SEED: {name} (baseline={baseline} clauses)", flush=True)
    print(f"{'='*70}", flush=True)
    
    rng = random.Random(42)
    
    # Strategy 1: Exhaustive local search
    print(f"\n--- Exhaustive local search ---", flush=True)
    e1, nc1, h1 = exhaustive_local_search(seed_edges, 200, 100, rng, verbose=True)
    print(f"  Final: {nc1} clauses", flush=True)
    
    # Strategy 2: Simulated annealing
    print(f"\n--- Simulated annealing ---", flush=True)
    rng2 = random.Random(123)
    e2, nc2, h2 = simulated_annealing(seed_edges, 500, rng2, temp_start=30, temp_end=0.1, verbose=True)
    print(f"  Final: {nc2} clauses", flush=True)
    
    all_results[name] = {
        "local_search": {"best": nc1, "edges": sorted(e1), "history": h1},
        "simulated_annealing": {"best": nc2, "edges": sorted(e2), "history": h2},
    }
    
    # Save intermediate
    out = os.path.join(HERE, "results", f"deep_mutation_{name}.json")
    with open(out, "w") as f:
        json.dump(all_results[name], f, indent=2)

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

print(f"\n{'='*70}", flush=True)
print("SUMMARY", flush=True)
print(f"{'='*70}", flush=True)

global_best = float("inf")
global_best_edges = None
global_best_method = ""

for name, results in all_results.items():
    for method, data in results.items():
        nc = data["best"]
        print(f"  {name} / {method}: {nc} clauses", flush=True)
        if nc < global_best:
            global_best = nc
            global_best_edges = data["edges"]
            global_best_method = f"{name} / {method}"

print(f"\nGlobal best: {global_best} clauses via {global_best_method}", flush=True)
print(f"Best edges: {global_best_edges}", flush=True)

# Save global best
out = os.path.join(HERE, "results", "deep_mutation_global_best.json")
with open(out, "w") as f:
    json.dump({
        "best_clauses": global_best,
        "method": global_best_method,
        "edges": global_best_edges,
    }, f, indent=2)
print(f"Saved to {out}", flush=True)
