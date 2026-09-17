"""
modp_analysis_v2.py — Direction 1 refined: mod-p structure of the determinant system.

Key insight: The R8 determinant det = x1*y2 + x2*y3 + x3*y1 - x1*y3 - x2*y1 - x3*y2
is a quadratic form.  Its value mod p is determined by the coordinate parity /
residues.  

We check THREE things:
1. For each prime p, what's the *distribution* of det ≡ 0 across the 16 rotation classes?
   (The 64 raw patterns reduce to 16 equivalence classes; each class may have different
   mod-p behavior.)
2. Is there a prime p where EVERY triple has det ≡ 0 mod p (for some orientation)?
   (This would imply all constraints are parity-blocked — impossible at m=37.)
3. Are the 16-violation triples (from the best config) characterized by a specific
   mod-p signature?  (This would let us predict violations for untested configs.)

Usage:
    python modp_analysis_v2.py
"""
import os, sys, json, math, itertools, time
from collections import defaultdict
import random

HERE = os.path.dirname(os.path.abspath(__file__))

def c4(x, y, r, n):
    if r == 0: return (x, y)
    if r == 1: return (n - 1 - y, x)
    if r == 2: return (n - 1 - x, n - 1 - y)
    return (y, n - 1 - x)

def det_collinear(p1, p2, p3):
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3
    return x1*y2 + x2*y3 + x3*y1 - x1*y3 - x2*y1 - x3*y2

# The 16 R8 rotation equivalence classes (from r8_proof.md)
# Each is a set of 4 patterns (r1,r2,r3) related by C4 board rotations
# These are the 16 classes that cover all 64 raw patterns
R8_CLASSES = [
    [(0,0,1),(1,1,2),(2,2,3),(3,3,0)],
    [(0,0,2),(1,1,3),(2,2,0),(3,3,1)],
    [(0,0,3),(1,1,0),(2,2,1),(3,3,2)],
    [(0,1,0),(1,2,1),(2,3,2),(3,0,3)],
    [(0,1,1),(1,2,2),(2,3,3),(3,0,0)],
    [(0,1,2),(1,2,3),(2,3,0),(3,0,1)],
    [(0,1,3),(1,2,0),(2,3,1),(3,0,2)],
    [(0,2,0),(1,3,1),(2,0,2),(3,1,3)],
    [(0,2,1),(1,3,2),(2,0,3),(3,1,0)],
    [(0,2,2),(1,3,3),(2,0,0),(3,1,1)],
    [(0,2,3),(1,3,0),(2,0,1),(3,1,2)],
    [(0,3,0),(1,0,1),(2,1,2),(3,2,3)],
    [(0,3,1),(1,0,2),(2,1,3),(3,2,0)],
    [(0,3,2),(1,0,3),(2,1,0),(3,2,1)],
    [(0,3,3),(1,0,0),(2,1,1),(3,2,2)],
    [(0,0,0),(1,1,1),(2,2,2),(3,3,3)],  # identity class
]

def all_rotation_patterns():
    """Return all 64 patterns as list of (r1,r2,r3)."""
    return [(i,j,k) for i in range(4) for j in range(4) for k in range(4)]

def load_edges(path):
    with open(path) as f:
        data = json.load(f)
    return [(e[0], e[1]) for e in data["edges"]]

def random_cells(edges, rng):
    cells = []
    for u, v in edges:
        if u == v:
            cells.append((u, u))
        else:
            cells.append((u, v) if rng.randint(0, 1) else (v, u))
    return cells

