#!/usr/bin/env python3
"""
Construct explicit missing-center No-Three-In-Line solutions for the symmetry
classes that have NO example in the Flammenkamp cache (dia2, ort1, ort2).

A missing-center solution = every distance-ring about the grid centre holds
<= 2 points.  Symmetry is verified by the same transform logic as the cache.

Encoding (n even):
  dia2 (both diagonal reflections): orbit (x,y) under the two diagonal
       reflections -> {(x,y),(y,x),(n-1-y,n-1-x),(n-1-x,n-1-y)}.
       One representative (x,y) per y in [0,mid) with x = perm[y].
  ort2 (both orthogonal reflections): orbit (x,y) under the two axial
       reflections -> {(x,y),(n-1-x,y),(x,n-1-y),(n-1-x,n-1-y)}.
       One representative (x,y) per y in [0,mid) with x = perm[y].
  ort1 (vertical reflection only): 2 points per row, symmetric about the
       vertical axis -> (xl,y) and (n-1-xl,y).  xl(y) in [0,mid).

dia2 / ort2 are searched EXHAUSTIVELY over all permutations (cheap to n=16);
ort1 is searched exhaustively to n=8 and then randomized to n=18.

Results written to analysis/constructed_witnesses.txt and printed.
"""
import os, re, glob, random, time, itertools
from collections import Counter
from itertools import combinations

CACHE = os.path.join(os.path.dirname(__file__), 'flammenkamp_cache')
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def ring_sig(n, x, y):
    a = 2 * x - (n - 1)
    b = 2 * y - (n - 1)
    return a * a + b * b


def transform(n, x, y, t):
    return [(x, y), (n - 1 - y, x), (n - 1 - x, n - 1 - y), (y, n - 1 - x),
            (n - 1 - x, y), (x, n - 1 - y), (y, x), (n - 1 - y, n - 1 - x)][t]


def invariant(n, pts, t):
    S = set(pts)
    return all(transform(n, x, y, t) in S for x, y in pts)


def near_rot4(n, pts):
    S = set(pts)
    flt = {(x, y) for (x, y) in pts if x != y and x + y != n - 1}
    return not flt or all(transform(n, x, y, 1) in S for x, y in flt)


def symclass(n, pts):
    r90 = invariant(n, pts, 1); r180 = invariant(n, pts, 2)
    rv = invariant(n, pts, 4); rh = invariant(n, pts, 5)
    rd = invariant(n, pts, 6); ra = invariant(n, pts, 7)
    if r90 and rv and rh and rd and ra: return '*'
    if r90: return 'o'
    if near_rot4(n, pts): return 'c'
    if rd and ra: return 'x'
    if rv and rh: return '+'
    if r180: return ':'
    if rd or ra: return '/'
    if rv or rh: return '-'
    return '.'


def is_ntil(n, pts):
    if len(pts) != 2 * n:
        return False
    if any(c != 2 for c in Counter(x for x, _ in pts).values()):
        return False
    if any(c != 2 for c in Counter(y for _, y in pts).values()):
        return False
    P = sorted(pts)
    for (x1, y1), (x2, y2), (x3, y3) in combinations(P, 3):
        if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
            return False
    return True


def missing(n, pts):
    return max(Counter(ring_sig(n, x, y) for x, y in pts).values()) <= 2


def load_cache_witness(cls):
    best = None
    for f in glob.glob(os.path.join(CACHE, f'n*_{cls}')):
        m = re.match(r'n(\d+)_([a-z0-9]+)$', os.path.basename(f))
        if not m:
            continue
        n = int(m.group(1))
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                body = line[1:]
                if len(body) != 2 * n:
                    continue
                pts = []
                for y in range(n):
                    for j in range(2):
                        pts.append((ALPHABET.index(body[y * 2 + j]), y))
                if missing(n, pts) and symclass(n, pts) == CLASS_MARKER[cls]:
                    if best is None or n < best[0]:
                        best = (n, sorted(pts), cls)
    return best


CLASS_MARKER = {'iden': '.', 'rot2': ':', 'dia1': '/', 'dia2': 'x',
               'ort1': '-', 'ort2': '+', 'rot4': 'o', 'rct4': 'c', 'full': '*'}


