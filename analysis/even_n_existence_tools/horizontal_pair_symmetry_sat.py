"""Exact NTIL model with horizontal-pair symmetry.

Each row r chooses one complementary column pair {j,n-1-j}.  Since every
column must contain two points, each of the n/2 column pairs must be used by
exactly two rows.  Binary variables x[r,j] therefore satisfy

    sum_j x[r,j] = 1,     sum_r x[r,j] = 2.

Selecting x[r,j] places both (r,j) and (r,n-1-j).  Maximal-line constraints
make the formulation exact.
"""

from __future__ import annotations

import argparse
import collections
import json
import time

from ortools.sat.python import cp_model

from nearest_c4_solution_sat import long_grid_lines


def solve(
    n: int,
    time_limit: float,
    workers: int,
    max_direction_coordinate: int | None,
) -> dict:
    if n % 2:
        raise ValueError("n must be even")
    m = n // 2
    started = time.perf_counter()
    lines, line_stats = long_grid_lines(n)
    model = cp_model.CpModel()
    variables = {
        (row, pair): model.new_bool_var(f"x_{row}_{pair}")
        for row in range(n)
        for pair in range(m)
    }
    for row in range(n):
        model.add(sum(variables[row, pair] for pair in range(m)) == 1)
    for pair in range(m):
        model.add(sum(variables[row, pair] for row in range(n)) == 2)

    seen = set()
    coefficient_histogram: collections.Counter[int] = collections.Counter()
    included_directions: set[tuple[int, int]] = set()
    for line in lines:
        dx = line[1][0] - line[0][0]
        dy = line[1][1] - line[0][1]
        if (
            max_direction_coordinate is not None
            and max(abs(dx), abs(dy)) > max_direction_coordinate
        ):
            continue
        included_directions.add((dx, dy))
        counts: collections.Counter[tuple[int, int]] = collections.Counter()
        for row, column in line:
            pair = min(column, n - 1 - column)
            counts[row, pair] += 1
        signature = tuple(sorted(counts.items()))
        if signature in seen:
            continue
        seen.add(signature)
        model.add(
            sum(
                coefficient * variables[cell]
                for cell, coefficient in counts.items()
            )
            <= 2
        )
        coefficient_histogram.update(counts.values())

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    status = solver.solve(model)
    record = {
        "n": n,
        "status": solver.status_name(status),
        "wall_seconds": solver.wall_time,
        "total_seconds": time.perf_counter() - started,
        "variables": len(variables),
        "unique_line_constraints": len(seen),
        "included_directions": sorted(included_directions),
        "max_direction_coordinate": max_direction_coordinate,
        "coefficient_histogram": dict(coefficient_histogram),
        "line_statistics": line_stats,
        "conflicts": solver.num_conflicts,
        "branches": solver.num_branches,
        "best_objective_bound": solver.best_objective_bound,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        assignment = [
            next(
                pair
                for pair in range(m)
                if solver.value(variables[row, pair])
            )
            for row in range(n)
        ]
        points = [
            point
            for row, pair in enumerate(assignment)
            for point in ((row, pair), (row, n - 1 - pair))
        ]
        record["assignment"] = assignment
        record["points"] = points
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, nargs="+", required=True)
    parser.add_argument("--time-limit", type=float, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-direction-coordinate", type=int)
    parser.add_argument("--output")
    args = parser.parse_args()
    records = []
    for n in args.n:
        record = solve(
            n,
            args.time_limit,
            args.workers,
            args.max_direction_coordinate,
        )
        records.append(record)
        print(json.dumps(record), flush=True)
    if args.output:
        with open(args.output, "w") as stream:
            json.dump(records, stream, indent=2)


if __name__ == "__main__":
    main()
