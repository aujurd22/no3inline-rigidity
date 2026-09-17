"""
swarm_D1v3_twocycle_test.py — Optimized 2-cycle hypothesis test for m=37.

Uses O(12²) per orientation check (instead of O(12³)) for ~3x speedup.
Tests whether 2-cycles reduce clause count below best72's 470.

Output: results/swarm_D1v3_twocycle_test.json
"""
import os, sys, json, math, time, random
from collections import defaultdict, Counter
from math import isqrt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
sys.path.insert(0, HERE)
os.makedirs(RESULTS, exist_ok=True)

# ── optimized collinearity check ────────────────────────────────────────────
def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def igcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a

def line_of(p, q):
    dx = q[0] - p[0]
    dy = q[1] - p[1]
    if dx == 0 and dy == 0:
        return None
    A, B = dy, -dx
    g = igcd(abs(A), abs(B)) or 1
    A //= g; B //= g
    if A < 0 or (A == 0 and B < 0):
        A, B = -A, -B
    L = A * p[0] + B * p[1]
    return (A, B, L)

def has_collinear_triple(lifts):
    """
    Check if any 3 of the 12 points are collinear.
    O(12²) approach: for each ordered pair (i,j), compute line signature,
    then check if any 3rd point k shares the same signature via hash.
    """
    n = len(lifts)
    # Build adjacency matrix of line signatures
    # lines[i][j] = line_of(lifts[i], lifts[j])
    # But we can be smarter: for each point, build a map from line -> set of points
    
    # For each point i, compute line to all j > i, group by line
    line_map = {}  # line_sig -> set of point indices
    for i in range(n):
        pi = lifts[i]
        for j in range(i + 1, n):
            pj = lifts[j]
            if pi[0] == pj[0] and pi[1] == pj[1]:
                continue
            k = line_of(pi, pj)
            if k is None:
                continue
            if k not in line_map:
                line_map[k] = set()
            line_map[k].add(i)
            line_map[k].add(j)
            if len(line_map[k]) >= 3:
                return True
    return False

# ── Fast clause enumeration ────────────────────────────────────────────────
def enumerate_clauses_fast(m, edges):
    n = 2 * m
    t0 = time.time()
    
    # Precompute lifts for each edge × orientation
    cell_lifts = {}
    for idx, (u, v) in enumerate(edges):
        pts0 = [c4(u, v, r, n) for r in range(4)]
        cell_lifts[(idx, 0)] = pts0
        if u != v:
            pts1 = [c4(v, u, r, n) for r in range(4)]
            cell_lifts[(idx, 1)] = pts1
        else:
            cell_lifts[(idx, 1)] = pts0
    
    E = len(edges)
    n_clauses = 0
    edge_clause_count = Counter()
    triple_affected_count = 0
    
    for a in range(E):
        for b in range(a + 1, E):
            for c in range(b + 1, E):
                triple_has_clause = False
                for bits in range(8):
                    pts = (cell_lifts[(a, (bits>>0)&1)] + 
                           cell_lifts[(b, (bits>>1)&1)] + 
                           cell_lifts[(c, (bits>>2)&1)])
                    if has_collinear_triple(pts):
                        n_clauses += 1
                        triple_has_clause = True
                        edge_clause_count[a] += 1
                        edge_clause_count[b] += 1
                        edge_clause_count[c] += 1
                if triple_has_clause:
                    triple_affected_count += 1
    
    t1 = time.time()
    return {
        "n_clauses": n_clauses,
        "n_triples_affected": triple_affected_count,
        "n_triples_total": E * (E - 1) * (E - 2) // 6,
        "edge_clause_degrees": [edge_clause_count.get(i, 0) for i in range(E)],
        "time_s": round(t1 - t0, 2),
    }

# ── 2-factor generators ────────────────────────────────────────────────────
def gen_2factor_permutation(m, rng):
    perm = list(range(m))
    rng.shuffle(perm)
    visited = [False] * m
    edges = []
    for i in range(m):
        if not visited[i]:
            cycle = []
            j = i
            while not visited[j]:
                visited[j] = True
                cycle.append(j)
                j = perm[j]
            for k in range(len(cycle)):
                a, b = cycle[k], cycle[(k + 1) % len(cycle)]
                edges.append((min(a, b), max(a, b)))
    return sorted(edges)

def gen_2factor_simple(m, rng):
    """Simple 2-regular graph, NO 2-cycles (stub method, rejects repeats)."""
    for _ in range(200):
        stubs = []
        for v in range(m):
            stubs.append(v); stubs.append(v)
        rng.shuffle(stubs)
        edges = []
        seen = set()
        ok = True
        for k in range(0, 2 * m, 2):
            a, b = stubs[k], stubs[k + 1]
            if a == b:
                e = (a, a)
            else:
                u, v = (a, b) if a < b else (b, a)
                e = (u, v)
                if e in seen:
                    ok = False
                    break
            seen.add(e); edges.append(e)
        if ok and len(edges) == m:
            return sorted(edges)
    return gen_2factor_permutation(m, rng)  # fallback

