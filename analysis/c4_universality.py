#!/usr/bin/env python3
"""
Direction 1 (highest value): C4 CONSTRUCTION EXISTENCE -- corrected study.

CORRECTION (2026-07-09, this run): the earlier "cyclic universality
conjecture" claimed full-m-cycle and (1,m-1) 2-factors yield valid C4
solutions for all m >= 10.  That claim rested on an UNSOUND verifier
(c4_constructive.py inspected only the first 5000 triples).  A SOUND
O(N^2) direction-hash check shows those two naive patterns FAIL for every
m >= 4 (the seeds (i,i+1),(i+1,i+2),(i+2,i+3) are collinear on y=x+1).

This script therefore (a) confirms the negative result soundly, (b) tests
OTHER simple 2-factor families (skip-k single cycles) to look for a true
constructive family, and (c) runs a RANDOM 2-factor search -- positive
success rates support the Lovasz Local Lemma existence route for large m.

Independently, Flammenkamp's cache already CONTAINS a C4 (rot4) extremal
solution for every even n in [6,72], so C4 existence is empirically true on
that range; the open problem is a uniform proof for ALL even n.
"""
import os, math, random
from collections import defaultdict

# ----------------------------------------------------------- construction
def construct_from_edges(edges, m):
    n = 2 * m
    pts = []
    for i, j in edges:
        pts.append((i, j))
        pts.append((j, n - 1 - i))
        pts.append((n - 1 - i, n - 1 - j))
        pts.append((n - 1 - j, i))
    return pts

def full_m_cycle(m):
    return [(i, (i + 1) % m) for i in range(m)]

def self_loop_plus_cycle(m, loop=0):
    edges = [(loop, loop)]
    rem = [v for v in range(m) if v != loop]
    L = len(rem)
    for idx in range(L):
        edges.append((rem[idx], rem[(idx + 1) % L]))
    return edges

def skip_k_cycle(m, k):
    """Single 2-factor: edges (i, i+k mod m). 2-regular for any k."""
    return [(i, (i + k) % m) for i in range(m)]

def random_2factor(m, rng):
    """Random 2-regular graph = cycle decomposition of a random permutation."""
    perm = list(range(m))
    rng.shuffle(perm)
    edges = []
    seen = [False] * m
    for start in range(m):
        if seen[start]:
            continue
        # walk the cycle
        v = start
        while not seen[v]:
            seen[v] = True
            nxt = perm[v]
            edges.append((v, nxt))
            v = nxt
    return edges

# ------------------------------------------------------ SOUND collinearity
def _norm(dx, dy):
    if dx == 0 and dy == 0:
        return None
    g = math.gcd(abs(dx), abs(dy)) or 1
    dx //= g; dy //= g
    if dx < 0 or (dx == 0 and dy < 0):
        dx = -dx; dy = -dy
    return (dx, dy)

def has_collinear(points):
    N = len(points)
    for i in range(N):
        xi, yi = points[i]
        dirs = defaultdict(int)
        for j in range(N):
            if j == i:
                continue
            k = _norm(points[j][0] - xi, points[j][1] - yi)
            dirs[k] += 1
        for c in dirs.values():
            if c >= 2:
                return True
    return False

def is_valid_c4(edges, m):
    pts = construct_from_edges(edges, m)
    if len(pts) != 4 * m:
        return False
    return not has_collinear(pts)

# --------------------------------------------------------------- testing
def test_range(max_m=60, rand_trials=100, seed=12345):
    rng = random.Random(seed)
    out = []
    w = out.append
    w("=" * 78)
    w("DIRECTION 1 -- C4 EXISTENCE (SOUND).  Naive patterns debunked;")
    w("searching for a true constructive family + random-2-factor evidence.")
    w("=" * 78)
    w(f"{'m':>4}{'n':>5} | {'full':>5}{'(1,m-1)':>8} | {'#skip-k ok':>10} | "
      f"rand {rand_trials} ok")
    w("-" * 78)
    full_fail = []
    om_fail = []
    skipk_universal = set(range(3, max_m + 1))   # k that works for ALL m?
    rand_any = []                                 # m where random found one
    for m in range(3, max_m + 1):
        n = 2 * m
        fv = is_valid_c4(full_m_cycle(m), m)
        omv = any(is_valid_c4(self_loop_plus_cycle(m, lp), m)
                  for lp in range(m))
        # skip-k single cycles, k=2..m-1
        skipk_ok = []
        for k in range(2, m):
            if is_valid_c4(skip_k_cycle(m, k), m):
                skipk_ok.append(k)
        skipk_universal &= set(skipk_ok)
        # random 2-factors
        r_ok = 0
        for _ in range(rand_trials):
            if is_valid_c4(random_2factor(m, rng), m):
                r_ok += 1
        if r_ok > 0:
            rand_any.append(m)
        if not fv: full_fail.append(m)
        if not omv: om_fail.append(m)
        w(f"{m:>4}{n:>5} | {str(fv):>5}{str(omv):>8} | "
          f"{len(skipk_ok):>10} | {r_ok:>3}/{rand_trials}")
    w("-" * 78)
    w(f"full m-cycle FAILS for all m>=4 : {full_fail == list(range(4, max_m+1))}")
    w(f"(1,m-1)       FAILS for all m>=4 : {om_fail == list(range(4, max_m+1))}")
    w(f"skip-k single cycles that work for EVERY tested m : "
      f"{sorted(skipk_universal)}")
    w(f"m with >=1 valid RANDOM 2-factor (evidence for existence) : "
      f"{len(rand_any)}/{max_m-2}  (m in {rand_any})")
    w("=" * 78)
    rep = '\n'.join(out)
    print(rep)
    with open(os.path.join(os.path.dirname(__file__),
                           'c4_universality.txt'), 'w') as fo:
        fo.write(rep + '\n')
    return dict(full_fail=full_fail, om_fail=om_fail,
                skipk_universal=sorted(skipk_universal), rand_any=rand_any)


if __name__ == '__main__':
    import sys
    M = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    T = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    test_range(M, T)
