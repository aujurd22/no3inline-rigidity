#!/usr/bin/env python3
"""
Costas / Sidon / difference-set unification -- computational probes.

Two independent checks that back the theoretical bridge in
`analysis/results/sidon_costas_unification.md`:

(1) WELCH DEMO  -- shows the *linear / finite-field* construction works for
    Costas arrays (contrast: all 55+ finite-field attacks on rot4-NTIL failed).
    Welch(pi(i)=g^i mod p) gives a Costas array of order p-1 for prime p.

(2) C4-SYMMETRIC COSTAS SEARCH -- applies the R8-analog: a C4-symmetric Costas
    array of order n=4m is encoded by m cells in a (2m)x(2m) fundamental
    quadrant; the Costas (all-displacements-distinct) condition is *linear* in
    those cells, so we brute-force the tiny quadrant to probe the open question
    "do rotational (C4) Costas arrays exist?"  This is the exact Costas analogue
    of `cpsat_m37.py` (which handled the *quadratic* rot4-NTIL case).
"""
import itertools, sys

def primitive_root(p):
    if p == 2: return 1
    phi = p - 1
    # factor phi
    n, fac = phi, []
    d = 2
    while d * d <= n:
        while n % d == 0:
            fac.append(d); n //= d
        d += 1
    if n > 1: fac.append(n)
    fac = list(set(fac))
    for g in range(2, p):
        if all(pow(g, phi // f, p) != 1 for f in fac):
            return g
    return None

def is_costas_perm(pi):
    n = len(pi)
    seen = set()
    for i in range(n):
        for j in range(i + 1, n):
            dx, dy = j - i, pi[j] - pi[i]
            if (dx, dy) in seen:
                return False
            seen.add((dx, dy))
    return True

def welch(p):
    g = primitive_root(p)
    return [pow(g, i, p) for i in range(p - 1)]  # order p-1

def demo_welch(primes=(2, 3, 5, 7, 11, 13, 17, 19)):
    print("=== (1) Welch finite-field construction (linear method) ===")
    for p in primes:
        pi = welch(p)
        ok = is_costas_perm(pi)
        print(f"  p={p:2d} -> order {len(pi):2d} Costas={ok}")
    print()

def c4_lift(cell, N):
    x, y = cell
    return [(x, y), (N - 1 - y, x), (N - 1 - x, N - 1 - y), (y, N - 1 - x)]

def c4_symmetric_costas_search(m_max=4):
    print("=== (2) C4-symmetric Costas search (R8-analog: linear CSP) ===")
    print("    order n=4m, m cells in (2m)x(2m) fundamental quadrant\n")
    for m in range(1, m_max + 1):
        n = 4 * m              # order
        q = 2 * m              # fundamental quadrant side
        N = n                  # board side = order
        quad = [(x, y) for x in range(q) for y in range(q)]
        found = []
        for cells in itertools.combinations(quad, m):
            dots = []
            for c in cells:
                dots.extend(c4_lift(c, N))
            rows = [d[0] for d in dots]
            cols = [d[1] for d in dots]
            if len(set(rows)) != n or len(set(cols)) != n:
                continue  # not a permutation (one per row/col)
            # Costas check on the dot set
            seen = set()
            ok = True
            for i in range(len(dots)):
                for j in range(i + 1, len(dots)):
                    dx = dots[j][0] - dots[i][0]
                    dy = dots[j][1] - dots[i][1]
                    if (dx, dy) in seen:
                        ok = False; break
                    seen.add((dx, dy))
                if not ok: break
            if ok:
                found.append(cells)
        print(f"  m={m} (order n={n}): quadrant {q}x{q}, "
              f"combos C({q*q},{m})={len(list(itertools.combinations(quad, m))):,}, "
              f"C4-symmetric Costas found = {len(found)}")
        if found:
            print(f"      example fundamental cells: {found[0]}")
    print()

if __name__ == "__main__":
    demo_welch()
    c4_symmetric_costas_search(m_max=4)
