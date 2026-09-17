"""Complete one modular hyperbola layer by an arbitrary permutation.

For p prime and n=p-1, fix

    H_a = {(x-1, a/x mod p - 1): x in F_p^*}.

This n-point set is NTIL because it lies on a nondegenerate finite-field
conic.  Select one further point in every row and column, outside H_a, while
keeping every integer grid line at load at most two.
"""

from __future__ import annotations

import argparse
import json
import time

from ortools.sat.python import cp_model

from nearest_c4_solution_sat import long_grid_lines
from three_hyperbola_cover_sat import verify


Point = tuple[int, int]


def hyperbola_layer(p: int, multiplier: int) -> set[Point]:
    return {
        (x - 1, multiplier * pow(x, -1, p) % p - 1)
        for x in range(1, p)
    }


def solve(
    p: int,
    multiplier: int,
    time_limit: float,
    workers: int,
    seed: int,
) -> dict:
    n = p - 1
    fixed = hyperbola_layer(p, multiplier)
    candidates = {
        (x, y)
        for x in range(n)
        for y in range(n)
        if (x, y) not in fixed
    }
    model = cp_model.CpModel()
    variables = {
        point: model.new_bool_var(f"z_{point[0]}_{point[1]}")
        for point in candidates
    }
    for row in range(n):
        model.add(
            sum(variable for (x, _), variable in variables.items() if x == row)
            == 1
        )
    for column in range(n):
        model.add(
            sum(variable for (_, y), variable in variables.items() if y == column)
            == 1
        )

    started = time.perf_counter()
    lines, line_statistics = long_grid_lines(n)
    constrained_lines = 0
    fixed_two_lines = 0
    for line in lines:
        fixed_load = sum(point in fixed for point in line)
        terms = [variables[point] for point in line if point in variables]
        if not terms:
            continue
        model.add(sum(terms) <= 2 - fixed_load)
        constrained_lines += 1
        fixed_two_lines += fixed_load == 2
    build_seconds = time.perf_counter() - started

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    status = solver.solve(model)
    result = {
        "p": p,
        "n": n,
        "multiplier": multiplier,
        "status": solver.status_name(status),
        "candidate_cells": len(candidates),
        "line_statistics": line_statistics,
        "constrained_lines": constrained_lines,
        "fixed_secant_lines": fixed_two_lines,
        "build_seconds": build_seconds,
        "solve_seconds": solver.wall_time,
        "conflicts": solver.num_conflicts,
        "branches": solver.num_branches,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        added = {
            point for point, variable in variables.items() if solver.value(variable)
        }
        selected = fixed | added
        result["added_points"] = sorted(added)
        result["selected_points"] = sorted(selected)
        result["verification"] = verify(selected, n)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--multipliers", type=int, nargs="+")
    parser.add_argument("--time-limit", type=float, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output")
    args = parser.parse_args()
    multipliers = args.multipliers or list(range(1, args.p))
    records = []
    for index, multiplier in enumerate(multipliers):
        result = solve(
            args.p,
            multiplier % args.p,
            args.time_limit,
            args.workers,
            args.seed + index,
        )
        records.append(result)
        print(json.dumps(result), flush=True)
    if args.output:
        with open(args.output, "w") as stream:
            json.dump(records, stream, indent=2)


if __name__ == "__main__":
    main()
