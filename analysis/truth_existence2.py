"""
Truth B (refined): WHY the naive Lovasz Local Lemma / second-moment proof FAILS.

Key finding from truth_existence.py: for CONSECUTIVE rows (0,1,2), the bad-event
probability p_consec(n) decays as ~ c/n (NOT 1/n^3 as naively guessed).  We verify
this scaling at large n by Monte Carlo, and measure the AVERAGE bad-event
probability over random row-triples (to get E[#bad triples] per random config).

Conclusion we expect: the no-three-in-line constraint is LOCAL.  Consecutive rows
produce a collinear triple with constant probability per triple; summed over the
~n consecutive triples this gives Theta(1) bad triples per config and the LLL
product e*p*d ~ Theta(n) diverges.  Hence the standard probabilistic method
CANNOT prove D(n)=2n.  This is the fundamental structural reason the problem is hard.
"""
import random, math
from itertools import combinations

def bad_consecutive(n, Si, Sj, Sk):
    pts = [(c, 0) for c in Si] + [(c, 1) for c in Sj] + [(c, 2) for c in Sk]
    A = pts[:2]; B = pts[2:4]; C = pts[4:6]
    for a in A:
        for b in B:
            for c in C:
                (x1, y1), (x2, y2), (x3, y3) = a, b, c
                if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
                    return True
    return False

def p_consecutive_mc(n, trials=300000):
    cols = list(range(n))
    pairs = [tuple(p) for p in combinations(cols, 2)]
    P = len(pairs)
    bad = 0
    for _ in range(trials):
        Si = pairs[random.randrange(P)]
        Sj = pairs[random.randrange(P)]
        Sk = pairs[random.randrange(P)]
        if bad_consecutive(n, Si, Sj, Sk):
            bad += 1
    return bad / trials

def p_average_mc(n, trials=200000):
    """Average bad probability over a RANDOM triple of distinct row positions."""
    cols = list(range(n))
    pairs = [tuple(p) for p in combinations(cols, 2)]
    P = len(pairs)
    bad = 0
    for _ in range(trials):
        ys = random.sample(range(n), 3)
        ys.sort()
        y0, y1, y2 = ys
        Si = pairs[random.randrange(P)]
        Sj = pairs[random.randrange(P)]
        Sk = pairs[random.randrange(P)]
        # test collinearity of one point per row at positions y0<y1<y2
        A = [(c, y0) for c in Si]; B = [(c, y1) for c in Sj]; C = [(c, y2) for c in Sk]
        found = False
        for a in A:
            for b in B:
                for c in C:
                    (x1, y1), (x2, y2), (x3, y3) = a, b, c
                    if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
                        found = True; break
                if found: break
            if found: break
        if found:
            bad += 1
    return bad / trials

def main():
    out = []
    w = out.append
    w("=" * 78)
    w("TRUTH B (refined): the scaling that kills the naive LLL proof")
    w("=" * 78)
    w("")
    w("p_consec(n) = Pr(consecutive rows 0,1,2 contain a collinear triple)")
    w("If p_consec ~ c/n, then LLL product e*p*d ~ e*(c/n)*(1.5 n^2) = O(n) -> inf.")
    w("")
    w("--- p_consec(n) at large n (Monte Carlo) ---")
    w(f"  {'n':>7} {'p_consec':>12} {'p*n':>10}   interpretation")
    for n in [50, 100, 300, 1000, 3000, 10000]:
        p = p_consecutive_mc(n, trials=400000)
        w(f"  {n:>7} {p:>12.6e} {p*n:>10.3f}   -> p ~ {p*n:.2f}/n")
    w("")
    w("--- average p over RANDOM row-triples, and E[#bad] per random config ---")
    w(f"  {'n':>5} {'p_avg':>12} {'E_bad=C(n,3)*p_avg':>22}")
    for n in [20, 40, 80, 160, 320]:
        pa = p_average_mc(n, trials=200000)
        eb = math.comb(n, 3) * pa
        w(f"  {n:>5} {pa:>12.6e} {eb:>22.2f}")
    w("")
    w("If E_bad grows with n (not shrinks), random configs are ALWAYS bad ->")
    w("the probabilistic method cannot certify a zero-collinearity config.")
    w("=" * 78)
    report = "\n".join(out)
    print(report)
    with open("truth_existence2.txt", "w") as f:
        f.write(report + "\n")

if __name__ == "__main__":
    random.seed(98765)
    main()
