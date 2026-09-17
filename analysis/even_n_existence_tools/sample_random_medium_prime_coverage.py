"""Baseline medium-prime coverage in random disjoint permutation pairs."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics
from pathlib import Path

from analyze_large_prime_carries import determinant, primes_below


def sample(n: int, sample_count: int) -> dict:
    relevant_primes = [
        p
        for p in primes_below((n - 1) ** 2 + 1)
        if p >= math.sqrt(n)
    ]
    rough = [False] * ((n - 1) ** 2 + 1)
    for value in range(1, len(rough)):
        rough[value] = any(value % p == 0 for p in relevant_primes)

    fractions = []
    zero_counts = []
    total = math.comb(2 * n, 3)
    for seed in range(sample_count):
        rng = random.Random(seed)
        first = list(range(n))
        second = list(range(n))
        rng.shuffle(first)
        rng.shuffle(second)
        while any(first[row] == second[row] for row in range(n)):
            rng.shuffle(second)
        points = [(row, first[row]) for row in range(n)] + [
            (row, second[row]) for row in range(n)
        ]
        union = 0
        zeros = 0
        for triple in itertools.combinations(points, 3):
            value = determinant(*triple)
            if value == 0:
                zeros += 1
            elif rough[abs(value)]:
                union += 1
        fractions.append(union / total)
        zero_counts.append(zeros)
    return {
        "n": n,
        "sample_count": sample_count,
        "mean_medium_prime_union_fraction": statistics.mean(fractions),
        "population_standard_deviation": statistics.pstdev(fractions),
        "mean_ordinary_collinear_triples": statistics.mean(zero_counts),
        "fractions": fractions,
        "zero_counts": zero_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, nargs="+", required=True)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = {"results": [sample(n, args.samples) for n in args.n]}
    text = json.dumps(payload, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
