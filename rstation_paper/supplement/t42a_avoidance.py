# -*- coding: utf-8 -*-
"""T42a: T41-A avoidance landscape analysis.

Coarse board [0,m)^2, S: 2m points, 2 per row, 2 per column, no 3 collinear.
Confinement lift to fine n=2m board: rep (x, 2v), antipode (2m-1-x, 2m-1-2v).
Kill types (2 reps + 1 antipode collinear):
  MAIN:  A = {x-2v};  kill iff exists a: mult(a)==2 and mult(-a)>=1
  ANTI:  B = {x+2v};  kill iff exists c: mult(c)==2 and mult(2*(2m-1)-c)>=1
  CENT:  two reps with parallel doubled vectors (rep-rep-center line)
  G:     any other mixed collinear triple
Enumerate D(m) by DFS over rows, classify kills, dump near-misses.
"""
import sys, itertools, json
from collections import Counter

def collinear(p, q, r):
    return (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0]) == 0

def has_collinear_triple(pts):
    n = len(pts)
    for i in range(n):
        for j in range(i+1, n):
            dx, dy = pts[j][0]-pts[i][0], pts[j][1]-pts[i][1]
            for k in range(j+1, n):
                if dx*(pts[k][1]-pts[i][1]) == dy*(pts[k][0]-pts[i][0]):
                    return True
    return False

def enum_coarse(m, cap=200000):
    """DFS row by row: each row picks 2 columns; col count <=2; incremental no-3-collinear."""
    sols = []
    colcnt = [0]*m
    pts = []
    def dfs(v):
        if v == m:
            sols.append(list(pts))
            return
        for c1 in range(m):
            if colcnt[c1] >= 2: continue
            for c2 in range(c1+1, m):
                if colcnt[c2] >= 2: continue
                p, q = (c1, v), (c2, v)
                ok = True
                # incremental collinearity: new pair with any existing point
                for r in pts:
                    if collinear(p, q, r): ok = False; break
                if ok:
                    for i in range(len(pts)):
                        for j in range(i+1, len(pts)):
                            if collinear(pts[i], pts[j], p) or collinear(pts[i], pts[j], q):
                                ok = False; break
                        if not ok: break
                if ok:
                    colcnt[c1]+=1; colcnt[c2]+=1; pts.append(p); pts.append(q)
                    dfs(v+1)
                    pts.pop(); pts.pop(); colcnt[c1]-=1; colcnt[c2]-=1
    dfs(0)
    return sols

def kill_types(m, S):
    """Return dict of kill info for coarse solution S (list of (x,v))."""
    n2 = 2*m - 1  # antipode sum index base: fine coords 0..2m-1, antipode i -> 2m-1-i
    A = Counter(x - 2*v for x, v in S)
    B = Counter(x + 2*v for x, v in S)
    main = []
    for a, c in A.items():
        if c >= 2 and A.get(-a, 0) >= 1:
            main.append(a)
    anti = []
    for c, k in B.items():
        if k >= 2 and B.get(2*n2 - c, 0) >= 1:
            anti.append(c)
    cent = []
    pts = S
    for i in range(len(pts)):
        for j in range(i+1, len(pts)):
            u1, w1 = 2*pts[i][0]-n2, 4*pts[i][1]-n2
            u2, w2 = 2*pts[j][0]-n2, 4*pts[j][1]-n2
            if u1*w2 == u2*w1:
                cent.append((pts[i], pts[j]))
    return {"main": main, "anti": anti, "cent": cent, "A": A, "B": B}

def mixed_triples(m, S):
    """All collinear fine triples with exactly 2 reps + 1 antipode, classified.
    Fine board n=2m; reps (x,2v); antipode_k = (2m-1-x_k, 2m-1-2v_k).
    Type priority: 'cent' if the antipode belongs to one of the two reps (p,q,-q);
    'main' = A-type (slope +1, x-y=const, d-multiset a,a,-a);
    'anti' = B-type (slope -1, x+y=const, c+,c+,4m-2-c+);
    'G' = other."""
    n = 2*m
    reps = [(x, 2*v) for x, v in S]
    ants = [(n-1-x, n-1-2*v) for x, v in S]
    out = []
    for i in range(len(reps)):
        for j in range(i+1, len(reps)):
            for k in range(len(ants)):
                a, b, c = reps[i], reps[j], ants[k]
                if collinear(a, b, c):
                    if k == i or k == j:
                        t = "cent"
                    else:
                        dx, dy = b[0]-a[0], b[1]-a[1]
                        if abs(dx) == abs(dy):
                            t = "main" if dx*dy > 0 else "anti"
                        else:
                            t = "G"
                    out.append((a, b, c, t))
    return out

def g_kill_exists(m, S):
    return any(t == "G" for *_, t in mixed_triples(m, S))

def avoidance_ok(m, S):
    kt = kill_types(m, S)
    return not kt["main"] and not kt["anti"] and not kt["cent"]

def analyze(m, verbose=True):
    sols = enum_coarse(m)
    stats = Counter()
    rows_out = []
    for idx, S in enumerate(sols):
        kt = kill_types(m, S)
        n_kill_types = sum(1 for k in ("main","anti","cent") if kt[k])
        stats[n_kill_types] += 1
        rows_out.append((idx, n_kill_types, kt))
    if verbose:
        print(f"m={m}: {len(sols)} coarse solutions")
        for k in sorted(stats):
            print(f"  kill-type count {k}: {stats[k]}")
    return sols, rows_out

if __name__ == "__main__":
    m_lo, m_hi = int(sys.argv[1]), int(sys.argv[2])
    for m in range(m_lo, m_hi+1):
        sols, rows = analyze(m)
        from collections import Counter as C2
        tcount = C2()
        mismatch = 0
        for idx, S in enumerate(sols):
            kt = kill_types(m, S)
            tri = mixed_triples(m, S)
            tc = C2(t for *_, t in tri)
            tcount.update(tc)
            # cross-validate multiset checks vs triple classification
            if bool(kt["main"]) != (tc["main"] > 0): mismatch += 1; print(f"  MISMATCH main sol#{idx}: ms={kt['main']} tri={dict(tc)}")
            if bool(kt["anti"]) != (tc["anti"] > 0): mismatch += 1; print(f"  MISMATCH anti sol#{idx}: ms={kt['anti']} tri={dict(tc)}")
            if bool(kt["cent"]) != (tc["cent"] > 0): mismatch += 1; print(f"  MISMATCH cent sol#{idx}: tri={dict(tc)}")
            if not kt["main"] and not kt["anti"] and not kt["cent"]:
                print(f"  [3-type-clean] sol#{idx} triples={dict(tc)} A={dict(kt['A'])} B={dict(kt['B'])} S={S}")
        print(f"  triple-type totals: {dict(tcount)}  mismatches={mismatch}")
