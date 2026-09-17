"""Find the nearest saturated configuration preserving short-scale NTIL.

Starting from a known exact NTIL solution S, solve for a different 2n-point
row/column-saturated configuration S' having at most two points on every line
whose primitive direction scale is < Q.  Maximizing |S intersect S'| gives the
smallest possible macro switch that cannot reopen any already-closed short
direction.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_large_prime_carries import decode_solution, locate
from analyze_c4_fundamental_cycles import decode_record


Point = tuple[int, int]


def directions_below(q: int) -> list[tuple[int, int]]:
    result = []
    for first in range(1, q):
        for second in range(-(q - 1), q):
            if max(abs(first), abs(second)) >= q:
                continue
            if second == 0:
                continue
            if math.gcd(first, abs(second)) != 1:
                continue
            result.append((first, second))
    return result


def line_groups(n: int, direction: tuple[int, int]) -> list[list[Point]]:
    first, second = direction
    groups: dict[int, list[Point]] = {}
    for x in range(n):
        for y in range(n):
            intercept = second * x - first * y
            groups.setdefault(intercept, []).append((x, y))
    return [cells for cells in groups.values() if len(cells) >= 3]


def determinant(first: Point, second: Point, third: Point) -> int:
    return (second[0] - first[0]) * (third[1] - first[1]) - (
        third[0] - first[0]
    ) * (second[1] - first[1])


def primitive_scale(first: Point, second: Point) -> int:
    dx = abs(second[0] - first[0])
    dy = abs(second[1] - first[1])
    divisor = math.gcd(dx, dy)
    return max(dx // divisor, dy // divisor)


def verify(points: list[Point], n: int, q: int) -> dict:
    rows = [sum(x == row for x, _ in points) for row in range(n)]
    columns = [sum(y == column for _, y in points) for column in range(n)]
    short_conflicts = []
    for triple in itertools.combinations(points, 3):
        if determinant(*triple) != 0:
            continue
        scale = primitive_scale(triple[0], triple[1])
        if scale < q:
            short_conflicts.append([list(point) for point in triple])
    return {
        "distinct": len(set(points)) == 2 * n,
        "rows_saturated": rows == [2] * n,
        "columns_saturated": columns == [2] * n,
        "short_conflict_count": len(short_conflicts),
        "valid": (
            len(set(points)) == 2 * n
            and rows == [2] * n
            and columns == [2] * n
            and not short_conflicts
        ),
    }


def solve(
    original: list[Point],
    n: int,
    q: int,
    removed_count: int | None,
    hint_points: list[Point] | None,
    time_limit: float,
    workers: int,
) -> dict:
    original_set = set(original)
    model = cp_model.CpModel()
    selected = {
        (x, y): model.new_bool_var(f"z_{x}_{y}")
        for x in range(n)
        for y in range(n)
    }

    for row in range(n):
        model.add(sum(selected[row, y] for y in range(n)) == 2)
    for column in range(n):
        model.add(sum(selected[x, column] for x in range(n)) == 2)

    selected_directions = directions_below(q)
    line_count = 0
    for direction in selected_directions:
        for cells in line_groups(n, direction):
            model.add(sum(selected[cell] for cell in cells) <= 2)
            line_count += 1

    overlap = sum(selected[point] for point in original_set)
    if removed_count is None:
        model.add(overlap <= 2 * n - 1)
        model.maximize(overlap)
    else:
        model.add(overlap == 2 * n - removed_count)
    hint_set = set(hint_points) if hint_points is not None else original_set
    for cell, variable in selected.items():
        model.add_hint(variable, int(cell in hint_set))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.log_search_progress = False
    status = solver.solve(model)
    status_name = solver.status_name(status)
    result = {
        "n": n,
        "q": q,
        "meaning": "all primitive direction scales below q are protected",
        "direction_count": len(selected_directions),
        "line_constraint_count": line_count,
        "required_removed_count": removed_count,
        "hint_overlap": len(original_set & hint_set),
        "status": status_name,
        "wall_time_seconds": solver.wall_time,
        "best_overlap_bound": solver.best_objective_bound,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        points = [
            list(cell) for cell, variable in selected.items() if solver.value(variable)
        ]
        overlap_value = sum(tuple(point) in original_set for point in points)
        result.update(
            {
                "overlap": overlap_value,
                "symmetric_difference": 4 * n - 2 * overlap_value,
                "points": points,
                "verification": verify([tuple(point) for point in points], n, q),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--q", type=int, required=True)
    parser.add_argument(
        "--removed-count",
        type=int,
        help="solve exact feasibility with this many old points removed",
    )
    parser.add_argument("--time-limit", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--cache-neighbor-hint",
        action="store_true",
        help="hint with the cached record having maximum overlap with the first",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    path = locate(args.cache, args.n)
    original = decode_solution(path, args.n)
    hint_points = None
    if args.cache_neighbor_hint:
        original_set = set(original)
        best_overlap = -1
        for line in (text.strip() for text in path.read_text().splitlines() if text.strip()):
            candidate = decode_record(line, args.n, coordinate_format=" " in line)
            candidate_set = set(candidate)
            if candidate_set == original_set:
                continue
            overlap = len(original_set & candidate_set)
            if overlap > best_overlap:
                best_overlap = overlap
                hint_points = candidate
    result = solve(
        original,
        args.n,
        args.q,
        args.removed_count,
        hint_points,
        args.time_limit,
        args.workers,
    )
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
