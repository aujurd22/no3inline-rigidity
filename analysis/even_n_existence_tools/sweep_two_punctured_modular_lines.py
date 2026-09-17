"""Exhaust pairs of modular lines through the omitted corner.

For prime p put n=p-1 and identify the board coordinates with
F_p \\ {-1}.  For each nonzero slope s, the punctured modular line

    y + 1 = s (x + 1)  (mod p)

is a permutation graph on the n by n board.  The union for two distinct
slopes has exactly two points in every row and column.  We test whether its
standard integer representatives contain a collinear triple.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math


Point = tuple[int, int]


def is_prime(value: int) -> bool:
    return value >= 2 and all(
        value % divisor for divisor in range(2, math.isqrt(value) + 1)
    )


def points_for_slopes(p: int, first: int, second: int) -> list[Point]:
    return [
        point
        for x in range(p - 1)
        for point in (
            (x, (first * (x + 1) - 1) % p),
            (x, (second * (x + 1) - 1) % p),
        )
    ]


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


def first_bad_line(points: list[Point]) -> tuple[int, int, int] | None:
    seen: set[tuple[int, int, int]] = set()
    for a, b in itertools.combinations(points, 2):
        line = canonical_line(a, b)
        if line in seen:
            return line
        seen.add(line)
    return None


def bad_line_count(points: list[Point]) -> tuple[int, int]:
    counts: dict[tuple[int, int, int], int] = {}
    for a, b in itertools.combinations(points, 2):
        line = canonical_line(a, b)
        counts[line] = counts.get(line, 0) + 1
    rich = [pairs for pairs in counts.values() if pairs >= 3]
    # A line with k points contributes C(k,2) pairs.
    maximum = max(
        (
            (1 + math.isqrt(1 + 8 * pairs)) // 2
            for pairs in rich
        ),
        default=2,
    )
    return len(rich), maximum


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-p", type=int, default=101)
    parser.add_argument("--output")
    args = parser.parse_args()
    records = []
    for p in range(3, args.maximum_p + 1):
        if not is_prime(p):
            continue
        best = None
        solutions = []
        for first, second in itertools.combinations(range(1, p), 2):
            points = points_for_slopes(p, first, second)
            witness = first_bad_line(points)
            if witness is None:
                solutions.append((first, second))
                score = (0, 2)
            else:
                score = bad_line_count(points)
            candidate = {
                "slopes": [first, second],
                "bad_lines": score[0],
                "maximum_line_size": score[1],
                "first_bad_line": witness,
            }
            if best is None or (
                candidate["bad_lines"],
                candidate["maximum_line_size"],
            ) < (
                best["bad_lines"],
                best["maximum_line_size"],
            ):
                best = candidate
        record = {
            "p": p,
            "n": p - 1,
            "slope_pairs": math.comb(p - 1, 2),
            "solutions": solutions,
            "best": best,
        }
        records.append(record)
        print(json.dumps(record), flush=True)
    if args.output:
        with open(args.output, "w") as stream:
            json.dump(records, stream, indent=2)


if __name__ == "__main__":
    main()
