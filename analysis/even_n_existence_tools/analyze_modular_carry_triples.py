"""Analyze finite-field collinear triples and their nonzero integer carries.

For a known n=p-1 saturated NTIL solution, every triple whose determinant is
0 modulo p must have a nonzero integer determinant k*p.  This script records
the exact count and carry histogram and compares it with the universal lower
bound (p-1)(p-5)/2.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
from pathlib import Path

from analyze_c4_fundamental_cycles import decode_first


Point = tuple[int, int]


def determinant(first: Point, second: Point, third: Point) -> int:
    x1, y1 = first
    x2, y2 = second
    x3, y3 = third
    return (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)


def analyze(points: list[Point], n: int) -> dict:
    p = n + 1
    carry_histogram: collections.Counter[int] = collections.Counter()
    zero_determinants = 0
    for triple in itertools.combinations(points, 3):
        value = determinant(*triple)
        if value % p != 0:
            continue
        if value == 0:
            zero_determinants += 1
        else:
            carry_histogram[value // p] += 1
    modular_triples = zero_determinants + sum(carry_histogram.values())
    lower_bound = (p - 1) * (p - 5) // 2
    return {
        "n": n,
        "p": p,
        "point_count": len(points),
        "modular_collinear_triples": modular_triples,
        "universal_lower_bound": lower_bound,
        "ratio_to_lower_bound": (
            modular_triples / lower_bound if lower_bound else None
        ),
        "ordinary_collinear_triples": zero_determinants,
        "distinct_signed_carries": len(carry_histogram),
        "minimum_carry": min(carry_histogram, default=None),
        "maximum_carry": max(carry_histogram, default=None),
        "mean_absolute_carry": (
            sum(abs(carry) * count for carry, count in carry_histogram.items())
            / sum(carry_histogram.values())
            if carry_histogram
            else None
        ),
        "carry_histogram": dict(sorted(carry_histogram.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--compact", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    points = decode_first(Path(args.compact), args.n)
    result = analyze(points, args.n)
    print(json.dumps(result))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
