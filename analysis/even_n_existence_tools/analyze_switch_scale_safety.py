"""Measure how many permutation 2-switches preserve all short directions.

Every row/column-saturated configuration is a 2-regular bipartite graph and
therefore decomposes into two perfect matchings.  In one matching, choose two
rows a,b and exchange their columns.  This preserves every row and column
degree.  Starting from an exact NTIL solution, every new collinear triple must
contain at least one of the two inserted points.

For each legal switch this script records the minimum primitive direction
scale max(|u|,|v|) among newly created collinear triples.  Thus a switch with
minimum scale q is safe after all direction shells < Q have been closed iff
q >= Q.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
from pathlib import Path

from analyze_large_prime_carries import decode_solution, locate


Point = tuple[int, int]


def determinant(first: Point, second: Point, third: Point) -> int:
    return (second[0] - first[0]) * (third[1] - first[1]) - (
        third[0] - first[0]
    ) * (second[1] - first[1])


def primitive_scale(first: Point, second: Point) -> int:
    dx = abs(second[0] - first[0])
    dy = abs(second[1] - first[1])
    divisor = math.gcd(dx, dy)
    return max(dx // divisor, dy // divisor)


def validate(points: list[Point], n: int) -> None:
    if len(points) != 2 * n or len(set(points)) != 2 * n:
        raise ValueError("point set is not a 2n-element set")
    rows = collections.Counter(x for x, _ in points)
    columns = collections.Counter(y for _, y in points)
    if any(rows[x] != 2 or columns[x] != 2 for x in range(n)):
        raise ValueError("point set is not row/column saturated")
    for triple in itertools.combinations(points, 3):
        if determinant(*triple) == 0:
            raise ValueError(f"input contains a collinear triple: {triple}")


def decompose(points: list[Point], n: int) -> list[list[int]]:
    """Two-edge-colour the 2-regular row-column bipartite graph."""

    edges = list(points)
    by_row: list[list[int]] = [[] for _ in range(n)]
    by_column: list[list[int]] = [[] for _ in range(n)]
    for edge, (row, column) in enumerate(edges):
        by_row[row].append(edge)
        by_column[column].append(edge)
    if any(len(bucket) != 2 for bucket in by_row + by_column):
        raise ValueError("degree is not two")

    color: list[int | None] = [None] * len(edges)
    for start in range(len(edges)):
        if color[start] is not None:
            continue
        color[start] = 0
        stack = [start]
        while stack:
            edge = stack.pop()
            assert color[edge] is not None
            row, column = edges[edge]
            for bucket in (by_row[row], by_column[column]):
                other = bucket[0] if bucket[1] == edge else bucket[1]
                wanted = 1 - color[edge]
                if color[other] is None:
                    color[other] = wanted
                    stack.append(other)
                elif color[other] != wanted:
                    raise ValueError("odd alternating cycle in bipartite graph")

    permutations = [[-1] * n for _ in range(2)]
    for edge, (row, column) in enumerate(edges):
        assert color[edge] is not None
        permutations[color[edge]][row] = column
    if any(sorted(permutation) != list(range(n)) for permutation in permutations):
        raise ValueError("edge colouring did not produce permutations")
    return permutations


def secant_index(points: list[Point], n: int) -> dict[Point, list[tuple[int, int, int]]]:
    """Index old secants by every other grid cell on their full lattice line."""

    result: dict[Point, list[tuple[int, int, int]]] = collections.defaultdict(list)
    for first_index, second_index in itertools.combinations(range(len(points)), 2):
        first = points[first_index]
        second = points[second_index]
        dx = second[0] - first[0]
        dy = second[1] - first[1]
        divisor = math.gcd(abs(dx), abs(dy))
        ux, uy = dx // divisor, dy // divisor
        scale = max(abs(ux), abs(uy))

        # Walk from first in both primitive directions.  A no-three set ensures
        # no third occupied point occurs, but empty cells may lie between or
        # beyond the endpoints.
        for sign in (-1, 1):
            x, y = first
            while True:
                x += sign * ux
                y += sign * uy
                if not (0 <= x < n and 0 <= y < n):
                    break
                cell = (x, y)
                if cell != first and cell != second:
                    result[cell].append((first_index, second_index, scale))
    return result


def minimum_new_scale(
    points: list[Point],
    secants: dict[Point, list[tuple[int, int, int]]],
    removed: tuple[int, int],
    inserted: tuple[Point, Point],
) -> int | None:
    removed_set = set(removed)
    best: int | None = None
    for cell in inserted:
        for first, second, scale in secants.get(cell, ()):
            if first in removed_set or second in removed_set:
                continue
            if best is None or scale < best:
                best = scale

    first_cell, second_cell = inserted
    pair_scale = primitive_scale(first_cell, second_cell)
    for index, point in enumerate(points):
        if index in removed_set:
            continue
        if determinant(first_cell, second_cell, point) == 0:
            if best is None or pair_scale < best:
                best = pair_scale
    return best


def analyze(points: list[Point], n: int) -> dict:
    validate(points, n)
    permutations = decompose(points, n)
    point_index = {point: index for index, point in enumerate(points)}
    secants = secant_index(points, n)
    occupied = set(points)

    histogram: collections.Counter[str] = collections.Counter()
    legal = 0
    full_solution_neighbors = 0
    by_matching = []
    for matching_index, permutation in enumerate(permutations):
        local_histogram: collections.Counter[str] = collections.Counter()
        local_legal = 0
        for first_row, second_row in itertools.combinations(range(n), 2):
            old_first = (first_row, permutation[first_row])
            old_second = (second_row, permutation[second_row])
            new_first = (first_row, permutation[second_row])
            new_second = (second_row, permutation[first_row])
            if new_first in occupied or new_second in occupied:
                continue
            removed = (point_index[old_first], point_index[old_second])
            minimum = minimum_new_scale(
                points, secants, removed, (new_first, new_second)
            )
            key = "none" if minimum is None else str(minimum)
            histogram[key] += 1
            local_histogram[key] += 1
            legal += 1
            local_legal += 1
            if minimum is None:
                full_solution_neighbors += 1
        by_matching.append(
            {
                "matching": matching_index,
                "legal_switches": local_legal,
                "minimum_new_scale_histogram": dict(
                    sorted(
                        local_histogram.items(),
                        key=lambda item: n + 1 if item[0] == "none" else int(item[0]),
                    )
                ),
            }
        )

    thresholds = {}
    maximum_possible_scale = (n - 1) // 2
    for threshold in range(1, maximum_possible_scale + 2):
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
        "point_count": len(points),
        "legal_switches": legal,
        "full_solution_neighbors": full_solution_neighbors,
        "minimum_new_scale_histogram": dict(
            sorted(
                histogram.items(),
                key=lambda item: n + 1 if item[0] == "none" else int(item[0]),
            )
        ),
        "safe_by_threshold": thresholds,
        "by_matching": by_matching,
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
