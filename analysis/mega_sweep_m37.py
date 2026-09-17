#!/usr/bin/env python3
"""mega_sweep_m37.py — 10-hour exhaustive 2-factor SAT scan for m=37 rot4-NTIL.

Strategy:
- 50% Mutation from best known (varying n_swaps)
- 20% Random 2-cycle decompositions (large + small cycle)
- 20% Span-aware Hamiltonian cycles
- 10% Random multi-cycle (3-6 cycles)

Checkpoints every 25 trials to results/mega_sweep_CHECKPOINT.json.
Ctrl+C safe — resumes from checkpoint.
"""

import sys, os, json, time, math, random, argparse, shutil
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import hamiltonian_sweep as H
import solver_2factor_sat_pipeline as P
import solver_theory_m37 as S

M = 37
CHECKPOINT_INT = 25       # Save every N trials
MAXSAT_ON_NEW_BEST = True # Run full MaxSAT when we find new best
MAXSAT_TIME = 120         # Seconds for MaxSAT on promising candidates
DEEP_MAXSAT_EVERY = 200   # Deep check every N trials on current best

def generate_2cycle_decomposition(m, rng, size_large=None):
    """Generate a 2-factor with 2 cycles: one large (25-32), one small (5-12)."""
    if size_large is None:
        size_large = rng.randint(24, 32)
    size_small = m - size_large
    if size_small < 3:
        size_small = 3
        size_large = m - 3
    
    vertices = list(range(m))
    rng.shuffle(vertices)
    
    # Build large cycle
    lv = vertices[:size_large]
    edges = []
    for k in range(size_large):
        a, b = lv[k], lv[(k+1) % size_large]
        edges.append((a, b) if a <= b else (b, a))
    
    # Build small cycle
    sv = vertices[size_large:size_large + size_small]
    for k in range(size_small):
        a, b = sv[k], sv[(k+1) % size_small]
        edges.append((a, b) if a <= b else (b, a))
    
    return sorted(edges)


