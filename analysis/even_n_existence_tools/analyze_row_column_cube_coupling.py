"""Measure simultaneous row-cube and column-cube occupancy of large primes.

Every triple whose nonzero determinant is divisible by p >= n has three
distinct rows and three distinct columns.  It is therefore one vertex of an
eight-determinant row cube and one vertex of a transposed column cube.  This
script records the joint occupancy (k_row, k_column) for every such labelled
triple.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
from pathlib import Path

from analyze_large_prime_carries import (
    decode_solution,
    determinant,
    locate,
    primes_below,
)


Point = tuple[int, int]


def analyze(points: list[Point], n: int) -> dict:
    rows: list[list[int]] = [[] for _ in range(n)]
    columns: list[list[int]] = [[] for _ in range(n)]
    for row, column in points:
        rows[row].append(column)
        columns[column].append(row)
    if any(len(bucket) != 2 for bucket in rows + columns):
        raise ValueError("configuration is not row/column saturated")

    maximum = (n - 1) ** 2
    large_prime_factor = [0] * (maximum + 1)
    for prime in primes_below(maximum + 1):
        if prime < n:
            continue
        for value in range(prime, maximum + 1, prime):
            if large_prime_factor[value]:
                raise AssertionError(
                    "a determinant magnitude has two prime factors at least n"
                )
            large_prime_factor[value] = prime

    row_cache: dict[tuple[tuple[int, int, int], int], int] = {}
    column_cache: dict[tuple[tuple[int, int, int], int], int] = {}

    def row_occupancy(row_triple: tuple[int, int, int], prime: int) -> int:
        key = (row_triple, prime)
        if key not in row_cache:
            first, second, third = row_triple
            row_cache[key] = sum(
                determinant(
                    (first, first_column),
                    (second, second_column),
                    (third, third_column),
                )
                % prime
                == 0
                for first_column in rows[first]
                for second_column in rows[second]
                for third_column in rows[third]
            )
        return row_cache[key]

    def column_occupancy(
        column_triple: tuple[int, int, int], prime: int
    ) -> int:
        key = (column_triple, prime)
        if key not in column_cache:
            first, second, third = column_triple
            column_cache[key] = sum(
                determinant(
                    (first_row, first),
                    (second_row, second),
                    (third_row, third),
                )
                % prime
                == 0
                for first_row in columns[first]
                for second_row in columns[second]
                for third_row in columns[third]
            )
        return column_cache[key]

    matrix: collections.Counter[tuple[int, int]] = collections.Counter()
    labelled_triples = 0
    for triple in itertools.combinations(points, 3):
        value = abs(determinant(*triple))
        prime = large_prime_factor[value]
        if not prime:
            continue
        row_triple = tuple(sorted(row for row, _ in triple))
        column_triple = tuple(sorted(column for _, column in triple))
        if len(set(row_triple)) != 3 or len(set(column_triple)) != 3:
            raise AssertionError("a p >= n label has a repeated row or column")
        row_count = row_occupancy(row_triple, prime)
        column_count = column_occupancy(column_triple, prime)
        matrix[row_count, column_count] += 1
        labelled_triples += 1

    return {
        "n": n,
        "large_prime_labelled_triples": labelled_triples,
        "joint_occupancy_matrix": {
            f"{row_count},{column_count}": amount
            for (row_count, column_count), amount in sorted(matrix.items())
        },
        "triple_incidences_with_row_and_column_occupancy_three": sum(
            amount
            for (row_count, column_count), amount in matrix.items()
            if row_count == 3 and column_count == 3
        ),
        "triple_incidences_with_one_occupancy_three_and_other_above_one": sum(
            amount
            for (row_count, column_count), amount in matrix.items()
            if (row_count == 3 and column_count > 1)
            or (column_count == 3 and row_count > 1)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--n", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = {
        "results": [
            analyze(decode_solution(locate(args.cache, n), n), n) for n in args.n
        ]
    }
    encoded = json.dumps(payload, indent=2)
    print(encoded)
    if args.output:
        args.output.write_text(encoded)


if __name__ == "__main__":
    main()
