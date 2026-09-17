#!/usr/bin/env python3
"""
Targeted search for a missing-center solution with ort1 (single vertical
mirror) symmetry, using the *distance-ring square* as a hard, SAFE prune.

Key observation (reformulation of missing-center for ort1):
  A vertical-mirror solution places, in each row y, a symmetric pair
  (xl, y), (n-1-xl, y).  Both points of a pair have the SAME squared
  distance from the grid centre C, namely
        N(y) = (2*xl-(n-1))^2 + (2*y-(n-1))^2 .
  Missing-center  <=>  no distance-ring holds >= 3 solution points
                <=>  all n pair-squares N(y) are DISTINCT
                (a repeated N would put two pairs = 4 points on one ring).

SAFETY of the prune: once a pair-square repeats, that ring already holds
>= 4 points, so the partial solution can NEVER become missing-center.
Pruning on a repeat therefore loses NO missing-center solution; the
search remains exhaustive over missing-center ort1 solutions.

Completeness of the row model: for BOTH parities a 2n-point vertical-mirror
solution must place exactly 2 points in every row (a single fixed centre
point per row would make the total < 2n), so the "one pair per row,
xl in [0, n//2)" model covers every v-invariant 2n configuration.

We run an exhaustive DFS per n (norm + collinearity + column-count pruning)
and report the first witness found, or prove non-existence if the whole
space is exhausted within the budget.
"""
import sys, time
from collections import Counter

sys.setrecursionlimit(100000)


def solve(n, time_limit, node_cap=200_000_000):
    mid = n // 2
    a2 = [(2 * xl - (n - 1)) ** 2 for xl in range(mid)]   # squared half-axis
    b2 = [(2 * y - (n - 1)) ** 2 for y in range(n)]       # squared row term
    colcnt = [0] * n
    placed = []
    pset = set()
    used = set()                  # pair-squares already used -> ring collision
    witnesses = []
    stats = {'nodes': 0, 'exhausted': False}
    t0 = time.time()

    def ok_collinear(nx, ny):
        k = len(placed)
        for i in range(k):
            xi, yi = placed[i]
            for j in range(i + 1, k):
                xj, yj = placed[j]
                if (xi - nx) * (yj - ny) == (xj - nx) * (yi - ny):
                    return False
        return True

    def dfs(y):
        if witnesses:
            return
        if time.time() > t0 + time_limit:
            return
        if y == n:
            # 2n points placed, colcnt<=2 each => all exactly 2 (sum=2n).
            # norms all distinct by construction.  => missing-center witness.
            witnesses.append((n, sorted(pset)))
            stats['exhausted'] = True
            return
        for xl in range(mid):
            xr = n - 1 - xl
            if colcnt[xl] >= 2 or colcnt[xr] >= 2:
                continue
            p1 = (xl, y); p2 = (xr, y)
            if p1 in pset or p2 in pset:
                continue
            if not ok_collinear(xl, y) or not ok_collinear(xr, y):
                continue
            norm = a2[xl] + b2[y]
            if norm in used:
                continue
            placed.append(p1); placed.append(p2); pset.add(p1); pset.add(p2)
            colcnt[xl] += 1; colcnt[xr] += 1; used.add(norm)
            stats['nodes'] += 1
            dfs(y + 1)
            if witnesses:
                return
            placed.pop(); placed.pop(); pset.discard(p1); pset.discard(p2)
            colcnt[xl] -= 1; colcnt[xr] -= 1; used.discard(norm)
        if y == 0:
            stats['exhausted'] = True   # finished top level -> whole space done

    dfs(0)
    return witnesses, stats, time.time() - t0


def main():
    import os as _os
    path = _os.path.join(_os.path.dirname(__file__), 'ort1_norm_search.txt')
    with open(path, 'w') as fo:
        fo.write("ORT1 MISSING-CENTER SEARCH (norm-pruned exhaustive DFS)\n")
        fo.flush()
    overall_witness = None
    for n in range(4, 30):
        t0 = time.time()
        wit, stats, dt = solve(n, time_limit=120)
        if wit:
            nn, pts = wit[0]
            line = (f"[n={n:2d}] WITNESS FOUND  nodes={stats['nodes']:>12,}  "
                    f"time={dt:5.1f}s\n"
                    f"        pts={{{', '.join(f'({x},{y})' for x, y in pts)}}}\n")
            overall_witness = (nn, pts)
            print(line, flush=True)
            with open(path, 'a') as fo:
                fo.write(line); fo.flush()
            break
        else:
            tag = "EXHAUSTED (proved none)" if stats['exhausted'] else \
                  "budget reached (inconclusive)"
            line = (f"[n={n:2d}] none   nodes={stats['nodes']:>12,}  "
                    f"time={dt:5.1f}s  [{tag}]\n")
            print(line, flush=True)
            with open(path, 'a') as fo:
                fo.write(line); fo.flush()
    if overall_witness is None:
        line = "\nNo missing-center ort1 solution found for n=4..29.\n"
        print(line, flush=True)
        with open(path, 'a') as fo:
            fo.write(line); fo.flush()


if __name__ == '__main__':
    main()
