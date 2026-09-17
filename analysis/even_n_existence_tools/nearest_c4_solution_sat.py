"""Find the exact nearest C4-symmetric NTIL configuration.

Variables are the m^2 possible cells in the top-left m by m fundamental
domain of a 2m by 2m board.  Selecting a cell selects its complete C4 orbit.

The row/column saturation condition is the degree-two condition

    sum_y z[v,y] + sum_x z[x,v] = 2,

where a loop z[v,v] has coefficient two.  For each maximal grid line L,
the exact NTIL condition is

    sum_c |orbit(c) intersect L| z[c] <= 2.

This is an exact 0-1 linear formulation; no list of collinear triples is
needed.  The objective minimizes the number of selected cells not shared
with a supplied reference fundamental domain.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
import time

from ortools.sat.python import cp_model


Cell = tuple[int, int]
Point = tuple[int, int]
Line = tuple[int, int, int]


def parse_cells(text: str) -> tuple[Cell, ...]:
    return tuple(
        (int(first), int(second))
        for first, second in re.findall(r"\((-?\d+),\s*(-?\d+)\)", text)
    )


def rotate(point: Point, n: int) -> Point:
    x, y = point
    return (n - 1 - y, x)


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
    return (a, b, c)


def point_cell_map(m: int) -> dict[Point, Cell]:
    n = 2 * m
    result: dict[Point, Cell] = {}
    for cell in ((x, y) for x in range(m) for y in range(m)):
        point = cell
        for _ in range(4):
            if point in result:
                raise AssertionError("C4 fundamental-domain orbits overlap")
            result[point] = cell
            point = rotate(point, n)
    if len(result) != n * n:
        raise AssertionError("C4 orbits do not cover the board")
    return result


def long_grid_lines(
    n: int,
) -> tuple[list[tuple[Point, ...]], dict[str, int | float]]:
    """Enumerate each maximal grid line containing at least three points.

    Give every unoriented primitive direction its representative (dx, dy)
    with dx > 0, plus the vertical direction (0, 1).  A maximal line has a
    unique first grid point p in that direction, characterized by p-d being
    outside the board.  Requiring p+2d inside is exactly the three-point test.
    """

    started = time.perf_counter()
    maximum_step = (n - 1) // 2
    directions = [(0, 1)]
    directions.extend(
        (dx, dy)
        for dx in range(1, maximum_step + 1)
        for dy in range(-maximum_step, maximum_step + 1)
        if math.gcd(dx, abs(dy)) == 1
    )
    lines: list[tuple[Point, ...]] = []
    for dx, dy in directions:
        for x in range(n):
            for y in range(n):
                if 0 <= x - dx < n and 0 <= y - dy < n:
                    continue
                if not (0 <= x + 2 * dx < n and 0 <= y + 2 * dy < n):
                    continue
                points = []
                current_x, current_y = x, y
                while 0 <= current_x < n and 0 <= current_y < n:
                    points.append((current_x, current_y))
                    current_x += dx
                    current_y += dy
                lines.append(tuple(points))
    return lines, {
        "primitive_directions_with_possible_three_point_lines": len(
            directions
        ),
        "lines_with_at_least_three_grid_points": len(lines),
        "line_enumeration_seconds": time.perf_counter() - started,
    }


def build_model(
    m: int,
    reference: set[Cell],
    minimize_changes: bool,
    hint_reference: bool,
) -> tuple[
    cp_model.CpModel,
    dict[Cell, cp_model.IntVar],
    cp_model.LinearExpr,
    dict[str, int | float],
]:
    n = 2 * m
    point_to_cell = point_cell_map(m)
    lines, statistics = long_grid_lines(n)
    model = cp_model.CpModel()
    variables = {
        (x, y): model.new_bool_var(f"z_{x}_{y}")
        for x in range(m)
        for y in range(m)
    }

    model.add(sum(variables.values()) == m)
    for vertex in range(m):
        terms = []
        for second in range(m):
            terms.append(variables[(vertex, second)])
        for first in range(m):
            terms.append(variables[(first, vertex)])
        model.add(sum(terms) == 2)

    coefficient_histogram: collections.Counter[int] = collections.Counter()
    line_constraint_count = 0
    seen_line_signatures: set[tuple[tuple[Cell, int], ...]] = set()
    for line_points in lines:
        cell_counts: collections.Counter[Cell] = collections.Counter(
            point_to_cell[point] for point in line_points
        )
        signature = tuple(sorted(cell_counts.items()))
        if signature in seen_line_signatures:
            continue
        seen_line_signatures.add(signature)
        model.add(
            sum(
                coefficient * variables[cell]
                for cell, coefficient in cell_counts.items()
            )
            <= 2
        )
        coefficient_histogram.update(cell_counts.values())
        line_constraint_count += 1

    overlap = sum(variables[cell] for cell in reference)
    changes = m - overlap
    if minimize_changes:
        model.minimize(changes)
    if hint_reference:
        for cell, variable in variables.items():
            model.add_hint(variable, int(cell in reference))
    statistics.update(
        {
            "variables": len(variables),
            "degree_constraints": m,
            "raw_line_constraints_before_c4_deduplication": len(lines),
            "line_constraints": line_constraint_count,
            "line_cell_coefficient_histogram": dict(
                sorted(coefficient_histogram.items())
            ),
        }
    )
    return model, variables, changes, statistics


def determinant(first: Point, second: Point, third: Point) -> int:
    return (second[0] - first[0]) * (third[1] - first[1]) - (
        second[1] - first[1]
    ) * (third[0] - first[0])


def verify(cells: tuple[Cell, ...], m: int) -> dict[str, int | bool]:
    n = 2 * m
    degree = [0] * m
    points: list[Point] = []
    for first, second in cells:
        degree[first] += 1
        degree[second] += 1
        point = (first, second)
        for _ in range(4):
            points.append(point)
            point = rotate(point, n)
    bad = 0
    for first, second, third in __import__("itertools").combinations(points, 3):
        bad += determinant(first, second, third) == 0
    return {
        "cell_count": len(cells),
        "point_count": len(points),
        "distinct_points": len(set(points)),
        "degree_two": degree == [2] * m,
        "collinear_triples": bad,
        "valid": (
            len(cells) == m
            and len(set(points)) == 4 * m
            and degree == [2] * m
            and bad == 0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--time-limit", type=float, default=3600.0)
    parser.add_argument("--log-search", action="store_true")
    parser.add_argument("--satisfaction", action="store_true")
    parser.add_argument("--hint-reference", action="store_true")
    args = parser.parse_args()
    reference = set(parse_cells(args.reference))
    if len(reference) != args.m:
        raise ValueError("reference must contain exactly m distinct cells")

    model, variables, changes, statistics = build_model(
        args.m,
        reference,
        minimize_changes=not args.satisfaction,
        hint_reference=args.hint_reference,
    )
    print(
        json.dumps({"model_built": True, **statistics}),
        file=sys.stderr,
        flush=True,
    )
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = args.workers
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.log_search_progress = args.log_search
    started = time.perf_counter()
    status = solver.solve(model)
    result: dict = {
        "m": args.m,
        "n": 2 * args.m,
        "status": solver.status_name(status),
        "wall_seconds": time.perf_counter() - started,
        "model_statistics": statistics,
        "best_objective_bound": solver.best_objective_bound,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        cells = tuple(
            cell
            for cell, variable in variables.items()
            if solver.value(variable)
        )
        result.update(
            {
                "changed_cells_from_reference": solver.value(changes),
                "reference_overlap": args.m - solver.value(changes),
                "cells": cells,
                "verification": verify(cells, args.m),
            }
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
