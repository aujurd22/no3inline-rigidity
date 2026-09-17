#!/usr/bin/env python3
"""Validate the SOUND collinearity check against KNOWN facts:
  (1) a real Flammenkamp rot4 solution MUST have zero collinear triples;
  (2) the full m-cycle must be caught as collinear.
This rules out false negatives in has_collinear before we trust any 'failure'.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import hypergraph_framework as hf
from c4_universality import has_collinear, construct_from_edges, full_m_cycle

CACHE = hf.CACHE

def brute_collinear(pts):
    from itertools import combinations
    c = 0
    for a, b, d in combinations(pts, 3):
        if (b[0]-a[0])*(d[1]-a[1]) == (d[0]-a[0])*(b[1]-a[1]):
            c += 1
    return c

# (1) real rot4 solution from cache
for n in [12, 18, 24]:
    f = os.path.join(CACHE, f'n{n}_rot4')
    if not os.path.exists(f):
        continue
    with open(f) as fh:
        line = fh.readline().strip()
    pts = hf.decode_line(line, n)
    fast = has_collinear(pts)
    slow = brute_collinear(pts)
    print(f"REAL rot4 n={n}: decode_ok={pts is not None} "
          f"pts={len(pts)} has_collinear(fast)={fast} "
          f"collinear_triples(brute)={slow}  -> "
          f"{'OK (verifier agrees, solution valid)' if (not fast and slow==0) else '*** MISMATCH ***'}")

# (2) full m-cycle must be caught (known bad: (0,1),(1,2),(2,3) collinear)
for m in [4, 5, 10]:
    pts = construct_from_edges(full_m_cycle(m), m)
    fast = has_collinear(pts)
    slow = brute_collinear(pts)
    print(f"full m-cycle m={m}: fast={fast} brute_collinear={slow} "
          f"-> {'OK caught' if fast else '*** MISSED ***'}")
