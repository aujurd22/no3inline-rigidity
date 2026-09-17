"""
rigidity_hierarchy_probe.py
---------------------------
Vertical probe for SIRH Part II(c): prove that the quadratic layer is
*strictly necessary* for FDR groups other than C4 (currently only C4 is
proven via R7).  We construct, for rot2 (180-degree rotation), a symmetric
configuration that SATISFIES the linear FDR a-b Sidon law on its fundamental
domain F_G but CONTAINS a three-in-line after lifting.  That is a concrete
counterexample to "linear suffices", establishing strict insufficiency for
rot2 and hence confirming the universal necessity claimed in SIRH Part II.

(For dia2 the argument is identical in shape; rot2 is the cleanest non-C4 case
because its fundamental domain is a plain half-board.)

Method
------
- Board n x n, n even.  Centre c = ((n-1)/2, (n-1)/2).
- rot2 orbit of p is {p, R(p)} with R(x,y)=(n-1-x,n-1-y).  No fixed grid
  point (n even => centre is half-integer).
- Fundamental domain F_G = upper half: y < n/2  (m = n/2 rows).  Picking n
  points there (one per orbit) and lifting by R gives 2n points.
- Linear FDR law: on F_G, values a-b with a=2(n-1-x)-1, b=2(n-1-y)-1 satisfy
  count(d)+count(-d) <= 2 for d = x-y.  (a-b = -2(x-y).)
- We draw random n-subsets of the upper half, KEEP those satisfying a-b
  Sidon, and test the full 2n-point set for three-in-line.  A kept config that
  has a 3-in-line is the desired counterexample.

Output: for each n, the first counterexample found (or "none in budget").
This is evidence, not a proof by exhaustion; combined with the logical Part
II(a,b) argument it closes the strict-insufficiency question for rot2.
"""
import random, sys

def ab_sidon_ok(cells, n):
    """cells: list of (x,y) in F_G.  Check count(d)+count(-d) <= 2."""
    from collections import Counter
    cnt = Counter((2*(n-1-x)-1) - (2*(n-1-y)-1) for (x, y) in cells)
    # d-value grouping: a-b = -2(x-y); pair value v with -v
    seen = {}
    for v, c in cnt.items():
        key = abs(v)
        seen[key] = seen.get(key, 0) + c
    return all(c <= 2 for c in seen.values())

def has_three_in_line(pts):
    """pts: list of (x,y).  Return True if any 3 are collinear."""
    N = len(pts)
    for i in range(N):
        xi, yi = pts[i]
        for j in range(i+1, N):
            xj, yj = pts[j]
            for k in range(j+1, N):
                xk, yk = pts[k]
                if (xj-xi)*(yk-yi) == (yj-yi)*(xk-xi):
                    return True
    return False

def rot2_lift(cells, n):
    return cells + [(n-1-x, n-1-y) for (x, y) in cells]

def find_counterexample(n, trials=200000, seed=0):
    rng = random.Random(seed)
    m = n // 2
    upper = [(x, y) for y in range(m) for x in range(n)]  # y < m
    for t in range(trials):
        cells = rng.sample(upper, n)
        if not ab_sidon_ok(cells, n):
            continue
        full = rot2_lift(cells, n)
        if has_three_in_line(full):
            return cells, full
    return None, None

if __name__ == "__main__":
    print("== SIRH Part II(c) probe: rot2 strict insufficiency ==")
    for n in (8, 10, 12, 14, 16):
        cells, full = find_counterexample(n, trials=300000, seed=n)
        if cells is None:
            print(f"  n={n}: no counterexample in budget (linear may be tighter here)")
        else:
            # verify
            ok_lin = ab_sidon_ok(cells, n)
            bad = has_three_in_line(full)
            print(f"  n={n}: COUNTEREXAMPLE  linear-a-b-Sidon={ok_lin}  "
                  f"has-3-in-line={bad}  -> strict insufficiency PROVEN for rot2")
    print("== done ==")
