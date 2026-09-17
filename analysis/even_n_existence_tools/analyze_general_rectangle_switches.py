"""Exhaust every two-point rectangle reconnection of an exact NTIL solution.

Unlike a swap inside one fixed perfect-matching decomposition, this permits
the removed edges to have either alternating colour.  It is the complete
distance-four neighbourhood in the space of row/column-saturated point sets.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
from pathlib import Path

from analyze_large_prime_carries import decode_solution, locate
from analyze_switch_scale_safety import minimum_new_scale, secant_index


Point = tuple[int, int]


def analyze(points: list[Point], n: int) -> dict:
    occupied = set(points)
    secants = secant_index(points, n)
    histogram: collections.Counter[str] = collections.Counter()
    witnesses: dict[str, dict] = {}
    legal = 0

    for first, second in itertools.combinations(range(len(points)), 2):
        first_point = points[first]
        second_point = points[second]
        if (
            first_point[0] == second_point[0]
            or first_point[1] == second_point[1]
        ):
            continue
        inserted = (
            (first_point[0], second_point[1]),
            (second_point[0], first_point[1]),
        )
        if inserted[0] in occupied or inserted[1] in occupied:
            continue
        minimum = minimum_new_scale(
            points, secants, (first, second), inserted
        )
        key = "none" if minimum is None else str(minimum)
        histogram[key] += 1
        legal += 1
        witnesses.setdefault(
            key,
            {
                "removed": [list(first_point), list(second_point)],
                "inserted": [list(inserted[0]), list(inserted[1])],
            },
        )

    thresholds = {}
    for threshold in range(1, (n - 1) // 2 + 2):
        count = histogram["none"] + sum(
            amount
            for scale, amount in histogram.items()
            if scale != "none" and int(scale) >= threshold
        )
        thresholds[str(threshold)] = {
            "safe_switches": count,
            "fraction_of_legal": count / legal if legal else None,
        }
    return {
        "n": n,
        "legal_general_rectangle_switches": legal,
        "full_solution_neighbors": histogram["none"],
        "minimum_new_scale_histogram": dict(
            sorted(
                histogram.items(),
                key=lambda item: n + 1 if item[0] == "none" else int(item[0]),
            )
        ),
        "safe_by_threshold": thresholds,
        "one_witness_by_exact_minimum_scale": witnesses,
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
    text = json.dumps(payload, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
