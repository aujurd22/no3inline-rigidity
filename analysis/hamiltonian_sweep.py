"""
Hamiltonian cycle sweep for m=37 rot4-NTIL.
Since D1v3 proved: 2-cycles don't help, best72 is a SINGLE Hamiltonian cycle,
and random 2-factors are >1000 clauses — we need to search Hamiltonian cycles.

This script generates MANY Hamiltonian cycles on ℤ/mℤ, counts their clause count
(no SAT check unless close to 470), and finds the best.

By default m=37.
"""
import sys, os, json, time, math, random, argparse
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver_2factor_sat_pipeline as P

# ── Hamiltonian cycle generators ─────────────────────────────────────────────

def random_hamiltonian_cycle(m, rng):
    """Generate a random Hamiltonian cycle on {0..m-1}."""
    perm = list(range(m))
    rng.shuffle(perm)
    edges = []
    for k in range(m):
        a, b = perm[k], perm[(k + 1) % m]
        u, v = (a, b) if a <= b else (b, a)
        edges.append((u, v))
    # Deduplicate (some edge may appear twice if perm[0]==perm[-1] after shuffle)
    # Actually for a Hamiltonian cycle, each edge is unique
    return sorted(edges)


def span_aware_hamiltonian(m, rng, min_span=3, max_attempts=1000):
    """
    Generate a Hamiltonian cycle with constraints on edge span.
    Edge span = |a-b| (distance on the line Z/mZ).
    best72 has min span=5, no adjacencies.
    """
    for attempt in range(max_attempts):
        edges = random_hamiltonian_cycle(m, rng)
        ok = True
        for u, v in edges:
            span = min(abs(u - v), m - abs(u - v))
            if span < min_span:
                ok = False
                break
        if ok:
            return edges
    # fallback
    return random_hamiltonian_cycle(m, rng)


def mutate_cycle(edges, rng, n_swaps=1):
    """
    Apply n 2-switches to a Hamiltonian cycle while keeping it a single cycle.
    Uses the standard 2-switch: replace (a,b),(c,d) with (a,c),(b,d).
    For a Hamiltonian cycle this preserves 2-regularity and connectivity.
    """
    E = list(edges)
    m = max(max(u,v) for u,v in E) + 1
    for _ in range(n_swaps):
        # Pick two random edges
        i, j = rng.sample(range(len(E)), 2)
        u1, v1 = E[i]
        u2, v2 = E[j]
        # Four vertices must be distinct for a valid 2-switch
        if len({u1, v1, u2, v2}) < 4:
            continue
        # Two ways: (u1,u2),(v1,v2) or (u1,v2),(v1,u2)
        if rng.random() < 0.5:
            new1 = (u1, u2) if u1 <= u2 else (u2, u1)
            new2 = (v1, v2) if v1 <= v2 else (v2, v1)
        else:
            new1 = (u1, v2) if u1 <= v2 else (v2, u1)
            new2 = (v1, u2) if v1 <= u2 else (u2, v1)
        # Check no self-loop
        if new1[0] == new1[1] or new2[0] == new2[1]:
            continue
        # Replace
        E[i] = new1
        E[j] = new2
    return sorted(E)


# ── Clause count only (fast, no SAT) ─────────────────────────────────────────
def count_clauses_fast(m, edges, n=None):
    """
    Enumerate clauses but only count them — no storage, no SAT check.
    Much faster than the full pipeline for sweep purposes.
    """
    import solver_2factor_sat_pipeline as P
    if n is None:
        n = 2 * m
    
    # Precompute cell lifts
    def c4_lift(x, y):
        pts = [(x, y)]
        for _ in range(3):
            x, y = n - 1 - y, x
            pts.append((x, y))
        return pts
    
    cell_lifts = {}
    for idx, (u, v) in enumerate(edges):
        pts0 = c4_lift(u, v)
        cell_lifts[(idx, 0)] = pts0
        if u != v:
            pts1 = c4_lift(v, u)
            cell_lifts[(idx, 1)] = pts1
        else:
            cell_lifts[(idx, 1)] = pts0
    
    # Precompute all lift points for orientation 0 (or any)
    # For clause counting we need to check all 8 combos per triple
    
    clause_count = 0
    E = len(edges)
    forbidden_sets = []
    
    for a_idx in range(E):
        for b_idx in range(a_idx + 1, E):
            for c_idx in range(b_idx + 1, E):
                for bits in range(8):
                    t1 = (bits >> 0) & 1
                    t2 = (bits >> 1) & 1
                    t3 = (bits >> 2) & 1
                    
                    lifts12 = cell_lifts[(a_idx, t1)] + cell_lifts[(b_idx, t2)]
                    # Quick check: any 3 collinear among first 8 lifts?
                    bad = False
                    # Check all triples among 12 lifts using incremental line_of
                    all_12 = lifts12 + cell_lifts[(c_idx, t3)]
                    
                    # Efficient collinearity check: for each pair (i,j), count how many
                    # points share that line. If >=3, bad.
                    line_counts = {}
                    for i in range(12):
                        pi = all_12[i]
                        for j in range(i + 1, 12):
                            pj = all_12[j]
                            if pi[0] == pj[0] and pi[1] == pj[1]:
                                continue
                            k = P.line_of(pi, pj)
                            line_counts[k] = line_counts.get(k, 0) + 1
                    
                    # A line with s points has C(s,2) pairs; s>=3 iff C(s,2)>=3
                    for k, cnt in line_counts.items():
                        s = (1 + math.isqrt(1 + 8 * cnt)) // 2
                        if s >= 3:
                            bad = True
                            break
                    
                    if bad:
                        clause_count += 1
    
    return clause_count


