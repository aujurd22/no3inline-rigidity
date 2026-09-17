"""Find minimum balanced switches under successive secant-closure layers.

Let S be a row/column-saturated exact NTIL configuration.  A switch removes a
set R from S and adds an equally row/column-balanced set A of empty cells.

Stage ``old2`` enforces only conflicts consisting of two retained old points
and one new point.  Equivalently, for every z in A, R is a transversal of the
matching of old secants through z.

Stage ``old1`` additionally enforces all conflicts consisting of one retained
old point and two new points.  Any remaining collinear triple in the returned
configuration must then consist of three new points.  Stage ``full`` also
forbids those all-new triples.

The objective is the exact minimum |R| among nontrivial balanced switches.
This separates the cost of secant-transversal closure from the later
new-point compatibility bottleneck.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_c4_fundamental_cycles import decode_record
from analyze_large_prime_carries import decode_solution, determinant, locate
from analyze_switch_scale_safety import primitive_scale, secant_index


Point = tuple[int, int]


def primitive_directions(n: int, q: int) -> list[Point]:
    """Canonical non-axis directions able to support a protected triple."""

    maximum = min(q - 1, (n - 1) // 2)
    result: list[Point] = []
    for dx in range(1, maximum + 1):
        for dy in range(-maximum, maximum + 1):
            if max(dx, abs(dy)) > maximum:
                continue
            if dy == 0:
                continue
            if math.gcd(dx, abs(dy)) != 1:
                continue
            result.append((dx, dy))
    return result


def line_through(point: Point, direction: Point, n: int) -> list[Point]:
    dx, dy = direction
    x, y = point
    while 0 <= x - dx < n and 0 <= y - dy < n:
        x -= dx
        y -= dy
    cells = []
    while 0 <= x < n and 0 <= y < n:
        cells.append((x, y))
        x += dx
        y += dy
    return cells


def maximal_lines(direction: Point, n: int) -> list[list[Point]]:
    """Enumerate every maximal grid line in one canonical direction."""

    dx, dy = direction
    result = []
    for x in range(n):
        for y in range(n):
            if 0 <= x - dx < n and 0 <= y - dy < n:
                continue
            cells = []
            current_x, current_y = x, y
            while 0 <= current_x < n and 0 <= current_y < n:
                cells.append((current_x, current_y))
                current_x += dx
                current_y += dy
            if len(cells) >= 3:
                result.append(cells)
    return result


def verify_candidate(
    original: list[Point],
    removed: list[Point],
    added: list[Point],
    n: int,
    q: int,
) -> dict:
    removed_set = set(removed)
    added_set = set(added)
    final = [point for point in original if point not in removed_set] + added
    rows = collections.Counter(x for x, _ in final)
    columns = collections.Counter(y for _, y in final)
    by_new_count: collections.Counter[int] = collections.Counter()
    protected_by_new_count: collections.Counter[int] = collections.Counter()
    examples = []
    for triple in itertools.combinations(final, 3):
        if determinant(*triple) != 0:
            continue
        new_count = sum(point in added_set for point in triple)
        scale = primitive_scale(triple[0], triple[1])
        by_new_count[new_count] += 1
        if scale < q:
            protected_by_new_count[new_count] += 1
        if len(examples) < 20:
            examples.append(
                {
                    "points": [list(point) for point in triple],
                    "new_point_count": new_count,
                    "primitive_scale": scale,
                }
            )
    return {
        "point_count": len(final),
        "distinct": len(set(final)) == 2 * n,
        "rows_saturated": all(rows[row] == 2 for row in range(n)),
        "columns_saturated": all(columns[column] == 2 for column in range(n)),
        "collinear_triples_by_new_point_count": dict(sorted(by_new_count.items())),
        "protected_collinear_triples_by_new_point_count": dict(
            sorted(protected_by_new_count.items())
        ),
        "collinear_triple_examples": examples,
        "is_exact_ntil": not by_new_count,
    }


def solve(
    original: list[Point],
    n: int,
    q: int,
    stage: str,
    removed_count: int | None,
    force_cell: Point | None,
    old1_encoding: str,
    hint_points: list[Point] | None,
    time_limit: float,
    workers: int,
) -> dict:
    original_set = set(original)
    point_index = {point: index for index, point in enumerate(original)}
    empty = [
        (x, y)
        for x in range(n)
        for y in range(n)
        if (x, y) not in original_set
    ]

    model = cp_model.CpModel()
    removed_variables = [
        model.new_bool_var(f"r_{index}") for index in range(len(original))
    ]
    added_variables = {
        cell: model.new_bool_var(f"a_{cell[0]}_{cell[1]}") for cell in empty
    }

    old_by_row: list[list[int]] = [[] for _ in range(n)]
    old_by_column: list[list[int]] = [[] for _ in range(n)]
    empty_by_row: list[list[Point]] = [[] for _ in range(n)]
    empty_by_column: list[list[Point]] = [[] for _ in range(n)]
    for index, (row, column) in enumerate(original):
        old_by_row[row].append(index)
        old_by_column[column].append(index)
    for cell in empty:
        empty_by_row[cell[0]].append(cell)
        empty_by_column[cell[1]].append(cell)

    for row in range(n):
        model.add(
            sum(added_variables[cell] for cell in empty_by_row[row])
            == sum(removed_variables[index] for index in old_by_row[row])
        )
    for column in range(n):
        model.add(
            sum(added_variables[cell] for cell in empty_by_column[column])
            == sum(removed_variables[index] for index in old_by_column[column])
        )

    total_removed = sum(removed_variables)
    model.add(total_removed >= 1)
    if removed_count is not None:
        model.add(total_removed == removed_count)
    else:
        model.minimize(total_removed)
    if force_cell is not None:
        if force_cell not in added_variables:
            raise ValueError(f"forced cell {force_cell} is not empty")
        model.add(added_variables[force_cell] == 1)

    secants = secant_index(original, n)
    old2_constraint_count = 0
    relevant_secant_incidence_count = 0
    for cell, variable in added_variables.items():
        for first, second, scale in secants.get(cell, ()):
            if scale >= q:
                continue
            model.add(
                variable
                <= removed_variables[first] + removed_variables[second]
            )
            old2_constraint_count += 1
            relevant_secant_incidence_count += 1

    old1_constraint_count = 0
    direction_count = 0
    directions: list[Point] = []
    if stage in ("old1", "full"):
        directions = primitive_directions(n, q)
        direction_count = len(directions)
        for old_index, point in enumerate(original):
            removal = removed_variables[old_index]
            for direction in directions:
                cells = line_through(point, direction, n)
                if len(cells) < 3:
                    continue
                line_empty = [
                    cell for cell in cells if cell in added_variables
                ]
                if len(line_empty) < 2:
                    continue
                if old1_encoding == "bigm":
                    # If this old point remains, at most one new point may be
                    # selected on its line.  If it is removed, the constraint
                    # is inactive.
                    model.add(
                        sum(added_variables[cell] for cell in line_empty)
                        <= 1 + (len(line_empty) - 1) * removal
                    )
                    old1_constraint_count += 1
                else:
                    # The pairwise form is logically equivalent but gives a
                    # substantially stronger relaxation to CP-SAT.
                    for first, second in itertools.combinations(line_empty, 2):
                        model.add(
                            added_variables[first] + added_variables[second]
                            <= 1 + removal
                        )
                        old1_constraint_count += 1

    new3_line_constraint_count = 0
    if stage == "full":
        for direction in directions:
            for cells in maximal_lines(direction, n):
                line_empty = [
                    cell for cell in cells if cell in added_variables
                ]
                if len(line_empty) < 3:
                    continue
                model.add(
                    sum(added_variables[cell] for cell in line_empty) <= 2
                )
                new3_line_constraint_count += 1

    hint_set = set(hint_points) if hint_points is not None else original_set
    for index, variable in enumerate(removed_variables):
        model.add_hint(variable, int(original[index] not in hint_set))
    for cell, variable in added_variables.items():
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
        "meaning": "primitive direction scales strictly below q are protected",
        "stage": stage,
        "required_removed_count": removed_count,
        "forced_added_cell": list(force_cell) if force_cell is not None else None,
        "old_point_count": len(original),
        "empty_cell_count": len(empty),
        "hint_removed_count": len(original_set - hint_set),
        "old2_secant_constraint_count": old2_constraint_count,
        "relevant_secant_incidence_count": relevant_secant_incidence_count,
        "old1_conditional_line_constraint_count": old1_constraint_count,
        "old1_direction_count": direction_count,
        "old1_encoding": old1_encoding,
        "new3_line_constraint_count": new3_line_constraint_count,
        "status": status_name,
        "wall_time_seconds": solver.wall_time,
        "best_removed_count_bound": solver.best_objective_bound,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        removed = [
            original[index]
            for index, variable in enumerate(removed_variables)
            if solver.value(variable)
        ]
        added = [
            cell
            for cell, variable in added_variables.items()
            if solver.value(variable)
        ]
        result.update(
            {
                "removed_count": len(removed),
                "added_count": len(added),
                "symmetric_difference": len(removed) + len(added),
                "removed": [list(point) for point in removed],
                "added": [list(point) for point in added],
                "verification": verify_candidate(
                    original, removed, added, n, q
                ),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--q", type=int)
    parser.add_argument(
        "--stage", choices=("old2", "old1", "full"), default="old2"
    )
    parser.add_argument(
        "--old1-encoding",
        choices=("pairwise", "bigm"),
        default="pairwise",
    )
    parser.add_argument("--removed-count", type=int)
    parser.add_argument("--force-cell", type=int, nargs=2, metavar=("ROW", "COLUMN"))
    parser.add_argument("--time-limit", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--cache-neighbor-hint",
        action="store_true",
        help="hint with the cached exact solution having maximum overlap",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    q = args.q if args.q is not None else args.n
    cache_path = locate(args.cache, args.n)
    original = decode_solution(cache_path, args.n)
    hint_points = None
    if args.cache_neighbor_hint:
        original_set = set(original)
        best_overlap = -1
        for line in (
            text.strip()
            for text in cache_path.read_text().splitlines()
            if text.strip()
        ):
            candidate = decode_record(
                line, args.n, coordinate_format=" " in line
            )
            candidate_set = set(candidate)
            if candidate_set == original_set:
                continue
            overlap = len(original_set & candidate_set)
            if overlap > best_overlap:
                best_overlap = overlap
                hint_points = candidate
    result = solve(
        original=original,
        n=args.n,
        q=q,
        stage=args.stage,
        removed_count=args.removed_count,
        force_cell=tuple(args.force_cell) if args.force_cell else None,
        old1_encoding=args.old1_encoding,
        hint_points=hint_points,
        time_limit=args.time_limit,
        workers=args.workers,
    )
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