def analyze_mod_structure(cells, m, primes):
    """
    For each prime p and each rotation class, count det ≡ 0 (mod p).
    Also find the 16-specific patterns.
    """
    n = 2 * m
    lifts = {}
    for idx, (x, y) in enumerate(cells):
        lifts[idx] = [c4(x, y, r, n) for r in range(4)]
    
    n_cells = len(cells)
    all_patterns = all_rotation_patterns()
    
    # Per-prime, per-class counts
    class_counts = {p: {c: 0 for c in range(16)} for p in primes}
    class_total = {c: 0 for c in range(16)}
    
    for i in range(n_cells):
        for j in range(i + 1, n_cells):
            for k in range(j + 1, n_cells):
                for ci, patterns in enumerate(R8_CLASSES):
                    d_ref = det_collinear(
                        lifts[i][patterns[0][0]],
                        lifts[j][patterns[0][1]],
                        lifts[k][patterns[0][2]]
                    )
                    class_total[ci] += 1
                    for p in primes:
                        if d_ref % p == 0:
                            class_counts[p][ci] += 1
    
    return class_counts, class_total

def main():
    m = 37
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73]
    rng = random.Random(42)
    
    edges_path = os.path.join(HERE, "results", "config_408_edges.json")
    edges = load_edges(edges_path)
    print(f"m={m}, edges={len(edges)}")
    
    # Run with one random orientation
    cells = random_cells(edges, rng)
    class_counts, class_total = analyze_mod_structure(cells, m, primes)
    
    print("\n=== Per-class determinant count (%) ===")
    header = f"{'class':>5s}"
    for p in primes[:10]:  # first 10 primes
        header += f"  p={p:2d}%"
    print(header)
    
    for ci in range(16):
        total = class_total[ci]
        row = f"{ci:5d}"
        for p in primes[:10]:
            cnt = class_counts[p][ci]
            row += f"  {cnt/total*100:6.2f}"
        print(row)
    
    # Check: is any prime forcing 100% det≡0 for all classes?
    print("\n=== Prime-by-prime: % of all triples with det≡0 ===")
    totals = {p: sum(class_counts[p].values()) for p in primes}
    grand_total = sum(class_total.values())
    for p in primes:
        print(f"  p={p:3d}: {totals[p]/grand_total*100:6.2f}% of all triples have det≡0 (mod p)")
    
    # Check: the 16 identity class (class 15) specifically
    print("\n=== Identity rotation class (r1=r2=r3) characteristics ===")
    ci_ident = 15
    print(f"  class {ci_ident} total triples: {class_total[ci_ident]}")
    for p in primes:
        cnt = class_counts[p][ci_ident]
        print(f"  p={p:3d}: {cnt}/{class_total[ci_ident]} = {cnt/class_total[ci_ident]*100:.2f}%")
    
    # Analysis: For p large enough (> max possible determinant), 
    # det ≡ 0 (mod p) ⇒ det = 0 (integer collinearity)
    # Max possible determinant for coordinates in [0,73]:
    # det_max = max of x1*y2 + x2*y3 + x3*y1 - x1*y3 - x2*y1 - x3*y2
    # The max absolute value is bounded by 4*73*73 = 21316
    max_det = 4 * 73 * 73
    print(f"\n=== Large prime analysis ===")
    print(f"  Max possible determinant value: {max_det}")
    large_primes = [p for p in primes if p > max_det]
    if large_primes:
        for p in large_primes:
            print(f"  p={p}: det≡0={totals[p]} (if >0, some triple has integer-det=0)")
    else:
        print(f"  No primes > {max_det} in test set")
    
    # Check if there are any triples where det ≡ 0 mod ALL primes = 
    # det is a multiple of the product of all primes = a huge number
    # But more practically: check if det = 0 for any triple
    print("\n=== Integer zero determinants (sampled) ===")
    n = 2*m
    zero_count = 0
    total_checked = 0
    # Sample: check triple of cells (0,1,2) with all 64 patterns
    for ri in range(4):
        for rj in range(4):
            for rk in range(4):
                for i, j, k in [(0,1,2), (3,5,7), (10,15,20)]:
                    d = det_collinear(
                        c4(cells[i][0], cells[i][1], ri, n),
                        c4(cells[j][0], cells[j][1], rj, n),
                        c4(cells[k][0], cells[k][1], rk, n)
                    )
                    total_checked += 1
                    if d == 0:
                        zero_count += 1
    print(f"  Sampled {total_checked} triples from 3 cell-triples: {zero_count} have det=0")

if __name__ == "__main__":
    main()
