#!/usr/bin/env python3
"""Computational corroboration of Theorem R (rotational Costas classification).

A Costas array of order n is C2-symmetric (invariant under 180 deg rotation
about the grid centre) iff its permutation pi satisfies
    pi(n-1-i) = n-1 - pi(i)   for all i.           (*)
This is because 180 deg rotation sends (i, pi(i)) -> (n-1-i, n-1-pi(i)),
and set-invariance forces that image to be a plotted point.

We enumerate all permutations satisfying (*) for small n and test the Costas
condition.  Theorem R predicts: only n=2 yields solutions (the two order-2
Costas arrays, both D2 = C2+diagonal); every n>=3 C2-symmetric set fails
Costas.  This corroborates the parallelogram / two-orbit collision proof.

Run: python costas_c2_corroborate.py
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


def c2_symmetric_perms(n):
    """Yield all permutations pi on {0..n-1} satisfying (*)."""
    if n % 2 == 0:
        k = n // 2
        # choose pi(0..k-1) freely; pi(k..n-1) determined
        for head in itertools.permutations(range(n), k):
            pi = [None] * n
            for i in range(k):
                pi[i] = head[i]
            for i in range(k, n):
                pi[i] = (n - 1) - pi[n - 1 - i]
            if len(set(pi)) == n:
                yield pi
    else:
        k = (n - 1) // 2
        # middle index m = k must satisfy pi(k) = k
        for head in itertools.permutations(range(n), k):
            pi = [None] * n
            for i in range(k):
                pi[i] = head[i]
            pi[k] = k
            for i in range(k + 1, n):
                pi[i] = (n - 1) - pi[n - 1 - i]
            if len(set(pi)) == n:
                yield pi


def main():
    print("=== C2-symmetric Costas corroboration (Theorem R) ===")
    for n in [2, 4, 6, 8, 10]:
        count = 0
        examples = []
        for pi in c2_symmetric_perms(n):
            if is_costas(pi):
                count += 1
                if len(examples) < 3:
                    examples.append(pi)
        verdict = "OK (Costas exists)" if count else "NONE (collision, per R)"
        print(f"  n={n}: C2-symmetric Costas count={count}  -> {verdict}")
        if examples:
            for ex in examples:
                print(f"        eg {ex}")


if __name__ == "__main__":
    main()
