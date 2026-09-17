"""Measure modular collinear triples for every prime n <= p < 2n-2.

For a row/column-saturated 2n-point set in the n by n integer grid, reduction
modulo any prime p >= n is injective.  The non-axis affine lines over F_p have

    I = 2n(p-1) point-line incidences,
    K = n(2n-3) pairs.

The pointwise inequality

    C(r, 3) >= (2 C(r, 2) - r) / 3

therefore gives

    T_p >= 2n(2n-p-2)/3.

This script checks the exact modular-triple counts and carry histograms on the
known quarter-turn-symmetric extremal configurations.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
from pathlib import Path

from analyze_c4_fundamental_cycles import decode_record


Point = tuple[int, int]


def primes_below(limit: int) -> list[int]:
    sieve = bytearray(b"\x01") * limit
    if limit:
        sieve[0] = 0
    if limit > 1:
        sieve[1] = 0
    for value in range(2, math.isqrt(limit - 1) + 1):
        if sieve[value]:
            sieve[value * value : limit : value] = b"\x00" * (
                (limit - 1 - value * value) // value + 1
            )
    return [value for value in range(2, limit) if sieve[value]]


def determinant(first: Point, second: Point, third: Point) -> int:
    x1, y1 = first
    x2, y2 = second
    x3, y3 = third
    return (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)


def analyze(points: list[Point], n: int) -> dict:
    primes = [p for p in primes_below(2 * n - 2) if p >= n]
    histograms = {p: collections.Counter() for p in primes}
    ordinary = 0
    all_determinants: list[int] = []
    for triple in itertools.combinations(points, 3):
        value = determinant(*triple)
        if value == 0:
            ordinary += 1
            continue
        all_determinants.append(value)
        for p in primes:
            if value % p == 0:
                histograms[p][value // p] += 1

    rows = []
    triple_ids_are_disjoint = True
    # Since |D| <= (n-1)^2 < p*q for distinct p,q >= n, the statement below
    # also follows mathematically.  Retain an explicit data check.
    for value in all_determinants:
        if sum(value % p == 0 for p in primes) > 1:
            triple_ids_are_disjoint = False
            break

    for p in primes:
        histogram = histograms[p]
        count = sum(histogram.values())
        numerator = 2 * n * (2 * n - p - 2)
        lower_bound = max(0, math.ceil(numerator / 3))
        rows.append(
            {
                "p": p,
                "modular_collinear_triples": count,
                "lower_bound": lower_bound,
                "ratio_to_lower_bound": count / lower_bound if lower_bound else None,
                "distinct_signed_carries": len(histogram),
                "minimum_carry": min(histogram, default=None),
                "maximum_carry": max(histogram, default=None),
                "mean_absolute_carry": (
                    sum(abs(carry) * amount for carry, amount in histogram.items())
                    / count
                    if count
                    else None
                ),
                "carry_histogram": dict(sorted(histogram.items())),
            }
        )

    return {
        "n": n,
        "point_count": len(points),
        "ordinary_collinear_triples": ordinary,
        "prime_count": len(primes),
        "different_prime_triple_sets_disjoint": triple_ids_are_disjoint,
        "total_modular_triples_over_large_primes": sum(
            row["modular_collinear_triples"] for row in rows
        ),
        "total_lower_bound": sum(row["lower_bound"] for row in rows),
        "ratio_total_to_lower_bound": (
            sum(row["modular_collinear_triples"] for row in rows)
            / sum(row["lower_bound"] for row in rows)
            if sum(row["lower_bound"] for row in rows)
            else None
        ),
        "primes": rows,
    }


def locate(cache: Path, n: int) -> Path:
    for suffix in ("", ".few", ".mvr"):
        path = cache / f"n{n}_rot4{suffix}"
        if path.exists():
            return path
    raise FileNotFoundError(f"no compact n={n} record in {cache}")


def decode_solution(path: Path, n: int) -> list[Point]:
    line = next(text.strip() for text in path.read_text().splitlines() if text.strip())
    return decode_record(line, n, coordinate_format=" " in line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--n", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    results = []
    for n in args.n:
        path = locate(args.cache, n)
        points = decode_solution(path, n)
        results.append(analyze(points, n))
    payload = {"results": results}
    text = json.dumps(payload, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
