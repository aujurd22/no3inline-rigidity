# -*- coding: utf-8 -*-
"""T42e: T'-F2 certificate census over rot2 library solutions.

F2-unimodular triangle: reps p,q,r with |det(q-p, -r-p)| = 1 (original coords).
Layer-1 certificate: adjacent horizontal rep pair (c,y),(c+1,y) + antipode of a
rep in row n-2-y  (det = 1 via ey=1).
Census: per-solution count, certificate types by rep-pair difference vector,
layer-1 coverage, adjacent-pair availability.
"""
import sys, os, glob, os
from collections import Counter
from itertools import combinations

LIB = os.environ.get("NTIL_LIB", ".")

def load_rot2(path, cap=None):
    sols = []
    cur = None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line.startswith("# solution"):
            if cur: sols.append(cur)
            cur = []
        elif line.startswith("#"):
            continue
        elif line:
            x, y = map(int, line.split())
            cur.append((x, y))
    if cur: sols.append(cur)
    return sols[:cap] if cap else sols

def f2_triangles(n, pts):
    """All F2-unimodular triangles from rep set R (left-half points)."""
    reps = [p for p in pts if p[0] < n/2]
    out = []
    for p, q, r in combinations(reps, 3):
        for a, b, cc in ((p,q,r),(p,r,q),(q,r,p)):
            dx, dy = b[0]-a[0], b[1]-a[1]
            ex, ey = (n-1-cc[0])-a[0], (n-1-cc[1])-a[1]
            if abs(dx*ey - dy*ex) == 1:
                out.append((a, b, cc))
                break
    return reps, out

def has_adjacent_rep_pair(reps):
    """Row-adjacent horizontal rep pairs (c,y),(c+1,y)."""
    rowpts = {}
    for x, y in reps:
        rowpts.setdefault(y, set()).add(x)
    return any(any(x+1 in xs for x in xs) for xs in rowpts.values())

def layer1_f2_exists(n, reps):
    rowpts = {}
    for x, y in reps:
        rowpts.setdefault(y, set()).add(x)
    for y, xs in rowpts.items():
        y2 = n-2-y
        if y2 in rowpts and any(x+1 in xs for x in xs):
            return True
    return False

def main():
    n_lo, n_hi = int(sys.argv[1]), int(sys.argv[2])
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else None
    grand = Counter()
    pair_type_tot = Counter()
    hard = []
    for n in range(n_lo, n_hi+1):
        if n % 2: continue
        path = os.path.join(LIB, f"n{n}_rot2.txt")
        if not os.path.exists(path):
            # single-digit naming
            path = os.path.join(LIB, f"n{n}_rot2.txt")
        if not os.path.exists(path): continue
        sols = load_rot2(path, cap)
        st = Counter()
        for si, pts in enumerate(sols):
            reps, tri = f2_triangles(n, pts)
            n_tri = len(tri)
            st["sols"] += 1
            if n_tri == 0:
                st["F2_free"] += 1
                hard.append((n, si, pts))
                continue
            assert all(abs(((q[0]-p[0]))*((n-1-r[1])-p[1]) - ((q[1]-p[1]))*((n-1-r[0])-p[0])) == 1 for p,q,r in tri)
            if layer1_f2_exists(n, reps): st["L1_cert"] += 1
            if has_adjacent_rep_pair(reps): st["has_adj_pair"] += 1
            # certificate pair types
            for a, b, cc in tri:
                d = (b[0]-a[0], b[1]-a[1])
                if d[0] < 0 or (d[0] == 0 and d[1] < 0): d = (-d[0], -d[1])
                pair_type_tot[d] += 1
        grand.update(st)
        if st["sols"]:
            print(f"n={n}: {st['sols']} sols, F2-free={st['F2_free']}, L1-cert={st['L1_cert']}, has-adj-pair={st['has_adj_pair']}")
    print(f"\nTOTAL: {dict(grand)}")
    print("top certificate pair-difference types:", pair_type_tot.most_common(12))
    if hard:
        print(f"\nF2-FREE SOLUTIONS ({len(hard)}) — T'-F2 COUNTEREXAMPLE CANDIDATES:")
        for n, si, pts in hard[:5]:
            print(f"  n={n} sol#{si}: {pts}")

if __name__ == "__main__":
    main()