def dia2_points(n, perm):
    mid = n // 2
    pts = set()
    for y in range(mid):
        x = perm[y]
        pts.add((x, y)); pts.add((y, x))
        pts.add((n - 1 - y, n - 1 - x)); pts.add((n - 1 - x, n - 1 - y))
    return sorted(pts)


def ort2_points(n, perm):
    mid = n // 2
    pts = set()
    for y in range(mid):
        x = perm[y]
        pts.add((x, y)); pts.add((n - 1 - x, y))
        pts.add((x, n - 1 - y)); pts.add((n - 1 - x, n - 1 - y))
    return sorted(pts)


def search_perm_class(name, ptsfn, marker, max_n=16):
    for n in range(8, max_n + 1, 2):
        mid = n // 2
        for perm in itertools.permutations(range(mid)):
            pts = ptsfn(n, perm)
            if len(pts) != 2 * n:
                continue
            if is_ntil(n, pts) and missing(n, pts) and symclass(n, pts) == marker:
                return n, pts
    return None


def search_ort1(max_n=18, trials_per_n=2_000_000, deadline=None):
    for n in range(4, max_n + 1, 2):
        mid = n // 2
        if n <= 8:                          # exhaustive
            for prof in itertools.product(range(mid), repeat=n):
                cols = [0] * n
                ok = True
                for y in range(n):
                    xl = prof[y]
                    cols[xl] += 1; cols[n - 1 - xl] += 1
                    if cols[xl] > 2 or cols[n - 1 - xl] > 2:
                        ok = False; break
                if not ok:
                    continue
                pts = set()
                for y in range(n):
                    xl = prof[y]
                    pts.add((xl, y)); pts.add((n - 1 - xl, y))
                if len(pts) != 2 * n:
                    continue
                pts = sorted(pts)
                if is_ntil(n, pts) and missing(n, pts) and symclass(n, pts) == '-':
                    return n, pts
        else:                              # randomized
            for _ in range(trials_per_n):
                if deadline and time.time() > deadline:
                    return None
                prof = [random.randrange(mid) for _ in range(n)]
                cols = [0] * n
                ok = True
                for y in range(n):
                    xl = prof[y]
                    cols[xl] += 1; cols[n - 1 - xl] += 1
                    if cols[xl] > 2 or cols[n - 1 - xl] > 2:
                        ok = False; break
                if not ok:
                    continue
                pts = set()
                for y in range(n):
                    xl = prof[y]
                    pts.add((xl, y)); pts.add((n - 1 - xl, y))
                if len(pts) != 2 * n:
                    continue
                pts = sorted(pts)
                if is_ntil(n, pts) and missing(n, pts) and symclass(n, pts) == '-':
                    return n, pts
    return None


def main():
    out = []
    w = out.append
    w("=" * 78)
    w("CONSTRUCTED MISSING-CENTER WITNESSES (classes absent from cache)")
    w("=" * 78)

    for name, fn, marker in [('dia2', dia2_points, 'x'), ('ort2', ort2_points, '+')]:
        w(f"\n[{name}] exhaustive permutation search (n=8..16)")
        res = search_perm_class(name, fn, marker, 16)
        if res is None:
            w("   NO witness found (n<=16)")
        else:
            n, pts = res
            w(f"   n={n}  valid NTIL={is_ntil(n,pts)}  missing-c={missing(n,pts)}"
              f"  symmetry={symclass(n,pts)} (expect '{marker}')")
            w(f"   points: {{{', '.join(f'({x},{y})' for x,y in pts)}}}")

    w(f"\n[ort1] exhaustive (n<=8) + randomized (n<=18)")
    res = search_ort1(max_n=18, trials_per_n=1_500_000,
                      deadline=time.time() + 220)
    if res is None:
        w("   NO witness found (n<=18, 1.5M trials/n)")
    else:
        n, pts = res
        w(f"   n={n}  valid NTIL={is_ntil(n,pts)}  missing-c={missing(n,pts)}"
          f"  symmetry={symclass(n,pts)} (expect '-')")
        w(f"   points: {{{', '.join(f'({x},{y})' for x,y in pts)}}}")

    w("=" * 78)
    report = '\n'.join(out)
    print(report)
    with open(os.path.join(os.path.dirname(__file__),
                           'constructed_witnesses.txt'), 'w') as fo:
        fo.write(report + '\n')


if __name__ == '__main__':
    main()