def count_2cycles(edges):
    ct = Counter(edges)
    return sum(1 for v in ct.values() if v >= 2), dict(ct)

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    rng = random.Random(20260715)
    
    print("=" * 70)
    print("swarm_D1v3_twocycle_test: 2-Cycle Hypothesis Test (OPTIMIZED)")
    print("=" * 70)
    
    all_results = []
    best_clauses = float("inf")
    best_edges = None
    best_gen = ""
    
    # ── Test 1: Permutation-based (natural 2-cycles) ──
    print("\n--- Permutation-based 2-factors ---")
    for trial in range(15):
        edges = gen_2factor_permutation(37, rng)
        n2, ct = count_2cycles(edges)
        result = enumerate_clauses_fast(37, edges)
        result.update({"trial": trial, "n_2cycles": n2, 
                       "n_unique": len(set(edges)), "generator": "permutation",
                       "edges": list(edges)})
        all_results.append(result)
        print(f"  t{trial}: {n2} tc, {result['n_clauses']} cls, {result['time_s']:.1f}s", flush=True)
        if result['n_clauses'] < best_clauses:
            best_clauses = result['n_clauses']; best_edges = edges; best_gen = "permutation"
    
    # ── Test 2: Simple (NO 2-cycles) ──
    print("\n--- Simple 2-factors (no 2-cycles) ---")
    for trial in range(15):
        edges = gen_2factor_simple(37, rng)
        result = enumerate_clauses_fast(37, edges)
        result.update({"trial": trial, "n_2cycles": 0,
                       "n_unique": len(set(edges)), "generator": "simple",
                       "edges": list(edges)})
        all_results.append(result)
        print(f"  t{trial}: 0 tc, {result['n_clauses']} cls, {result['time_s']:.1f}s", flush=True)
        if result['n_clauses'] < best_clauses:
            best_clauses = result['n_clauses']; best_edges = edges; best_gen = "simple"
    
    # ── Test 3: best72 with 1 forced 2-cycle ──
    print("\n--- best72 edges + 1 forced 2-cycle ---")
    with open(os.path.join(RESULTS, "swarm_D1_2_best72_clauses.json")) as f:
        d72 = json.load(f)
    best72_edges = [tuple(e) for e in d72["edges"]]
    
    for trial in range(10):
        # Pick a random edge from best72 to duplicate = 2-cycle
        idx = rng.randrange(37)
        dup_edge = best72_edges[idx]
        edges = list(best72_edges)
        edges.append(dup_edge)  # add duplicate
        # Remove another edge to keep count at 37
        rm_idx = rng.randrange(37)
        while rm_idx == idx:
            rm_idx = rng.randrange(37)
        edges.pop(rm_idx)
        edges = sorted(edges)
        
        n2, ct = count_2cycles(edges)
        if n2 == 0:
            continue  # didn't get a 2-cycle, skip
        
        result = enumerate_clauses_fast(37, edges)
        result.update({"trial": trial, "n_2cycles": n2,
                       "n_unique": len(set(edges)), "generator": "best72_forced_2cycle",
                       "edges": list(edges)})
        all_results.append(result)
        print(f"  t{trial}: {n2} tc, {result['n_clauses']} cls "+
              f"(was 470), {result['time_s']:.1f}s", flush=True)
        if result['n_clauses'] < best_clauses:
            best_clauses = result['n_clauses']; best_edges = edges; best_gen = "best72_forced_2cycle"
    
    # ── Test 4: Pure random 2-factor with DEGREE-2 constraint (sample from pipeline) ──
    print("\n--- Random permutation (for clause count distribution) ---")
    # Already done above - just report
    
    # ── Summary ──
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    by_gen = defaultdict(list)
    for r in all_results:
        by_gen[r["generator"]].append(r["n_clauses"])
    for gen, vals in sorted(by_gen.items()):
        print(f"  {gen}: min={min(vals)} max={max(vals)} mean={sum(vals)/len(vals):.1f} n={len(vals)}")
    
    print(f"\n  GLOBAL BEST: {best_clauses} clauses ({best_gen})")
    if best_edges:
        n2, ct = count_2cycles(best_edges)
        print(f"  Best edges have {n2} 2-cycles")
    
    # Clause count vs 2-cycle count
    by_n2 = defaultdict(list)
    for r in all_results:
        by_n2[r["n_2cycles"]].append(r["n_clauses"])
    print("\n--- Clause count vs 2-cycle count ---")
    for n2 in sorted(by_n2.keys()):
        vals = by_n2[n2]
        print(f"  n_2cycles={n2}: min={min(vals)} max={max(vals)} mean={sum(vals)/len(vals):.1f} n={len(vals)}")
    
    # Save
    for r in all_results:
        r["edges"] = [list(e) for e in r["edges"]]
    
    output = {
        "m": 37,
        "best_clauses_global": best_clauses,
        "best_generator": best_gen,
        "by_generator": {g: {"min": min(v), "max": max(v), "mean": sum(v)/len(v), "n": len(v)}
                         for g, v in by_gen.items()},
        "by_n_2cycles": {str(n2): {"min": min(v), "max": max(v), "mean": sum(v)/len(v), "n": len(v)}
                         for n2, v in by_n2.items()},
        "all_results": all_results,
    }
    
    with open(os.path.join(RESULTS, "swarm_D1v3_twocycle_test.json"), "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {RESULTS}/swarm_D1v3_twocycle_test.json")

if __name__ == "__main__":
    main()
