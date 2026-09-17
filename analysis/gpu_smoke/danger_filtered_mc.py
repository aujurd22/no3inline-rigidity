#!/usr/bin/env python3
"""
Danger-filtered MC search: precompute danger via Python, then use
GPU validator to test random samples that EXCLUDE the top-K most
dangerous directions.

Hypothesis: the top few diagonal directions carry most of the
off-centre collinearity risk. If we exclude them, ANY random
selection among the rest has a much higher success rate.

This bridges the user's "GPU as validator" idea with the structural
insight (danger concentration).
"""
import sys, os, time, random
from collections import defaultdict
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

def gcd(a, b):
    a, b = abs(a), abs(b)
    while b: a, b = b, a % b
    return a or 1

def canon_dir(r, c, n):
    a, c2 = 2*r-(n-1), 2*c-(n-1)
    g = gcd(a, c2)
    a //= g; c2 //= g
    if a < 0 or (a == 0 and c2 < 0): a = -a; c2 = -c2
    return (a, c2)

def r180(p, n): return (n-1-p[0], n-1-p[1])

def collinear(p, q, r):
    return (q[0]-p[0])*(r[1]-p[1]) == (q[1]-p[1])*(r[0]-p[0])

def forbidden_triple(oi, oj, ok, n):
    pts = [oi, r180(oi,n), oj, r180(oj,n), ok, r180(ok,n)]
    for a,b,c in combinations(range(6),3):
        if collinear(pts[a],pts[b],pts[c]): return True
    return False

def build_orbit_space(n):
    orbits = []
    dir_to_indices = defaultdict(list)
    seen = set()
    for r in range(n):
        for c in range(n):
            p = (r,c); q = r180(p,n)
            if p <= q and p not in seen:
                seen.add(p); seen.add(q)
                d = canon_dir(r,c,n)
                idx = len(orbits)
                orbits.append((p,d))
                dir_to_indices[d].append(idx)
    return orbits, dir_to_indices

def compute_danger(orbits, n):
    M = len(orbits)
    danger = [0]*M
    for i in range(M):
        for j in range(i+1,M):
            for k in range(j+1,M):
                if forbidden_triple(orbits[i][0], orbits[j][0], orbits[k][0], n):
                    danger[i] += 1; danger[j] += 1; danger[k] += 1
    return danger

def validate_candidate(orbits, indices, n):
    """CPU validator — same logic as GPU kernel."""
    pts = []
    for idx in indices:
        p = orbits[idx][0]
        pts.append(p)
        pts.append(r180(p, n))
    for a,b,c in combinations(range(len(pts)), 3):
        if collinear(pts[a], pts[b], pts[c]):
            return False
    return True

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 100000
    exclude_top = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 42

    rng = random.Random(seed); t0 = time.time()

    orbits, dir_to_indices = build_orbit_space(n)
    M = len(orbits)
    ND = len(dir_to_indices)
    print(f"n={n}  orbits={M}  directions={ND}", file=sys.stderr)

    # Compute danger degrees
    print("computing danger...", file=sys.stderr, end=" ", flush=True)
    danger = compute_danger(orbits, n)
    print("done.", file=sys.stderr)

    # Compute per-direction danger (sum of orbit dangers)
    dir_danger = {}
    for d, idxs in dir_to_indices.items():
        dir_danger[d] = sum(danger[i] for i in idxs)

    # Sort directions by danger, exclude top-K
    sorted_dirs = sorted(dir_danger.items(), key=lambda x: x[1], reverse=True)
    excluded_dirs = {d for d, _ in sorted_dirs[:exclude_top]}
    remaining_dirs = [d for d in dir_to_indices.keys() if d not in excluded_dirs]

    print(f"excluded {exclude_top} dirs: {list(excluded_dirs)[:5]}...", file=sys.stderr)
    print(f"remaining dirs: {len(remaining_dirs)}", file=sys.stderr)

    if len(remaining_dirs) < n:
        print(f"ERROR: only {len(remaining_dirs)} dirs left, need {n}", file=sys.stderr)
        return

    found = 0; tested = 0
    t_batch = time.time()
    for trial in range(trials):
        # Pick n random directions from remaining
        chosen_dirs = rng.sample(remaining_dirs, n)
        # For each direction, pick a random orbit
        chosen_orbit_indices = []
        for d in chosen_dirs:
            orbs = dir_to_indices[d]
            chosen_orbit_indices.append(rng.choice(orbs))
        tested += 1
        if validate_candidate(orbits, chosen_orbit_indices, n):
            found += 1
            print(f"\nSOLUTION #{found} at trial {trial+1}", file=sys.stderr)
            for idx, d in zip(chosen_orbit_indices, chosen_dirs):
                print(f"  {orbits[idx][0]} dir={d}", file=sys.stderr)

        if (trial+1) % 10000 == 0:
            elapsed = time.time() - t_batch
            print(f"  trial {trial+1}/{trials}  found={found}  "
                  f"t={elapsed:.1f}s", file=sys.stderr)
            t_batch = time.time()

    elapsed = time.time() - t0
    pct = 100.0*found/tested if tested else 0
    print(f"\nFINAL n={n} exclude_top={exclude_top}  tested={tested}  "
          f"found={found}  hit={pct:.4f}%  time={elapsed:.1f}s",
          file=sys.stderr)

if __name__ == "__main__":
    main()
