"""
lll_pilot.py -- exact pilot computation for the RANDOM-LABELED 2-FACTOR LLL
(main line proposed by the user).

Model: fix an abstract 2-factor skeleton (cycle-type [37]); assign a uniform
random bijection pi: vertices -> [m] and orient each edge independently.
Every outcome is a 2-regular m-cell set (no cardinality / Gap-B issue).

We compute, exactly, for the WORST-case canonical conflict event:
  * p_k4_max : Pr(a 3-consecutive-edge X-event occurs)  [k=4 endpoints]
  * N_total   : total number of canonical conflict events
  * d_worst   : dependency degree (events sharing >=1 vertex)
  * e * p * (d+1)  : the symmetric-LLL sufficient condition

A pass (<=1) would be a rigorous non-constructive existence proof for m=37.
"""
import math
from itertools import product

m = 37
n = 2 * m


def orbit(x, y, r):
    if r == 0:
        return (x, y)
    if r == 1:
        return (n - 1 - y, x)
    if r == 2:
        return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)


def collinear(p1, p2, p3):
    return (p2[0] - p1[0]) * (p3[1] - p1[1]) == (p3[0] - p1[0]) * (p2[1] - p1[1])


def exact_p_k4_base():
    """3 consecutive edges (0,1),(1,2),(2,3); base orientation increasing.
    Cells: (a,b),(b,c),(c,d) with a,b,c,d = pi(0..3) distinct in [m].
    For each of 64 rotation combos count collinear assignments exactly over
    all ordered distinct (a,b,c,d) in [m] (m*(m-1)*(m-2)*(m-3) total)."""
    total = m * (m - 1) * (m - 2) * (m - 3)
    sat = [0] * 64
    # iterate ordered distinct 4-tuples
    vals = list(range(m))
    for a in vals:
        for b in vals:
            if b == a:
                continue
            for c in vals:
                if c == a or c == b:
                    continue
                for d in vals:
                    if d == a or d == b or d == c:
                        continue
                    cells = [(a, b), (b, c), (c, d)]
                    for ri in range(4):
                        p1 = orbit(cells[0][0], cells[0][1], ri)
                        for rj in range(4):
                            p2 = orbit(cells[1][0], cells[1][1], rj)
                            for rk in range(4):
                                p3 = orbit(cells[2][0], cells[2][1], rk)
                                if collinear(p1, p2, p3):
                                    sat[ri * 16 + rj * 4 + rk] += 1
    # each rotation combo is a distinct event; per-event prob = sat/ (total*8)
    # (the /8 is for the 3 edge orientations; here we used base orientation)
    p_max = max(sat) / total
    return p_max, total


def exact_p_S_base():
    """S-event: 3 cells on a slope=+1 line y = x + const (fundamental quadrant).
    Use 3 consecutive edges (0,1),(1,2),(2,3) base orientation (a,b),(b,c),(c,d).
    Condition: b-a == c-b == d-c  (arithmetic progression of the 4 labels)."""
    total = m * (m - 1) * (m - 2) * (m - 3)
    sat = 0
    vals = list(range(m))
    for a in vals:
        for b in vals:
            if b == a:
                continue
            for c in vals:
                if c == a or c == b:
                    continue
                for d in vals:
                    if d == a or d == b or d == c:
                        continue
                    if (b - a) == (c - b) == (d - c):
                        sat += 1
    return sat / total


if __name__ == "__main__":
    p_k4, tot = exact_p_k4_base()
    # account for the 3 edge orientations (each event fixes them): divide by 8
    p_k4_event = p_k4 / 8.0
    print(f"[m=37] exact p (3-consec-edge X-event, base orient) = {p_k4:.6f}")
    print(f"        per-event p (with orientation factor 1/8) = {p_k4_event:.6f}")

    p_S = exact_p_S_base() / 8.0
    print(f"[m=37] exact p (S slope+1 3-cell event)            = {p_S:.6f}")

    # total canonical events = C(m,3) undirected edge-triples * 8 orient * 64 rot
    from math import comb
    N = comb(m, 3) * 8 * 64
    # dependency: edges incident to the 4 vertices {0,1,2,3} of the worst event
    # in a 37-cycle: edges (36,0),(0,1),(1,2),(2,3),(3,4) = 5 edges
    incident_edges = 5
    free_edges = m - incident_edges
    d_worst = N - comb(free_edges, 3) * 8 * 64
    print(f"[m=37] total events N      = {N:,}")
    print(f"[m=37] worst dep degree d  = {d_worst:,}")

    e = math.e
    val = e * p_k4_event * (d_worst + 1)
    print(f"[m=37] symmetric LLL value e*p*(d+1) = {val:.3e}  "
          f"({'PASS (<=1)' if val <= 1 else 'FAIL (>>1)'})")
    valS = e * p_S * (d_worst + 1)
    print(f"[m=37] symmetric LLL (S only)      = {valS:.3e}  "
          f"({'PASS' if valS <= 1 else 'FAIL'})")