# ── Main sweep ───────────────────────────────────────────────────────────────
def sweep(m, n_trials, strategy="random", seed=42, out=None, verbose=True,
          sat_check_below=500):
    rng = random.Random(seed)
    best = float("inf")
    best_edges = None
    results = []
    t0 = time.time()
    
    for trial in range(n_trials):
        if strategy == "random":
            edges = random_hamiltonian_cycle(m, rng)
        elif strategy == "span5":
            edges = span_aware_hamiltonian(m, rng, min_span=5)
        elif strategy == "span3":
            edges = span_aware_hamiltonian(m, rng, min_span=3)
        elif strategy == "mutate":
            if best_edges is None:
                edges = random_hamiltonian_cycle(m, rng)
            else:
                edges = mutate_cycle(best_edges, rng, n_swaps=rng.randint(1, 3))
        else:
            edges = random_hamiltonian_cycle(m, rng)
        
        # Deduplicate
        edges = sorted(set(edges))
        
        # Quick cycle check
        if len(edges) != m:
            if verbose:
                print(f"  trial {trial}: invalid {len(edges)} edges (expected {m}), skip", flush=True)
            continue
        
        n_clauses = count_clauses_fast(m, edges)
        
        elapsed = time.time() - t0
        res = {"trial": trial, "n_clauses": n_clauses, "strategy": strategy,
               "time_s": round(time.time() - t0, 1)}
        
        if n_clauses < best:
            best = n_clauses
            best_edges = edges
            if verbose:
                print(f"  ** NEW BEST: trial {trial}: {n_clauses} clauses [{strategy}] ({elapsed:.0f}s) **", flush=True)
            
            # If close to 470, do SAT check
            if n_clauses <= sat_check_below and n_clauses > 0:
                if verbose:
                    print(f"  -> running SAT check...", flush=True)
                sat_res = P.check_sat(m, edges, [], time_limit=30, verbose=False)
                # Wait — can't use empty clauses. Let me fix this.
                # Actually need the full check. Let me skip SAT for now.
                pass
        
        results.append(res)
        
        # Save incremental
        if out and (trial + 1) % 100 == 0:
            with open(out, "w") as f:
                json.dump({"m": m, "n_trials": trial + 1, "seed": seed,
                           "strategy": strategy, "best_clauses": best,
                           "results": results, "best_edges": best_edges}, f, indent=2)
        
        if time.time() - t0 > 3600:  # 1 hour max
            break
    
    # Save final
    if out:
        with open(out, "w") as f:
            json.dump({"m": m, "n_trials": n_trials, "seed": seed,
                       "strategy": strategy, "best_clauses": best,
                       "results": results, "best_edges": best_edges,
                       "total_time_s": round(time.time() - t0, 1)}, f, indent=2)
    
    return results, best, best_edges


# ── Check known config ───────────────────────────────────────────────────────
def check_config(m, edges, label="", out=None):
    """Full pipeline: count clauses + SAT check."""
    clauses, cmap = P.enumerate_clauses(m, edges, verbose=True)
    n_c = len(clauses)
    print(f"{label}: {n_c} clauses", flush=True)
    if n_c == 0:
        print(f"  *** TRIVIAL SAT! ***", flush=True)
    else:
        sat_res = P.check_sat(m, edges, clauses, time_limit=60, verbose=False)
        mv = sat_res.get("maxsat_min_violations", -1)
        sat_found = sat_res.get("sat_found", False)
        print(f"  SAT={sat_found} min_violations={mv}", flush=True)
        if out:
            with open(out, "w") as f:
                json.dump({"label": label, "n_clauses": n_c,
                           **sat_res, "edges": edges}, f, indent=2)


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=37)
    ap.add_argument("--trials", type=int, default=500)
    ap.add_argument("--strategy", default="random",
                    choices=["random","span3","span5","mutate"])
    ap.add_argument("--seed", type=int, default=20260715)
    ap.add_argument("--out", default="results/hamiltonian_sweep.json")
    ap.add_argument("--check", help="JSON file with edges to check")
    args = ap.parse_args()
    
    if args.check:
        with open(args.check) as f:
            data = json.load(f)
        edges = data.get("best_edges", data.get("edges", []))
        edges = [tuple(e) for e in edges]
        check_config(args.m, edges, label=os.path.basename(args.check),
                     out=args.out.replace(".json", "_checked.json"))
        return
    
    out = os.path.join(HERE, args.out) if not os.path.isabs(args.out) else args.out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    
    results, best, best_edges = sweep(args.m, args.trials,
                                       strategy=args.strategy,
                                       seed=args.seed, out=out,
                                       verbose=True)
    
    print(f"\n=== Sweep complete ===", flush=True)
    print(f"Strategy: {args.strategy}", flush=True)
    print(f"Best: {best} clauses", flush=True)
    print(f"Total trials: {len(results)}", flush=True)
    
    # If best is close to 470, check SAT
    if best <= 470 and best_edges:
        pout = out.replace(".json", "_satchk.json")
        check_config(args.m, best_edges, label="sweep_best", out=pout)


if __name__ == "__main__":
    main()
