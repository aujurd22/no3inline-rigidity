"""Exhaust nested n -> n+2 gap-insertion chains from all small solutions.

An extension chooses two new row coordinates and two new column coordinates,
embeds every old point order-preservingly in the complementary coordinates,
and adds the four forced points at the new-row/new-column intersections.
It is the unique extension that preserves every old point and keeps two
points in every row and column.

Unlike scans from one cached record, this program enumerates every saturated
NTIL set expressible as two disjoint permutation graphs at a small seed order,
deduplicates the uncoloured point sets, and follows every valid extension.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math


Point = tuple[int, int]
Configuration = tuple[Point, ...]


def normal_direction(dx: int, dy: int) -> tuple[int, int]:
    divisor = math.gcd(abs(dx), abs(dy))
    dx //= divisor
    dy //= divisor
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return dx, dy


def no_three(points: Configuration | list[Point]) -> bool:
    for first_index, first in enumerate(points):
        seen: set[tuple[int, int]] = set()
        for second_index, second in enumerate(points):
            if first_index == second_index:
                continue
            direction = normal_direction(
                second[0] - first[0], second[1] - first[1]
            )
            if direction in seen:
                return False
            seen.add(direction)
    return True


def seed_configurations(n: int) -> set[Configuration]:
    permutations = list(itertools.permutations(range(n)))
    result: set[Configuration] = set()
    for first_index, first in enumerate(permutations):
        for second in permutations[first_index + 1 :]:
            if any(a == b for a, b in zip(first, second)):
                continue
            points = tuple(
                sorted(
                    [(row, first[row]) for row in range(n)]
                    + [(row, second[row]) for row in range(n)]
                )
            )
            if points not in result and no_three(points):
                result.add(points)
    return result


def complement_map(n: int, gaps: tuple[int, int]) -> tuple[int, ...]:
    return tuple(
        coordinate for coordinate in range(n + 2) if coordinate not in gaps
    )


def extensions(configuration: Configuration, n: int):
    gap_pairs = list(itertools.combinations(range(n + 2), 2))
    maps = {gaps: complement_map(n, gaps) for gaps in gap_pairs}
    for row_gaps in gap_pairs:
        row_map = maps[row_gaps]
        row_embedded = [(row_map[x], y) for x, y in configuration]
        for column_gaps in gap_pairs:
            column_map = maps[column_gaps]
            points = [
                (x, column_map[y]) for x, y in row_embedded
            ]
            points.extend(
                (x, y) for x in row_gaps for y in column_gaps
            )
            candidate = tuple(sorted(points))
            if no_three(candidate):
                yield row_gaps, column_gaps, candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-n", type=int, default=4)
    parser.add_argument("--maximum-n", type=int, default=16)
    parser.add_argument(
        "--configuration-limit",
        type=int,
        default=0,
        help="diagnostic cap after each level; zero means exhaustive",
    )
    args = parser.parse_args()

    current = seed_configurations(args.seed_n)
    witnesses: dict[Configuration, list[dict]] = {
        configuration: [] for configuration in current
    }
    print(
        json.dumps(
            {
                "n": args.seed_n,
                "configurations": len(current),
                "source": "all disjoint permutation pairs",
            }
        ),
        flush=True,
    )
    n = args.seed_n
    while current and n + 2 <= args.maximum_n:
        next_witnesses: dict[Configuration, list[dict]] = {}
        attempted = 0
        valid_transitions = 0
        for configuration in current:
            for row_gaps, column_gaps, candidate in extensions(configuration, n):
                valid_transitions += 1
                if candidate not in next_witnesses:
                    next_witnesses[candidate] = witnesses[configuration] + [
                        {
                            "from_n": n,
                            "row_gaps": row_gaps,
                            "column_gaps": column_gaps,
                        }
                    ]
                attempted += 1
        n += 2
        if args.configuration_limit and len(next_witnesses) > args.configuration_limit:
            next_witnesses = dict(
                itertools.islice(next_witnesses.items(), args.configuration_limit)
            )
        current = set(next_witnesses)
        witnesses = next_witnesses
        first = next(iter(current), None)
        print(
            json.dumps(
                {
                    "n": n,
                    "configurations": len(current),
                    "valid_transitions": valid_transitions,
                    "first_chain": witnesses[first] if first else None,
                    "first_configuration": first,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
