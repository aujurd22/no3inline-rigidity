"""Exhaust the small C4 fundamental-domain model.

An exact C4-symmetric 4m-point configuration on a 2m grid is determined by
an m-cell set A in the top-left quadrant.  If r_i and c_i are its row and
column degrees, exact row/column saturation is equivalent to r_i+c_i=2.

Conjectural structural strengthening:
If the full C4 orbit of A is NTIL, then its reduced four-regular multigraph is
the C4 orbit (with multiplicity) of a single permutation.

The program checks this implication exhaustively for small m.
"""

from __future__ import annotations

import argparse
import itertools
import json
import time


def rotate_base(edge: tuple[int, int], m: int) -> tuple[int, int]:
    return (m - 1 - edge[1], edge[0])


def base_orbits(m: int) -> tuple[list[tuple[tuple[int, int], ...]], dict[tuple[int, int], int]]:
    unseen = {(x, y) for x in range(m) for y in range(m)}
    orbits = []
    while unseen:
        edge = min(unseen)
        orbit = []
        current = edge
        for _ in range(4):
            if current not in orbit:
                orbit.append(current)
            current = rotate_base(current, m)
        for member in orbit:
            unseen.discard(member)
        orbits.append(tuple(orbit))
    lookup = {
        edge: orbit_index
        for orbit_index, orbit in enumerate(orbits)
        for edge in orbit
    }
    return orbits, lookup


def permutation_signatures(m: int, lookup: dict[tuple[int, int], int], orbit_count: int) -> set[tuple[int, ...]]:
    signatures = set()
    for permutation in itertools.permutations(range(m)):
        counts = [0] * orbit_count
        for x, y in enumerate(permutation):
            counts[lookup[(x, y)]] += 1
        signatures.add(tuple(counts))
    return signatures


def full_c4_orbit(A: tuple[tuple[int, int], ...], m: int) -> list[tuple[int, int]]:
    points = set()
    for point in A:
        current = point
        for _ in range(4):
            points.add(current)
            current = (2 * m - 1 - current[1], current[0])
    return list(points)


def is_ntil(points: list[tuple[int, int]]) -> bool:
    for first, second, third in itertools.combinations(points, 3):
        if (second[0] - first[0]) * (third[1] - first[1]) == (
            second[1] - first[1]
        ) * (third[0] - first[0]):
            return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m", type=int, required=True)
    args = parser.parse_args()
    m = args.m
    orbits, lookup = base_orbits(m)
    good_signatures = permutation_signatures(m, lookup, len(orbits))

    total = 0
    signatures_without_generator = 0
    ntil = 0
    counterexamples = []
    started = time.perf_counter()

    for row_degrees in itertools.product(range(3), repeat=m):
        if sum(row_degrees) != m:
            continue
        remaining_columns = [2 - degree for degree in row_degrees]
        chosen: list[tuple[int, int]] = []

        def visit(row: int) -> None:
            nonlocal total, signatures_without_generator, ntil
            if row == m:
                if any(remaining_columns):
                    return
                total += 1
                signature = [0] * len(orbits)
                for edge in chosen:
                    signature[lookup[edge]] += 1
                has_generator = tuple(signature) in good_signatures
                if not has_generator:
                    signatures_without_generator += 1
                points = full_c4_orbit(tuple(chosen), m)
                if len(points) != 4 * m or not is_ntil(points):
                    return
                ntil += 1
                if not has_generator:
                    counterexamples.append(tuple(chosen))
                    print(
                        json.dumps(
                            {"counterexample": chosen, "points": points},
                            indent=2,
                        ),
                        flush=True,
                    )
                return

            available = [
                column
                for column, capacity in enumerate(remaining_columns)
                if capacity
            ]
            for columns in itertools.combinations(available, row_degrees[row]):
                for column in columns:
                    remaining_columns[column] -= 1
                    chosen.append((row, column))
                if sum(remaining_columns) == sum(row_degrees[row + 1 :]):
                    visit(row + 1)
                for _ in columns:
                    chosen.pop()
                for column in columns:
                    remaining_columns[column] += 1

        visit(0)

    print(
        json.dumps(
            {
                "summary": True,
                "m": m,
                "fundamental_domains": total,
                "without_orbit_permutation_generator": signatures_without_generator,
                "ntil_fundamental_domains": ntil,
                "ntil_without_generator": len(counterexamples),
                "elapsed_seconds": time.perf_counter() - started,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
