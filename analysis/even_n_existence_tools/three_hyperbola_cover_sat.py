"""Choose two points per row/column from three modular hyperbola layers.

For an odd prime p and distinct nonzero multipliers a,b,c, let

    H_a = {(x, a/x mod p): x=1,...,p-1}.

After subtracting one from both coordinates these are three disjoint
permutations on the n=p-1 board, hence their union X has exactly three points
in every row and column.  We seek a perfect matching R inside this 3-regular
bipartite graph that hits every rich Euclidean line sufficiently often:

    |R intersect L| >= |X intersect L| - 2.

Then X\\R has exactly 2n points and at most two on every line.  This model is
strictly more flexible than selecting two fixed hyperbola layers.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from collections import defaultdict

from ortools.sat.python import cp_model


Point = tuple[int, int]
Line = tuple[int, int, int]


def canonical_line(first: Point, second: Point) -> Line:
    x1, y1 = first
    x2, y2 = second
    a = y2 - y1
    b = x1 - x2
    c = x2 * y1 - x1 * y2
    divisor = math.gcd(abs(a), math.gcd(abs(b), abs(c)))
    a //= divisor
    b //= divisor
    c //= divisor
    if a < 0 or (a == 0 and b < 0):
        a, b, c = -a, -b, -c
    return a, b, c


def hyperbola_union(p: int, multipliers: tuple[int, int, int]) -> dict[Point, int]:
    points: dict[Point, int] = {}
    for layer, multiplier in enumerate(multipliers):
        for residue_x in range(1, p):
            residue_y = multiplier * pow(residue_x, -1, p) % p
            point = (residue_x - 1, residue_y - 1)
            if point in points:
                raise ValueError("hyperbola layers are not disjoint")
            points[point] = layer
    return points


def rich_lines(points: set[Point]) -> list[tuple[Point, ...]]:
    pairs_by_line: dict[Line, set[Point]] = defaultdict(set)
    ordered = sorted(points)
    for first, second in itertools.combinations(ordered, 2):
        line = canonical_line(first, second)
        pairs_by_line[line].add(first)
        pairs_by_line[line].add(second)
    return [
        tuple(sorted(on_line))
        for on_line in pairs_by_line.values()
        if len(on_line) >= 3
    ]


def determinant(a: Point, b: Point, c: Point) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (
        b[1] - a[1]
    )


def verify(selected: set[Point], n: int) -> dict:
    row_counts = [sum(x == row for x, _ in selected) for row in range(n)]
    column_counts = [sum(y == column for _, y in selected) for column in range(n)]
    bad = sum(
        determinant(a, b, c) == 0
        for a, b, c in itertools.combinations(selected, 3)
    )
    return {
        "selected_points": len(selected),
        "rows_two": row_counts == [2] * n,
        "columns_two": column_counts == [2] * n,
        "collinear_triples": bad,
        "valid": (
            len(selected) == 2 * n
            and row_counts == [2] * n
            and column_counts == [2] * n
            and bad == 0
        ),
    }


def solve(
    p: int,
    multipliers: tuple[int, int, int],
    workers: int,
    time_limit: float,
    seed: int,
) -> dict:
    n = p - 1
    point_layers = hyperbola_union(p, multipliers)
    points = set(point_layers)
    started = time.perf_counter()
    lines = rich_lines(points)
    build_seconds = time.perf_counter() - started

    model = cp_model.CpModel()
    removed = {
        point: model.new_bool_var(f"r_{point[0]}_{point[1]}")
        for point in points
    }
    for row in range(n):
        model.add(sum(removed[pnt] for pnt in points if pnt[0] == row) == 1)
    for column in range(n):
        model.add(sum(removed[pnt] for pnt in points if pnt[1] == column) == 1)
    for line in lines:
        model.add(sum(removed[point] for point in line) >= len(line) - 2)

    # The fixed-layer solutions are useful starting points even though they
    # usually violate some rich-line constraints.
    for point, variable in removed.items():
        model.add_hint(variable, int(point_layers[point] == 2))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    status = solver.solve(model)
    result = {
        "p": p,
        "n": n,
        "multipliers": multipliers,
        "status": solver.status_name(status),
        "candidate_points": len(points),
        "rich_lines": len(lines),
        "rich_line_size_histogram": {
            size: sum(len(line) == size for line in lines)
            for size in sorted({len(line) for line in lines})
        },
        "line_build_seconds": build_seconds,
        "solve_wall_seconds": solver.wall_time,
        "branches": solver.num_branches,
        "conflicts": solver.num_conflicts,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        removed_points = {
            point for point, variable in removed.items() if solver.value(variable)
        }
        selected = points - removed_points
        result.update(
            {
                "removed_layer_histogram": {
                    layer: sum(point_layers[point] == layer for point in removed_points)
                    for layer in range(3)
                },
                "removed_points": sorted(removed_points),
                "selected_points": sorted(selected),
                "verification": verify(selected, n),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--multipliers", type=int, nargs=3, default=(1, 2, 3))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    multipliers = tuple(value % args.p for value in args.multipliers)
    if 0 in multipliers or len(set(multipliers)) != 3:
        raise ValueError("multipliers must be distinct and nonzero modulo p")
    result = solve(
        args.p, multipliers, args.workers, args.time_limit, args.seed
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
