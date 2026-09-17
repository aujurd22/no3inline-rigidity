"""
Deeper mining + construction probes.

1. Print the ACTUAL vertex orders of real single-m-cycle C4 solutions for
   small m, to look for a hidden pattern.
2. Test whether a real single cycle's order matches any simple generator
   (arithmetic AP, irrational-sorted "quasicrystal", power/gen).
3. Test RECURSIVE DOUBLING: from a C4 solution on m vertices, build one on
   2m vertices via edge blow-up  {i,j} -> {2i,2j},{2i+1,2j+1}. If valid,
   this is a genuine constructive existence proof (m => 2m).
"""

import os, math
from collections import defaultdict, Counter
from math import gcd

ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
CACHE = 'flammenkamp_cache'

def decode(line, n):
    line = line.strip()
    if len(line) < 2: return None
    body = line[1:]
    if len(body) != 2 * n: return None
    pts = []; per = len(body) // n
    for y in range(n):
        for j in range(per):
            ch = body[y * per + j]
            if ch not in ALPHABET: return None
            pts.append((ALPHABET.index(ch), y))
    return pts

def edges_of(pts, n):
    m = n // 2
    return sorted(set((x, y) if x <= y else (y, x) for x, y in pts if x < m and y < m))

def cycle_decomp(edges, m):
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b); adj[b].append(a)
    seen = set(); res = []
    for s in range(m):
        if s in seen or s not in adj: continue
        cur = s; prev = -1; length = 0
        while cur not in seen:
            seen.add(cur); nx = [w for w in adj[cur] if w != prev]
            if not nx: break
            prev, cur = cur, nx[0]; length += 1
        if length: res.append(length)
    return sorted(res, reverse=True)

def canonical(edges, m):
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b); adj[b].append(a)
    cur = 0; prev = -1; seq = []
    while True:
        seq.append(cur)
        nx = [w for w in adj[cur] if w != prev]
        if not nx: break
        prev, cur = cur, nx[0]
        if cur == 0: break
    rev = seq[::-1]
    def rot(s):
        i = s.index(0); return s[i:] + s[:i]
    return tuple(min(rot(seq), rot(rev)))

def orbit(i, j, m):
    n = 2 * m
    R = lambda x, y: (n - 1 - y, x)
    p0 = (i, j); p1 = R(*p0); p2 = R(*p1); p3 = R(*p2)
    return (p0, p1, p2, p3)

def is_valid(edges, m):
    pts = []
    for (i, j) in edges:
        if i > j: i, j = j, i
        pts.extend(orbit(i, j, m))
    N = len(pts)
    if N < 3: return True
    lc = Counter()
    for a in range(N):
        x1, y1 = pts[a]
        for b in range(a + 1, N):
            x2, y2 = pts[b]
            A = y2 - y1; B = x1 - x2; C = x2 * y1 - x1 * y2
            g = gcd(gcd(A, B), C)
            if g != 0: A //= g; B //= g; C //= g
            if A < 0 or (A == 0 and B < 0) or (A == 0 and B == 0 and C < 0):
                A, B, C = -A, -B, -C
            lc[(A, B, C)] += 1
    return (max(lc.values()) if lc else 0) < 3

def real_single_cycles(n):
    f = f'{CACHE}/n{n}_rot4'
    if not os.path.exists(f): return []
    m = n // 2
    out = set()
    with open(f) as fh:
        for line in fh:
            p = decode(line, n)
            if not p: continue
            e = edges_of(p, n)
            if cycle_decomp(e, m) == [m]:
                out.add(canonical(e, m))
    return list(out)

def gen_canonical(m, order):
    # order: list of m distinct vertices -> single cycle edges
    edges = [(order[k], order[(k + 1) % m]) for k in range(m)]
    return canonical(edges, m)

def main():
    small = [3, 4, 5, 7, 8, 9, 10, 11, 13, 14]
    print("=== real single-m-cycle vertex orders (canonical) ===")
    for m in small:
        n = 2 * m
        cycs = real_single_cycles(n)
        print(f"m={m}: {len(cycs)} distinct -> {cycs}")
        # pattern match against generators
        matches = []
        # arithmetic AP (a coprime to m)
        for a in range(1, m):
            if gcd(a, m) != 1: continue
            order = [(a * k) % m for k in range(m)]
            if gen_canonical(m, order) in cycs:
                matches.append(f"AP a={a}")
        # irrational sorted
        for name, al in [("phi",1.6180339887),("s2",math.sqrt(2)),("s3",math.sqrt(3)),
                         ("pi",math.pi),("e",math.e)]:
            order = sorted(range(m), key=lambda k: (k * al) % 1)
            if gen_canonical(m, order) in cycs:
                matches.append(f"{name}")
        if matches:
            print(f"    MATCH generators: {matches}")

    print("\n=== recursive DOUBLING test (m -> 2m) ===")
    ok = 0; tot = 0; examples = []
    for m in range(3, 25):
        n = 2 * m
        f = f'{CACHE}/n{n}_rot4'
        if not os.path.exists(f): continue
        with open(f) as fh:
            lines = [l for l in fh if l.strip()]
        # try first few solutions
        for line in lines[:5]:
            p = decode(line, n)
            if not p: continue
            E = edges_of(p, n)
            # blow up
            E2 = []
            for (i, j) in E:
                E2.append((2 * i, 2 * j))
                E2.append((2 * i + 1, 2 * j + 1))
            m2 = 2 * m
            # dedup and ensure i<j
            E2 = sorted(set((min(a, b), max(a, b)) for a, b in E2))
            tot += 1
            if is_valid(E2, m2):
                ok += 1
                if len(examples) < 3:
                    examples.append((m, m2))
                break
    print(f"doubling valid: {ok}/{tot} base-m tried; examples {examples}")

main()
