#!/usr/bin/env python3
"""Verify the Rickard bridge: transpose-symmetric (D-type) Costas array of odd
order n = 2m-1  <->  a Golomb ruler of order m.

We enumerate transpose-symmetric involutions pi = pi^-1 (fixed point at the
centre for odd n), keep the Costas ones, and extract the candidate "ruler"
marks.  Goal: confirm the exact correspondence and the difference-count, so we
can then apply a density bound to the open orders 32/33.

Run: python symmetric_costas_golomb.py
"""
import itertools


def is_costas(perm):
    n = len(perm)
    diffs = set()
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = (perm[j] - perm[i], j - i)
            if d in diffs:
                return False
            diffs.add(d)
    return True


def symmetric_involutions(n):
    """Yield involutions pi=pi^-1 on {0..n-1} with fixed point at centre (n odd)."""
    c = (n - 1) // 2
    rest = [i for i in range(n) if i != c]
    # partition `rest` (even length) into transpositions
    def pairings(items):
        if not items:
            yield []
            return
        a = items[0]
        for k in range(1, len(items)):
            b = items[k]
            for rest_pairs in pairings(items[1:k] + items[k+1:]):
                yield [(a, b)] + rest_pairs
    for pairs in pairings(rest):
        pi = [None] * n
        pi[c] = c
        for a, b in pairs:
            pi[a] = b
            pi[b] = a
        yield pi


def main():
    print("=== Symmetric (transpose) Costas <-> Golomb ruler bridge ===")
    for n in [5, 7, 9, 11, 13]:
        m = (n + 1) // 2
        found = 0
        example_pi = None
        example_marks = None
        for pi in symmetric_involutions(n):
            if not is_costas(pi):
                continue
            found += 1
            if example_pi is None:
                example_pi = pi
                # candidate ruler: the upper-triangle diagonal distances
                # d_i = pi(i) - i for i < c, plus centre?  Inspect both forms.
                c = (n - 1) // 2
                marks_A = sorted(pi[i] - i for i in range(c))   # differences
                marks_B = sorted(pi[i] for i in range(c))        # values
                example_marks = (marks_A, marks_B)
        ruler_order_needed = m
        # density sanity: a modular Golomb ruler of order m on Z_n needs
        # C(m,2) distinct nonzero differences among n-1 residues.
        needed_diffs = m * (m - 1) // 2
        avail = n - 1
        print(f"  n={n} (m={m}): symmetric-Costas count={found}  "
              f"need {needed_diffs} distinct diffs, have {avail} residues "
              f"({'OK' if needed_diffs <= avail else 'IMPOSSIBLE-by-count'})")
        if example_pi is not None:
            print(f"      eg pi={example_pi}")
            print(f"      marks(diff pi(i)-i)={example_marks[0]}")
            print(f"      marks(values pi(i))={example_marks[1]}")


if __name__ == "__main__":
    main()
