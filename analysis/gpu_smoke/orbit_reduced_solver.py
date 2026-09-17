#!/usr/bin/env python3
"""
Orbit-reduced no-three-in-line solver via Lemma-1 reduction.

For even n: a 2n-point R180-invariant solution = n R180-orbits with
pairwise distinct central directions and no forbidden orbit-triple.

Algorithm: DFS + backtracking over orbit space, danger-degree-biased ordering.
This is the exact analogue of n3line_gpu.cu's row-by-row DFS but operating
on the Lemma-1 reduced orbit space rather than raw grid points.

Phase 1: pure-Python prototype, validated against known Flammenkamp rot4.
Phase 2: port inner validation to CUDA for large n (74+).
"""
import sys, time, random, os
from collections import defaultdict
from itertools import combinations


# ── helpers ──────────────────────────────────────────────────────

def gcd(a, b):
    a, b = abs(a), abs(b)
    while b: a, b = b, a % b
    return a or 1

def canon_dir(r, c, n):
    a = 2 * r - (n - 1)
    b = 2 * c - (n - 1)
    g = gcd(a, b)
    return (a // g, b // g)

def r180(p, n):  return (n - 1 - p[0], n - 1 - p[1])

def collinear(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) == (q[1] - p[1]) * (r[0] - p[0])

def forbidden_triple(oi, oj, ok, n):
    pts = [oi, r180(oi,n), oj, r180(oj,n), ok, r180(ok,n)]
    for a, b, c in combinations(range(6), 3):
        if collinear(pts[a], pts[b], pts[c]): return True
    return False


# ── build orbit space ───────────────────────────────────────────

def build_orbit_space(n):
    orbits = []
    seen = set()
    for r in range(n):
        for c in range(n):
            p = (r, c); q = r180(p, n)
            if p <= q and p not in seen:
                seen.add(p); seen.add(q)
                d = canon_dir(r, c, n)
                orbits.append((p, d))
    return orbits


# ── danger degree (precomputation) ────────────────────────────────

def compute_danger(orbits, n):
    M = len(orbits)
    danger = [0] * M
    total = 0
    for i in range(M):
        for j in range(i+1, M):
            for k in range(j+1, M):
                total += 1
                if forbidden_triple(orbits[i][0], orbits[j][0], orbits[k][0], n):
                    danger[i] += 1; danger[j] += 1; danger[k] += 1
    print(f"  danger: {total} triples checked", file=sys.stderr)
    return danger


# ── core: DFS with backtracking ──────────────────────────────────

def dfs_solve(n, orbits, order, max_solutions=1, node_limit=None):
    """
    DFS over orbit space.  `order` = vertex visit order.
    Returns (solutions_found, nodes_explored, solutions).
    """
    M = len(orbits)
    S = []
    dirs_used = set()
    nodes = [0]
    solutions = []

    def dfs(pos):
        if len(solutions) >= max_solutions:
            return True
        if node_limit and nodes[0] >= node_limit:
            return False
        if len(S) == n:
            solutions.append(list(S))
            return True
        nodes[0] += 1

        for p in range(pos, M):
            vi = order[p]
            d = orbits[vi][1]
            if d in dirs_used:
                continue
            bad = False
            for si in range(len(S)):
                for sj in range(si + 1, len(S)):
                    if forbidden_triple(orbits[vi][0],
                                      orbits[S[si]][0],
                                      orbits[S[sj]][0], n):
                        bad = True
                        break
                if bad: break
            if bad: continue
            S.append(vi)
            dirs_used.add(d)
            if dfs(p + 1):
                return True
            S.pop()
            dirs_used.remove(d)
        return False

    dfs(0)
    return len(solutions), nodes[0], solutions


# ── solver entry point ───────────────────────────────────────────

def solve(n, trials=1, seed=42, verbose=True, danger_bias=True,
         max_solutions=1, node_limit=None):
    rng = random.Random(seed)
    t0 = time.time()

    orbits = build_orbit_space(n)
    M = len(orbits)
    if verbose:
        print(f"n={n}  orbits={M}  target={n}", file=sys.stderr)

    # Danger-degree ordering
    danger = None
    if danger_bias and M <= 800:
        if verbose: print("  computing danger...", file=sys.stderr, end=" ", flush=True)
        danger = compute_danger(orbits, n)
        if verbose: print("done.", file=sys.stderr)

    total_sol = 0; total_nodes = 0; best_S = []

    for trial in range(trials):
        indices = list(range(M))
        if danger:
            indices.sort(key=lambda i: danger[i])
            i = 0
            while i < len(indices):
                j = i + 1
                while j < len(indices) and danger[indices[j]] == danger[indices[i]]:
                    j += 1
                chunk = indices[i:j]; rng.shuffle(chunk)
                indices[i:j] = chunk; i = j
        else:
            rng.shuffle(indices)

        nsol, nnodes, sols = dfs_solve(
            n, orbits, indices,
            max_solutions=max_solutions - total_sol,
            node_limit=node_limit)
        total_sol += nsol; total_nodes += nnodes
        if sols: best_S = sols[0]

        elapsed = time.time() - t0
        if verbose:
            print(f"  trial {trial+1}/{trials}: found={nsol}  "
                  f"nodes={nnodes:,}  total={total_sol}  {elapsed:.1f}s",
                  file=sys.stderr)
        if total_sol >= max_solutions:
            break

    elapsed = time.time() - t0
    if verbose:
        print(f"DONE  trials={trials}  found={total_sol}  "
              f"nodes={total_nodes:,}  time={elapsed:.1f}s", file=sys.stderr)
    return best_S, total_sol, {"trials": trials, "time": elapsed, "nodes": total_nodes}


# ── verify against known Flammenkamp solutions ────────────────────

def load_rot4_solutions(n):
    HERE = os.path.dirname(os.path.abspath(__file__))
    base = os.path.join(HERE, "..", "flammenkamp_cache")
    ALPH = r"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%&@?!()[]<>{}=*+\|-/~^_:;,."
    for ext in ["", ".few"]:
        path = os.path.join(base, f"n{n}_rot4{ext}")
        if os.path.exists(path):
            sols = []
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line: continue
                    enc = line[1:]
                    pts = []
                    for pos in range(0, 2*n, 2):
                        c1 = ALPH.index(enc[pos]); c2 = ALPH.index(enc[pos+1])
                        pts.append((pos//2, c1)); pts.append((pos//2, c2))
                    sols.append(pts)
            return sols, ext or "plain"
    return None, None


def extract_orbit_seeds_from_solution(pts, n):
    used = set(); seeds = []
    for p in pts:
        rep = min(p, r180(p, n))
        if rep not in used: used.add(rep); seeds.append(rep)
    assert len(seeds) == n, f"expected {n}, got {len(seeds)}"
    return seeds


# ── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    seed   = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    max_sol = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    nlimit  = int(sys.argv[5]) if len(sys.argv) > 5 else None

    print(f"=== orbit-reduced DFS  n={n}  trials={trials}  seed={seed} ===",
          file=sys.stderr)

    best_S, nsol, stats = solve(
        n, trials=trials, seed=seed, verbose=True,
        danger_bias=True, max_solutions=max_sol, node_limit=nlimit)

    print(f"\nRESULT n={n}  solutions={nsol}  nodes={stats['nodes']:,}  "
          f"time={stats['time']:.1f}s")

    if best_S:
        orbits = build_orbit_space(n)
        print(f"SOLUTION ({len(best_S)} orbits):")
        for idx in best_S:
            pt, d = orbits[idx]
            print(f"  seed={pt}  dir={d}")

        # Verify against known solution
        known_sols, src = load_rot4_solutions(n)
        if known_sols:
            known_seeds = set(extract_orbit_seeds_from_solution(known_sols[0], n))
            found_seeds = set(orbits[i][0] for i in best_S)
            match = known_seeds == found_seeds
            print(f"\nVs Flammenkamp rot4 ({src}, {len(known_sols)} sols): "
                  f"{'MATCHES #0' if match else 'DIFFERENT (expected)'}")
