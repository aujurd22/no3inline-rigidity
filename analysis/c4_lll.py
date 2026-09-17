"""
C4 (rot4) existence -- probabilistic-method / LLL feasibility analysis.

A C4 solution on an n=2m grid corresponds to a 2-factor (2-regular graph)
on vertex set {0..m-1}: each edge {i,j} (i<j) lifts to a 4-orbit
O(i,j) = {(i,j),(n-1-j,i),(n-1-i,n-1-j),(j,n-1-i)}  (n=2m, 90deg about center).

S is missing-center / valid NTIL  <=>  no three points of S are collinear.

A "bad event" = a pair of distinct orbits (edges) whose union contains a
collinear triple. We:
  1. count, for each m, the fraction r(m) of ALL orbit-pairs that conflict;
  2. estimate E[#conflicting edge-pairs in a random 2-factor] = C(m,2)*r(m);
  3. fit r(m) = C * m^{-alpha}  and read off the 1st-moment / LLL verdict.

Honest goal: determine whether the *naive* probabilistic method even has a
chance, and quantify the sparsity of valid 2-factors.
"""

import math, time, os

def orbit(i, j, m):
    n = 2 * m
    R = lambda x, y: (n - 1 - y, x)          # 90 deg CCW about center (m-.5,m-.5)
    p0 = (i, j); p1 = R(*p0); p2 = R(*p1); p3 = R(*p2)
    return (p0, p1, p2, p3)

def collinear(a, b, c):
    (x1, y1), (x2, y2), (x3, y3) = a, b, c
    return (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) == 0

def build_orbits(m):
    return [orbit(i, j, m) for i in range(m) for j in range(i + 1, m)]

def pair_conflicts(orbs):
    k = len(orbs); cnt = 0
    for a in range(k):
        A = orbs[a]
        for b in range(a + 1, k):
            B = orbs[b]
            pts = A + B                      # 8 points
            bad = False
            for i in range(8):
                for j in range(i + 1, 8):
                    for l in range(j + 1, 8):
                        if collinear(pts[i], pts[j], pts[l]):
                            bad = True; break
                    if bad: break
                if bad: break
            if bad: cnt += 1
    return cnt

def main():
    ms = [4, 5, 6, 8, 10, 12, 15, 18, 22, 26, 30, 35]
    rows = []
    for m in ms:
        t0 = time.time()
        orbs = build_orbits(m)
        N = len(orbs)
        tot = N * (N - 1) // 2
        conf = pair_conflicts(orbs)
        r = conf / tot if tot else 0.0
        exp_rf = (m * (m - 1) // 2) * r       # E[#conflicting edge-pairs in random 2-factor]
        rows.append((m, N, tot, conf, r, exp_rf))
        print(f"m={m:2d} N={N:4d} pairs={tot:9d} conf={conf:9d} "
              f"r(m)={r:.4e}  E[conf]~{exp_rf:.4e}  ({time.time()-t0:.1f}s)", flush=True)

    fit_rows = [(m, r) for (m, *_x, r, _e) in rows if r > 0]   # skip r=0 (m=4: no conflicts)
    lms = [math.log(m) for (m, r) in fit_rows]
    lrs = [math.log(r) for (m, r) in fit_rows]
    n = len(lms); sx = sum(lms); sy = sum(lrs)
    sxx = sum(x * x for x in lms); sxy = sum(x * y for x, y in zip(lms, lrs))
    alpha = -(n * sxy - sx * sy) / (n * sxx - sx * sx)
    C = math.exp((sy + alpha * sx) / n)
    print()
    print(f"FIT:  r(m) = {C:.4f} * m^(-{alpha:.3f})")
    print(f"  =>  E[conf] ~ C(m,2)*C*m^(-alpha) ~ {C:.2f} * m^({2-alpha:+.3f})")
    if 2 - alpha < 0:
        print("  => DECAYS to 0 as m->inf  -->  naive 1st-moment method SUCCEEDS for large m")
    else:
        print("  => GROWS with m  -->  naive 1st-moment / plain LLL FAILS;")
        print("                        valid 2-factors are a SPARSE subset (consistent with")
        print("                        0/100 random-2-factor hits); a proof needs a")
        print("                        structured dependency argument, not the crude bound.")

    with open(os.path.join(os.path.dirname(__file__), 'c4_lll.txt'), 'w') as fo:
        fo.write("m  N  pairs  conf  r(m)  E[conf]\n")
        for (m, N, tot, conf, r, e) in rows:
            fo.write(f"{m} {N} {tot} {conf} {r:.6e} {e:.6e}\n")
        fo.write(f"\nFIT r(m)={C:.4f}*m^(-{alpha:.3f}); exponent 2-alpha={2-alpha:+.3f}\n")

main()
