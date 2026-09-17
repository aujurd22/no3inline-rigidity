"""Exhaust all three-edge alternating-cycle switches around an NTIL solution.

Choose three occupied cells with distinct rows and columns and cyclically
permute their columns.  This removes three points and inserts three, preserving
all row and column degrees.  The script records the minimum primitive scale of
any newly created collinear triple.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
from pathlib import Path

from analyze_large_prime_carries import decode_solution, locate
from analyze_switch_scale_safety import (
    determinant,
    primitive_scale,
    secant_index,
)


Point = tuple[int, int]


def minimum_new_scale(
    points: list[Point],
    point_index: dict[Point, int],
    secants: dict[Point, list[tuple[int, int, int]]],
    removed: tuple[int, int, int],
    inserted: tuple[Point, Point, Point],
    n: int,
) -> int | None:
    removed_set = set(removed)
    best: int | None = None

    # One inserted point plus two retained old points.
    for cell in inserted:
        for first, second, scale in secants.get(cell, ()):
            if first in removed_set or second in removed_set:
                continue
            if best is None or scale < best:
                best = scale

    # Two inserted points plus one retained old point.
    for first_cell, second_cell in itertools.combinations(inserted, 2):
        dx = second_cell[0] - first_cell[0]
        dy = second_cell[1] - first_cell[1]
        divisor = math.gcd(abs(dx), abs(dy))
        ux, uy = dx // divisor, dy // divisor
        scale = max(abs(ux), abs(uy))
        for sign in (-1, 1):
            x, y = first_cell
            while True:
                x += sign * ux
                y += sign * uy
                if not (0 <= x < n and 0 <= y < n):
                    break
                index = point_index.get((x, y))
                if index is not None and index not in removed_set:
                    if best is None or scale < best:
                        best = scale
                    break

    # All three inserted points.
    if determinant(*inserted) == 0:
        scale = primitive_scale(inserted[0], inserted[1])
        if best is None or scale < best:
            best = scale
    return best


def analyze(points: list[Point], n: int) -> dict:
    occupied = set(points)
    point_index = {point: index for index, point in enumerate(points)}
    secants = secant_index(points, n)
    histogram: collections.Counter[str] = collections.Counter()
    witnesses: dict[str, dict] = {}
    legal = 0

    for removed in itertools.combinations(range(len(points)), 3):
        old = tuple(points[index] for index in removed)
        if len({point[0] for point in old}) < 3:
            continue
        if len({point[1] for point in old}) < 3:
            continue
        rows = [point[0] for point in old]
        columns = [point[1] for point in old]
        for shift in (1, 2):
            inserted = tuple(
                (rows[index], columns[(index + shift) % 3])
                for index in range(3)
            )
            if any(cell in occupied for cell in inserted):
                continue
            minimum = minimum_new_scale(
                points, point_index, secants, removed, inserted, n
            )
            key = "none" if minimum is None else str(minimum)
            histogram[key] += 1
            legal += 1
            witnesses.setdefault(
                key,
                {
                    "removed": [list(point) for point in old],
                    "inserted": [list(point) for point in inserted],
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
        "legal_three_edge_cycle_switches": legal,
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
