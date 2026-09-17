#!/usr/bin/env python3
"""Backtracking search for a missing-center solution with vertical-mirror
(ort1) symmetry.  Rows are placed top-to-bottom; at row y we choose the
left x-coordinate xl(y) in [0, mid), which fixes the symmetric pair
(xl,y),(n-1-xl,y).  Collinearity is checked incrementally against all
already-placed points.  Missing-center (no ring with >=3 points) is checked
only at full depth.  Stops at the first witness found."""
import os, sys, time
from collections import Counter

sys.setrecursionlimit(10000)


def ring_sig(n, x, y):
    a = 2 * x - (n - 1); b = 2 * y - (n - 1)
    return a * a + b * b


def run(n, deadline, node_cap=50_000_000):
    mid = n // 2
    placed = []                       # list of (x,y)
    pset = set()
    colcnt = [0] * n
    rings = Counter()
    # incremental collinearity: for each new point, test against all pairs of old
    nodes = [0]

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
        if time.time() > deadline or nodes[0] > node_cap:
            return None
        if y == n:
            # full solution built; check missing-center
            return (n, sorted(pset)) if max(rings.values()) <= 2 else None
        for xl in range(mid):
            xr = n - 1 - xl
            if colcnt[xl] >= 2 or colcnt[xr] >= 2:
                continue
            p1 = (xl, y); p2 = (xr, y)
            if p1 in pset or p2 in pset:
                continue
            # collinearity of each new point vs all pairs of placed
            if not ok_collinear(xl, y) or not ok_collinear(xr, y):
                continue
            # tentative add
            placed.append(p1); placed.append(p2); pset.add(p1); pset.add(p2)
            colcnt[xl] += 1; colcnt[xr] += 1
            rings[ring_sig(n, xl, y)] += 1; rings[ring_sig(n, xr, y)] += 1
            nodes[0] += 1
            res = dfs(y + 1)
            if res is not None:
                return res
            # undo
            placed.pop(); placed.pop(); pset.discard(p1); pset.discard(p2)
            colcnt[xl] -= 1; colcnt[xr] -= 1
            rings[ring_sig(n, xl, y)] -= 1; rings[ring_sig(n, xr, y)] -= 1
        return None

    return dfs(0)


def symclass(n, pts):
    S = set(pts)
    def inv(t):
        if t == 4: f = lambda x, y: (n - 1 - x, y)
        elif t == 5: f = lambda x, y: (x, n - 1 - y)
        elif t == 6: f = lambda x, y: (y, x)
        elif t == 7: f = lambda x, y: (n - 1 - y, n - 1 - x)
        return all(f(x, y) in S for x, y in pts)
    rv, rh, rd, ra = inv(4), inv(5), inv(6), inv(7)
    if rv and rh: return '+'
    if rd and ra: return 'x'
    if rv or rh: return '-'
    if rd or ra: return '/'
    return '.'


def main():
    out = []
    deadline = time.time() + 220
    for n in [10, 12, 14, 16, 18, 20]:
        t0 = time.time()
        res = run(n, deadline)
        dt = time.time() - t0
        if res:
            nn, pts = res
            out.append(f"[ort1] n={nn} FOUND  symmetry={symclass(nn,pts)}"
                       f"  (valid NTIL={len(pts)==2*nn})")
            out.append(f"   points: {{{', '.join(f'({x},{y})' for x,y in pts)}}}")
            out.append("   (search stopped at first witness)")
            break
        else:
            out.append(f"[ort1] n={n}: no witness (search budget {dt:.0f}s)")
    print("\n".join(out))
    with open(os.path.join(os.path.dirname(__file__), 'ort1_search.txt'), 'w') as fo:
        fo.write("\n".join(out) + "\n")


if __name__ == '__main__':
    main()