def generate_multi_cycle(m, rng, n_cycles):
    """Generate a 2-factor with n_cycles cycles."""
    vertices = list(range(m))
    rng.shuffle(vertices)
    
    # Partition into n_cycles roughly equal cycles
    sizes = [m // n_cycles] * n_cycles
    for i in range(m % n_cycles):
        sizes[i] += 1
    # Shuffle sizes for variety
    rng.shuffle(sizes)
    
    edges = []
    start = 0
    for sz in sizes:
        if sz >= 3:
            cv = vertices[start:start+sz]
            for k in range(sz):
                a, b = cv[k], cv[(k+1) % sz]
                edges.append((a, b) if a <= b else (b, a))
        elif sz == 2:
            # 2 vertices → 2-cycle (two parallel edges)
            a, b = vertices[start], vertices[start+1]
            edges.append((a, b) if a <= b else (b, a))
            edges.append((a, b) if a <= b else (b, a))
        elif sz == 1:
            # 1 vertex → loop
            v = vertices[start]
            edges.append((v, v))
        start += sz
    
    return sorted(edges)


def mutate_with_acceptance(best_edges, rng, n_swaps=1, rng_temp=None):
    """Mutate a 2-factor with possible two-switch. If edges is not a single 
    cycle, we use random edge-swaps that preserve degree=2."""
    if len(best_edges) != M:
        # Fallback to random generation
        return generate_2cycle_decomposition(M, rng)
    
    edges = list(best_edges)
    
    for _ in range(n_swaps):
        if rng.random() < 0.7:
            # Two-switch: replace (a,b),(c,d) with (a,c),(b,d)
            i, j = rng.sample(range(len(edges)), 2)
            u1, v1 = edges[i]
            u2, v2 = edges[j]
            if len({u1, v1, u2, v2}) >= 4:
                if rng.random() < 0.5:
                    n1 = (u1, u2) if u1 <= u2 else (u2, u1)
                    n2 = (v1, v2) if v1 <= v2 else (v2, v1)
                else:
                    n1 = (u1, v2) if u1 <= v2 else (v2, u1)
                    n2 = (v1, u2) if v1 <= u2 else (u2, v1)
                if n1[0] != n1[1] and n2[0] != n2[1]:
                    edges[i] = n1
                    edges[j] = n2
        else:
            # Single edge rewire: replace one edge while preserving degree
            # Pick a random edge, remove it, reconnect its endpoints
            # This can change cycle structure
            i = rng.randrange(len(edges))
            u, v = edges[i]
            # Find the OTHER edges incident to u and v
            u_other = [e for e in edges if e != (u,v) and (e[0]==u or e[1]==u)]
            v_other = [e for e in edges if e != (u,v) and (e[0]==v or e[1]==v)]
            if len(u_other) >= 1 and len(v_other) >= 1:
                # Pick a random incident neighbor
                u_adj = [x for e in u_other for x in e if x != u]
                v_adj = [x for e in v_other for x in e if x != v]
                if u_adj and v_adj and u_adj[0] != v_adj[0]:
                    # Rewire: (u, v_adj[0]) and (v, u_adj[0])
                    n1 = (u, v_adj[0]) if u <= v_adj[0] else (v_adj[0], u)
                    n2 = (v, u_adj[0]) if v <= u_adj[0] else (u_adj[0], v)
                    if n1[0] != n1[1] and n2[0] != n2[1]:
                        edges[i] = n1
                        # Also update the partner edges
                        for idx, e in enumerate(edges):
                            if e in [u_other[0], v_other[0]] and idx != i:
                                # Replace the endpoint in this edge
                                if e[0] == u_adj[0] or e[1] == u_adj[0]:
                                    new_e = (v, e[1]) if e[0] == u_adj[0] else (v, e[0])
                                else:
                                    new_e = (u, e[1]) if e[0] == v_adj[0] else (u, e[0])
                                edges[idx] = (new_e[0], new_e[1]) if new_e[0] <= new_e[1] else (new_e[1], new_e[0])
    
    return sorted(edges)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=M)
    ap.add_argument("--hours", type=float, default=10)
    ap.add_argument("--seed", type=int, default=20260716)
    ap.add_argument("--checkpoint-int", type=int, default=CHECKPOINT_INT)
    ap.add_argument("--resume", default="results/mega_sweep_CHECKPOINT.json",
                    help="Resume from this checkpoint file")
    ap.add_argument("--out", default="results/mega_sweep_CHECKPOINT.json")
    args = ap.parse_args()

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    rng = random.Random(args.seed)
    m = args.m
    time_budget = args.hours * 3600

    # ── Load checkpoint if exists ──
    cp_path = os.path.join(HERE, args.resume) if not os.path.isabs(args.resume) else args.resume
    out_path = os.path.join(HERE, args.out) if not os.path.isabs(args.out) else args.out

    # State
    state = {
        "trial": 0,
        "best_clauses": float("inf"),
        "best_edges": None,
        "best_orientation": None,
        "best_violations": None,
        "best_total_bad": None,
        "n_maxsat_checks": 0,
        "n_proven_optimal": 0,
        "clause_history": [],  # list of (trial, clauses)
        "violation_history": [],  # list of (trial, violations) when MaxSAT done
        "start_time": time.time(),
        "tested_2factors": 0,
        "found_sat": False,
        "sat_edges": None,
        "sat_cells": None,
        "strategy_counts": Counter(),
    }

    if os.path.exists(cp_path):
        with open(cp_path) as f:
            saved = json.load(f)
        # Merge saved state (preserve keys that overlap)
        for k in ["trial", "best_clauses", "best_violations", "best_total_bad",
                  "n_maxsat_checks", "n_proven_optimal", "clause_history",
                  "violation_history", "tested_2factors", "found_sat",
                  "strategy_counts"]:
            if k in saved:
                state[k] = saved[k]
        if saved.get("best_edges"):
            state["best_edges"] = [tuple(e) for e in saved["best_edges"]]
        if saved.get("best_orientation"):
            state["best_orientation"] = list(saved["best_orientation"])
        print(f"🔄 Resumed from checkpoint: trial={state['trial']}, "
              f"best_clauses={state['best_clauses']}, "
              f"n_tested={state['tested_2factors']}", flush=True)
    else:
        # Seed from best known (448-clause winner)
        try:
            with open(os.path.join(HERE, "results/hamiltonian_mutate.json")) as f:
                sd = json.load(f)
            state["best_clauses"] = sd["best"]
            state["best_edges"] = [tuple(e) for e in sd["best_edges"]]
            print(f"🌱 Seeded from 448-clause winner: {state['best_clauses']} clauses", flush=True)
        except:
            print("⚠️  No seed file, starting from scratch", flush=True)

    # ── Strategy weights ──
    STRATS = [
        ("mutation_light", 0.30),    # 1-3 swaps from best
        ("mutation_heavy", 0.20),    # 4-8 swaps from best
        ("two_cycle", 0.20),         # 2-cycle decompositions
        ("hamiltonian_span", 0.20),  # Span-aware Hamiltonian cycles
        ("multi_cycle", 0.10),       # 3-6 cycles
    ]
    
    def pick_strategy():
        r = rng.random()
        cum = 0
        for name, weight in STRATS:
            cum += weight
            if r <= cum:
                return name
        return STRATS[-1][0]

    def generate_candidate(strategy):
        """Generate a candidate 2-factor using the chosen strategy."""
        if strategy.startswith("mutation"):
            if state["best_edges"] and len(state["best_edges"]) == m:
                if strategy == "mutation_light":
                    ns = rng.randint(1, 3)
                else:
                    ns = rng.randint(4, 8)
                edges = mutate_with_acceptance(state["best_edges"], rng, ns)
            else:
                edges = generate_2cycle_decomposition(m, rng)
            return sorted(set(edges))
        elif strategy == "two_cycle":
            return generate_2cycle_decomposition(m, rng)
        elif strategy == "hamiltonian_span":
            min_s = rng.randint(1, 6)
            return H.span_aware_hamiltonian(m, rng, min_span=min_s)
        elif strategy == "multi_cycle":
            nc = rng.randint(3, 6)
            return generate_multi_cycle(m, rng, nc)
        return generate_2cycle_decomposition(m, rng)

    t_start = time.time()
    print(f"🚀 Starting exhaustive m={m} scan for {args.hours}h ({time_budget:.0f}s)", flush=True)
    print(f"   Strategy weights: {STRATS}", flush=True)
    print(f"   Checkpoint every {args.checkpoint_int} trials", flush=True)
    print(f"   Output: {out_path}", flush=True)

    # ── Main loop ──
    while True:
        elapsed = time.time() - t_start
        if elapsed > time_budget:
            print(f"\n⏰ Time budget reached ({elapsed:.0f}s ≥ {time_budget:.0f}s)", flush=True)
            break

        state["trial"] += 1

        # Pick and apply strategy
        strat = pick_strategy()
        state["strategy_counts"][strat] += 1
        edges = generate_candidate(strat)
        if len(edges) != m:
            continue
        state["tested_2factors"] += 1

        # Fast clause count
        n_clauses = H.count_clauses_fast(m, edges)
        state["clause_history"].append((state["trial"], n_clauses, strat))

        # Check if new best
        is_new_best = n_clauses < state["best_clauses"]
        if is_new_best:
            old_best = state["best_clauses"]
            state["best_clauses"] = n_clauses
            state["best_edges"] = edges
            # Run full MaxSAT on new best
            if MAXSAT_ON_NEW_BEST and n_clauses > 0:
                state["n_maxsat_checks"] += 1
                clauses, _ = P.enumerate_clauses(m, edges, verbose=False)
                sat_res = P.check_sat(m, edges, clauses, time_limit=min(MAXSAT_TIME, max(30, n_clauses)), verbose=False)
                mv = sat_res.get("maxsat_min_violations", sat_res.get("min_violations", -1))
                sat_found = sat_res.get("sat_found", False)
                proven = sat_res.get("maxsat_proven_optimal", False)
                orient = sat_res.get("orientation", sat_res.get("maxsat_solution", []))
                state["best_violations"] = mv
                state["best_total_bad"] = mv * 4 if mv is not None and mv >= 0 else None
                state["best_orientation"] = orient
                if proven:
                    state["n_proven_optimal"] += 1
                if sat_found or (mv is not None and mv == 0):
                    state["found_sat"] = True
                    state["sat_edges"] = edges
                    state["sat_cells"] = []
                    for idx, (u, v) in enumerate(edges):
                        if u == v:
                            state["sat_cells"].append((u, u))
                        elif orient[idx] == 0:
                            state["sat_cells"].append((u, v))
                        else:
                            state["sat_cells"].append((v, u))
                    print(f"\n{'='*60}", flush=True)
                    print(f"*** 🚀 BREAKTHROUGH! SAT at trial {state['trial']}! ***", flush=True)
                    print(f"*** m={m} SOLVED! Violations=0 ***", flush=True)
                    print(f"{'='*60}\n", flush=True)
                    # Verify independently
                    board = S.Board(m)
                    board.build(state["sat_edges"], state["sat_cells"])
                    tb = board.verify_total()
                    print(f"   Independent verify_total: {tb}", flush=True)
                    if tb == 0:
                        print(f"   ✅ VERIFIED: m={m} has rot4-NTIL solution!", flush=True)
                else:
                    print(f"   *** NEW BEST: {old_best}→{n_clauses} clauses, "
                          f"violations={mv}, time={time.time()-t_start:.0f}s ***", flush=True)
                    if mv is not None and mv >= 0:
                        state["violation_history"].append((state["trial"], mv))
                continue

        # Periodic deep check on current best
        if state["trial"] % DEEP_MAXSAT_EVERY == 0 and state["best_edges"]:
            clauses, _ = P.enumerate_clauses(m, state["best_edges"], verbose=False)
            if len(clauses) > 0:
                state["n_maxsat_checks"] += 1
                sat_res = P.check_sat(m, state["best_edges"], clauses, time_limit=60, verbose=False)
                mv = sat_res.get("maxsat_min_violations", sat_res.get("min_violations", -1))
                if mv is not None and mv >= 0:
                    state["best_violations"] = mv
                    state["best_total_bad"] = mv * 4

        # Checkpoint
        if state["trial"] % args.checkpoint_int == 0:
            cp_data = {
                "trial": state["trial"],
                "best_clauses": state["best_clauses"],
                "best_edges": state["best_edges"],
                "best_orientation": state["best_orientation"],
                "best_violations": state["best_violations"],
                "best_total_bad": state["best_total_bad"],
                "n_maxsat_checks": state["n_maxsat_checks"],
                "n_proven_optimal": state["n_proven_optimal"],
                "found_sat": state["found_sat"],
                "tested_2factors": state["tested_2factors"],
                "clause_history": state["clause_history"][-5000:],
                "violation_history": state["violation_history"],
                "strategy_counts": dict(state["strategy_counts"]),
                "elapsed_s": round(elapsed, 1),
                "trials_per_hour": round(state["trial"] / (elapsed/3600), 1) if elapsed > 0 else 0,
            }
            # Write to temp first then rename for atomicity
            tmp = cp_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(cp_data, f, indent=2)
            shutil.move(tmp, cp_path)
            
            # Brief progress line
            rate = elapsed / max(1, state["trial"])
            eta = (time_budget - elapsed) / 3600
            print(f"  [{state['trial']:5d} trials, {elapsed/3600:.1f}h elapsed, "
                  f"{eta:.1f}h remaining, {rate:.1f}s/trial, "
                  f"best_clauses={state['best_clauses']}, "
                  f"best_violations={state['best_violations']}, "
                  f"tested={state['tested_2factors']}]", flush=True)

        # Light progress
        if state["trial"] % 100 == 0 and state["trial"] % args.checkpoint_int != 0:
            print(f"  [{state['trial']:5d} trials, {elapsed/3600:.1f}h] best={state['best_clauses']}", flush=True)

    # ── Final save ──
    final = {
        "m": m,
        "total_time_s": round(time.time() - t_start, 1),
        "total_trials": state["trial"],
        "tested_2factors": state["tested_2factors"],
        "best_clauses": state["best_clauses"],
        "best_edges": state["best_edges"],
        "best_orientation": state["best_orientation"],
        "best_violations": state["best_violations"],
        "best_total_bad": state["best_total_bad"],
        "found_sat": state["found_sat"],
        "n_maxsat_checks": state["n_maxsat_checks"],
        "n_proven_optimal": state["n_proven_optimal"],
        "strategy_counts": dict(state["strategy_counts"]),
        "clause_history": state["clause_history"],
        "violation_history": state["violation_history"],
    }
    tmp = out_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(final, f, indent=2)
    shutil.move(tmp, out_path)

    print(f"\n{'='*60}", flush=True)
    print(f"Scan complete!", flush=True)
    print(f"  Time: {final['total_time_s']:.0f}s ({final['total_time_s']/3600:.2f}h)", flush=True)
    print(f"  Trials: {final['total_trials']}", flush=True)
    print(f"  Tested 2-factors: {final['tested_2factors']}", flush=True)
    print(f"  Best clauses: {final['best_clauses']}", flush=True)
    print(f"  Best violations: {final['best_violations']}", flush=True)
    print(f"  Found SAT: {final['found_sat']}", flush=True)
    print(f"  Strategy: {final['strategy_counts']}", flush=True)
    print(f"\nSeek answers in: {out_path}", flush=True)


if __name__ == "__main__":
    main()
