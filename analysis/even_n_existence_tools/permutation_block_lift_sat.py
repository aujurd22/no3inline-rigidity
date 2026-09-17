"""Lift a saturated NTIL set by adaptive permutation blocks.

For a scale k, replace every selected base point (x,y) by a k-point
permutation matrix inside its k-by-k block:

    {(kx+r, ky+pi(r)): r=0,...,k-1}.

Because the base set has two points in every row and column, any independent
choice of micro-permutation preserves exactly two points in every output row
and column.  CP-SAT chooses one internally NTIL permutation per base point and
enforces every ordinary output-line capacity.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_c4_fundamental_cycles import decode_first
from nearest_c4_solution_sat import long_grid_lines
from three_hyperbola_cover_sat import verify


Point = tuple[int, int]


def canonical_line(first: Point, second: Point) -> tuple[int, int, int]:
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


def is_ntil_permutation(permutation: tuple[int, ...]) -> bool:
    points = [(row, column) for row, column in enumerate(permutation)]
    seen: dict[tuple[int, int, int], int] = {}
    for i, first in enumerate(points):
        for second in points[:i]:
            line = canonical_line(first, second)
            seen[line] = seen.get(line, 1) + 1
            if seen[line] >= 3:
                return False
    return True


def solve_block_lift(
    base_points: list[Point],
    n: int,
    scale: int,
    time_limit: float,
    workers: int,
    seed: int,
) -> dict:
    if len(set(base_points)) != 2 * n:
        raise ValueError(f"expected {2*n} distinct base points")
    micro_permutations = [
        permutation
        for permutation in itertools.permutations(range(scale))
        if is_ntil_permutation(permutation)
    ]
    output_n = scale * n
    model = cp_model.CpModel()
    choices: list[list[cp_model.IntVar]] = []
    for block_id, (x, y) in enumerate(base_points):
        block_choices = [
            model.new_bool_var(f"z_{block_id}_{x}_{y}_{permutation_id}")
            for permutation_id in range(len(micro_permutations))
        ]
        model.add_exactly_one(block_choices)
        choices.append(block_choices)

    cell_terms: dict[Point, list[cp_model.IntVar]] = {}
    for block_id, (x, y) in enumerate(base_points):
        for permutation_id, permutation in enumerate(micro_permutations):
            variable = choices[block_id][permutation_id]
            for row_offset, column_offset in enumerate(permutation):
                cell = (
                    scale * x + row_offset,
                    scale * y + column_offset,
                )
                cell_terms.setdefault(cell, []).append(variable)

    started = time.perf_counter()
    lines, line_statistics = long_grid_lines(output_n)
    constrained_lines = 0
    for line in lines:
        terms = [
            variable
            for cell in line
            for variable in cell_terms.get(cell, ())
        ]
        if len(terms) >= 3:
            model.add(sum(terms) <= 2)
            constrained_lines += 1
    build_seconds = time.perf_counter() - started

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    status = solver.solve(model)
    result = {
        "base_n": n,
        "scale": scale,
        "output_n": output_n,
        "base_point_count": len(base_points),
        "micro_permutation_count": len(micro_permutations),
        "binary_variables": sum(map(len, choices)),
        "line_statistics": line_statistics,
        "constrained_lines": constrained_lines,
        "build_seconds": build_seconds,
        "status": solver.status_name(status),
        "solve_seconds": solver.wall_time,
        "conflicts": solver.num_conflicts,
        "branches": solver.num_branches,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected: set[Point] = set()
        selected_permutation_ids = []
        for block_id, (x, y) in enumerate(base_points):
            permutation_id = next(
                index
                for index, variable in enumerate(choices[block_id])
                if solver.value(variable)
            )
            selected_permutation_ids.append(permutation_id)
            permutation = micro_permutations[permutation_id]
            selected.update(
                (
                    scale * x + row_offset,
                    scale * y + column_offset,
                )
                for row_offset, column_offset in enumerate(permutation)
            )
        result["micro_permutations"] = micro_permutations
        result["selected_permutation_ids"] = selected_permutation_ids
        result["selected_points"] = sorted(selected)
        result["verification"] = verify(selected, output_n)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--scale", type=int, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--compact")
    source.add_argument("--points-json")
    parser.add_argument("--time-limit", type=float, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.compact:
        base_points = decode_first(Path(args.compact), args.n)
    else:
        payload = json.loads(Path(args.points_json).read_text())
        raw_points = payload.get("selected_points", payload)
        base_points = [tuple(map(int, point)) for point in raw_points]
    result = solve_block_lift(
        base_points,
        args.n,
        args.scale,
        args.time_limit,
        args.workers,
        args.seed,
    )
    print(json.dumps(result), flush=True)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
