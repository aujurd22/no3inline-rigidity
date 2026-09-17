"""Test the diagonal 2-lift of a saturated NTIL configuration.

Each base point (x,y) is replaced by one of the two perfect matchings of its
2-by-2 block:

  type 0: (2x,2y), (2x+1,2y+1)
  type 1: (2x,2y+1), (2x+1,2y).

Either choice preserves two points in every output row and column.  The only
variables are the 2n binary block types; ordinary line capacities are linear
in those variables.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_c4_fundamental_cycles import decode_first
from nearest_c4_solution_sat import long_grid_lines
from three_hyperbola_cover_sat import verify


Point = tuple[int, int]


def solve_two_lift(
    base_points: list[Point],
    n: int,
    time_limit: float,
    workers: int,
    seed: int,
) -> dict:
    if len(set(base_points)) != 2 * n:
        raise ValueError(f"expected {2*n} distinct base points")
    output_n = 2 * n
    model = cp_model.CpModel()
    block_type = [
        model.new_bool_var(f"b_{index}_{x}_{y}")
        for index, (x, y) in enumerate(base_points)
    ]
    cell_expression: dict[Point, cp_model.LinearExpr] = {}
    for index, (x, y) in enumerate(base_points):
        variable = block_type[index]
        cell_expression[(2 * x, 2 * y)] = 1 - variable
        cell_expression[(2 * x + 1, 2 * y + 1)] = 1 - variable
        cell_expression[(2 * x, 2 * y + 1)] = variable
        cell_expression[(2 * x + 1, 2 * y)] = variable

    started = time.perf_counter()
    lines, line_statistics = long_grid_lines(output_n)
    constrained_lines = 0
    for line in lines:
        terms = [cell_expression[cell] for cell in line if cell in cell_expression]
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
        "output_n": output_n,
        "base_point_count": len(base_points),
        "binary_variables": len(block_type),
        "line_statistics": line_statistics,
        "constrained_lines": constrained_lines,
        "build_seconds": build_seconds,
        "status": solver.status_name(status),
        "solve_seconds": solver.wall_time,
        "conflicts": solver.num_conflicts,
        "branches": solver.num_branches,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        labels = [solver.value(variable) for variable in block_type]
        selected: set[Point] = set()
        for label, (x, y) in zip(labels, base_points):
            if label == 0:
                selected.update(((2 * x, 2 * y), (2 * x + 1, 2 * y + 1)))
            else:
                selected.update(((2 * x, 2 * y + 1), (2 * x + 1, 2 * y)))
        result["labels"] = labels
        result["selected_points"] = sorted(selected)
        result["verification"] = verify(selected, output_n)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
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
    result = solve_two_lift(
        base_points, args.n, args.time_limit, args.workers, args.seed
    )
    print(json.dumps(result), flush=True)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
