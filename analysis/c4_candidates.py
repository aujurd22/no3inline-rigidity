"""
Test explicit CONSTRUCTION families for C4 (rot4) solutions.

A C4 solution on n=2m corresponds to a 2-factor on {0..m-1}; each edge
{i,j} (i<j) -> a 4-orbit. Valid <=> no 3 of the 4m orbit points are collinear.

We test whether simple, DESCRIBABLE 2-factors are always valid -- this is
the "construction theory" the user wants. Families inspired by the
quasicrystal / low-discrepancy intuition (Part B):
  - golden/silver/irrational single m-cycles (vertex order = sort by {k*a})
  - Welch-Costas permutation 2-factor (connects to Costas arrays)
  - ladder (consecutive + reflection)
  - bit-reversal (powers of two)
"""

import math, os
from math import gcd
from collections import Counter

ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

def orbit(i, j, m):
    n = 2 * m
    R = lambda x, y: (n - 1 - y, x)
    p0 = (i, j); p1 = R(*p0); p2 = R(*p1); p3 = R(*p2)
    return (p0, p1, p2, p3)

def is_valid(edges, m):
    pts = []
    for (i, j) in edges:
        if i > j:
            i, j = j, i
        pts.extend(orbit(i, j, m))
    N = len(pts)
    if N < 3:
        return True
    linecount = Counter()
    for a in range(N):
        x1, y1 = pts[a]
        for b in range(a + 1, N):
            x2, y2 = pts[b]
            A = y2 - y1; B = x1 - x2; C = x2 * y1 - x1 * y2
            g = gcd(gcd(A, B), C)
            if g != 0:
                A //= g; B //= g; C //= g
            if A < 0 or (A == 0 and B < 0) or (A == 0 and B == 0 and C < 0):
                A, B, C = -A, -B, -C
            linecount[(A, B, C)] += 1
    return (max(linecount.values()) if linecount else 0) < 3

def cycle_edges(order):
    m = len(order)
    return [(order[k], order[(k + 1) % m]) for k in range(m)]

def golden_cycle(m, alpha):
    order = sorted(range(m), key=lambda k: (k * alpha) % 1)
    return cycle_edges(order)

def ladder_2factor(m):
    # each vertex connects to i+1 (mod m) and to m-1-i  -> degree 2
    edges = []
    for i in range(m):
        j = (i + 1) % m
        edges.append((i, j))
        k = m - 1 - i
        if k > i:
            edges.append((i, k))
    return edges

def bitreverse_cycle(m):
    # only for m = power of two
    if m & (m - 1):
        return None
    nb = m.bit_length() - 1
    order = [int(f'{k:0{nb}b}'[::-1], 2) for k in range(m)]
    return cycle_edges(order)

def welch_2factor(m):
    # m must be prime p; Welch Costas: pi(i) = g^i mod p (permutation of 0..p-1)
    # 2-factor = cycle decomposition of pi  => edges {i, pi(i)}
    if m < 2:
        return None
    # find a primitive root g of m
    def is_prime(p):
        if p < 2:
            return False
        for d in range(2, int(math.isqrt(p)) + 1):
            if p % d == 0:
                return False
        return True
    if not is_prime(m):
        return None
    # primitive root
    phi = m - 1
    def factors(x):
        f = set()
        d = 2
        while d * d <= x:
            while x % d == 0:
                f.add(d); x //= d
            d += 1
        if x > 1:
            f.add(x)
        return f
    for g in range(2, m):
        ok = all(pow(g, phi // f, m) != 1 for f in factors(phi))
        if ok:
            break
    pi = [(pow(g, i, m)) for i in range(m)]
    # pi(0)=1, we need permutation of 0..m-1; Welch gives {1..m-1} for i=0..m-2 and pi(m-1)=g^(m-1)=1 -> dup.
    # Use standard Welch: pi(i)=g^i mod p for i=0..p-2, pi(p-1)=0.
    pi = [pow(g, i, m) for i in range(m - 1)] + [0]
    edges = [(i, pi[i]) for i in range(m) if i < pi[i]]
    return edges

def test_family(name, gen, ms):
    succ = []; fail = []
    for m in ms:
        try:
            e = gen(m)
        except Exception:
            continue
        if e is None:
            continue
        ok = is_valid(e, m)
        (succ if ok else fail).append(m)
    print(f"{name:22s} success={len(succ):3d}  fail={len(fail):3d}  "
          f"first_fail={fail[:8]}")
    return succ, fail

def main():
    ms = list(range(3, 61))
    print("=== explicit C4 construction families (n=2m, m=3..60) ===")
    test_family("golden(phi)", lambda m: golden_cycle(m, 1.618033988749895), ms)
    test_family("silver(sqrt2)", lambda m: golden_cycle(m, math.sqrt(2)), ms)
    test_family("sqrt3", lambda m: golden_cycle(m, math.sqrt(3)), ms)
    test_family("pi", lambda m: golden_cycle(m, math.pi), ms)
    test_family("e", lambda m: golden_cycle(m, math.e), ms)
    test_family("1+sqrt2", lambda m: golden_cycle(m, 1 + math.sqrt(2)), ms)
    test_family("ladder", ladder_2factor, ms)
    test_family("bitreverse", bitreverse_cycle, ms)
    test_family("Welch-Costas", welch_2factor, ms)
    print("\nNote: 'success' = family yields a valid C4 solution for that m.")

main()
