"""Test the two modular-line construction for p = n+1 = 1 mod 4.

Use doubled centered coordinates u=2x-(n-1), v=2y-(n-1).  For a square
root s of -1 modulo p, take every grid point satisfying

    v = s*u  or  v = -s*u  (mod p).

Because x=0,...,p-2 parametrises every nonzero u, this is the union of two
disjoint permutation graphs and has exactly 2(p-1)=2n points.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math


Point = tuple[int, int]


def is_prime(value: int) -> bool:
    return value >= 2 and all(
        value % divisor for divisor in range(2, math.isqrt(value) + 1)
    )


def sqrt_minus_one(p: int) -> int:
    return next(value for value in range(1, p) if value * value % p == p - 1)


def construction(p: int) -> list[Point]:
    n = p - 1
    s = sqrt_minus_one(p)
    inverse_two = pow(2, -1, p)
    points = set()
    for x in range(n):
        u = (2 * x - (n - 1)) % p
        if u == 0:
            raise AssertionError("the board coordinate image should omit zero")
        for sign in (-1, 1):
            v = sign * s * u % p
            y = ((v + (n - 1)) * inverse_two) % p
            if y == p - 1:
                raise AssertionError("nonzero v should map inside the board")
            points.add((x, y))
    if len(points) != 2 * n:
        raise AssertionError("two modular lines should be disjoint off the origin")
    return sorted(points)


def canonical_line(a: Point, b: Point) -> tuple[int, int, int]:
    x1, y1 = a
    x2, y2 = b
    A = y2 - y1
    B = x1 - x2
    C = x2 * y1 - x1 * y2
    divisor = math.gcd(abs(A), math.gcd(abs(B), abs(C)))
    A //= divisor
    B //= divisor
    C //= divisor
    if A < 0 or (A == 0 and B < 0):
        A, B, C = -A, -B, -C
    return A, B, C


def line_spectrum(points: list[Point]) -> dict:
    lines: dict[tuple[int, int, int], set[Point]] = {}
    for a, b in itertools.combinations(points, 2):
        key = canonical_line(a, b)
        lines.setdefault(key, set()).update((a, b))
    rich = [(key, members) for key, members in lines.items() if len(members) >= 3]
    histogram = collections.Counter(len(members) for _, members in rich)
    return {
        "bad_lines": len(rich),
        "line_size_histogram": dict(sorted(histogram.items())),
        "maximum_line_size": max(histogram, default=2),
        "examples": [
            {"line": key, "points": sorted(members)}
            for key, members in sorted(rich, key=lambda item: -len(item[1]))[:10]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-p", type=int, default=500)
    parser.add_argument("--output")
    args = parser.parse_args()
    records = []
    for p in range(5, args.maximum_p + 1, 4):
        if not is_prime(p):
            continue
        points = construction(p)
        record = {
            "p": p,
            "n": p - 1,
            "sqrt_minus_one": sqrt_minus_one(p),
            "points": points,
            **line_spectrum(points),
        }
        records.append(record)
        print(
            json.dumps(
                {key: value for key, value in record.items() if key != "points"}
            ),
            flush=True,
        )
    if args.output:
        with open(args.output, "w") as stream:
            json.dump(records, stream, indent=2)


if __name__ == "__main__":
    main()
