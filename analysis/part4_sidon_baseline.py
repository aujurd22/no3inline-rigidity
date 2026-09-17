#!/usr/bin/env python3
"""Part IV empirical baseline.

SIRH Part IV = the *reverse* (property -> structure) question:
  does the FDR linear Sidon signature force (near-)symmetry?

Lemma E (fdr_theorem.md) says the *crude* reverse fails: asymmetric
(iden) configs can satisfy a-b<=2 by chance, with probability -> 0 as n->inf.

This script quantifies the BASELINE: among *random* m-subsets of the
m x m fundamental quadrant, what fraction satisfy the FDR linear layer
(a-b Sidon AND a+b Sidon, i.e. each slope+/-1 value appears at most twice)?

That fraction is the "prior" probability a random config carries the
symmetry signature.  Symmetric NTILs carry it with prob 1 (Part I).
The gap is the strength of Sidon as a *symptom* of symmetry.
"""
import random
from collections import Counter


def fdr_sidon_ok(subset):
    """subset: list of (a,b) in [0,m)^2.  Check FDR linear layer:
    a-b family AND a+b family each appear at most twice per signed value."""
    diffs = [a - b for a, b in subset]
    sums = [a + b for a, b in subset]
    for vals in (diffs, sums):
        c = Counter(vals)
        # slope+1 line: value d and -d collide on the same line family?
        # FDR law: count(d)+count(-d) <= 2 for every d.
        seen = set()
        for d, k in c.items():
            if d in seen:
                continue
            pair = k + c.get(-d, 0)
            if pair > 2:
                return False
            seen.add(d)
            seen.add(-d)
    return True


def main():
    random.seed(20260713)
    N = 40000
    print(f"# random m-subset FDR Sidon baseline (N={N} samples each)")
    print(f"# m  frac_sidon  (1 in ~)")
    for m in range(5, 17):
        grid = [(a, b) for a in range(m) for b in range(m)]
        hit = 0
        for _ in range(N):
            sub = random.sample(grid, m)
            if fdr_sidon_ok(sub):
                hit += 1
        frac = hit / N
        inv = (1.0 / frac) if frac > 0 else float('inf')
        print(f"{m:2d}  {frac:.6f}   (1 in ~{inv:.0f})")


if __name__ == "__main__":
    main()
