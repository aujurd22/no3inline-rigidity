#!/usr/bin/env python3
"""
C4 (rot4) single-cycle 2-factor FINDER (backtracking + collinearity pruning).

NOTE (honest status, 2026-07-09): this is a *search* tool, NOT a fast O(m)
constructor. It finds one valid single-m-cycle solution quickly for small m
(m <= ~10 in milliseconds) but BRANCHES EXPONENTIALLY and times out beyond
roughly m=12 on a single CPU. It is therefore a verification/exploration tool,
not a viable generator for n=74 (m=37) on limited hardware. The construction
THEORY is documented in c4_construction_theory.md.

Usage:  python c4_construct.py [max_m] [timelimit_sec]
"""
import sys, time
from collections import defaultdict

def orbit(i, j, m):
    """4 grid points of the C4 orbit of fundamental point (i,j), n=2m."""
    n = 2 * m
    return ((i, j), (j, n - 1 - i), (n - 1 - i, n - 1 - j), (n - 1 - j, i))

def collinear(a, b, c):
    (x1, y1), (x2, y2), (x3, y3) = a, b, c
    return (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1)

def build_single_cycle(m, timelimit=60.0):
    """Return a list of m vertices forming a single cycle (valid C4 2-factor)
    or None if not found within timelimit."""
    n = 2 * m
    placed = []          # list of all orbit points currently placed
    placed_set = set()
    used = [False] * m
    path = []
    nodes = [0]

    def orbit_ok(i, j):
        """Check the 4 new orbit points vs all pairs in placed."""
        pts = orbit(i, j, m)
        # quick: any new point already placed?
        for p in pts:
            if p in placed_set:
                return False
        L = len(placed)
        for p in pts:
            # check against all pairs (placed[a], placed[b])
            pa = placed
            for a in range(L):
                xa, ya = pa[a]
                for b in range(a + 1, L):
                    if collinear(pa[a], pa[b], p):
                        return False
        return True

    def recurse(last, depth):
        if time.time() - start > timelimit:
            return None
        nodes[0] += 1
        if depth == m:
            # must close: edge (last, 0)
            if orbit_ok(last, 0):
                return list(path)   # m vertices, cycle closes via v0
            return None
        # candidate next vertices: unused, not 0 unless closing
        cands = [v for v in range(m) if not used[v] and (depth < m - 1 or v != 0)]
        # most-constrained-first heuristic: prefer vertices whose remaining
        # orbit options are fewest (cheap proxy: just try in natural order,
        # but skip 0 until the end)
        for v in cands:
            if used[v]:
                continue
            if orbit_ok(last, v):
                used[v] = True
                path.append(v)
                for p in orbit(last, v, m):
                    placed.append(p); placed_set.add(p)
                res = recurse(v, depth + 1)
                if res is not None:
                    return res
                for p in orbit(last, v, m):
                    placed.pop(); placed_set.discard(p)
                path.pop()
                used[v] = False
        return None

    start = time.time()
    used[0] = True
    path.append(0)
    res = recurse(0, 1)
    return res, nodes[0], time.time() - start

def cycle_to_solution(cycle, m):
    """Convert a cycle vertex list into the full 4m grid points."""
    n = 2 * m
    pts = []
    L = len(cycle)
    for k in range(L):
        i = cycle[k]; j = cycle[(k + 1) % L]
        if i > j: i, j = j, i
        pts.extend(orbit(i, j, m))
    return pts

def verify(pts, n):
    from itertools import combinations
    total = len(pts)
    s = set(pts)
    if len(s) != total:
        return False, "duplicate points"
    for a, b, c in combinations(range(total), 3):
        if collinear(pts[a], pts[b], pts[c]):
            return False, "collinear triple"
    return True, "ok"

def main():
    max_m = int(sys.argv[1]) if len(sys.argv) > 1 else 37
    tl = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    print("=" * 70)
    print("FAST C4 SINGLE-CYCLE CONSTRUCTOR  (backtracking + collinear prune)")
    print("=" * 70)
    targets = [3, 4, 5, 7, 8, 9, 10, 12, 15, 20, 25, 30, 37]
    targets = [t for t in targets if t <= max_m] + ([max_m] if max_m not in targets else [])
    for m in targets:
        n = 2 * m
        res, nodes, dt = build_single_cycle(m, timelimit=tl)
        if res is not None:
            pts = cycle_to_solution(res, m)
            ok, msg = verify(pts, n)
            status = "VALID" if ok else f"INVALID({msg})"
            print(f"  m={m:>2} (n={n:>2}): FOUND single cycle in {dt:6.2f}s "
                  f"nodes={nodes:>10,}  cycle={res}  [{status}]")
        else:
            print(f"  m={m:>2} (n={n:>2}): not found in {dt:6.2f}s "
                  f"nodes={nodes:>10,}  (single-cycle search)")

if __name__ == '__main__':
    main()
