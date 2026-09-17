"""Extract a small line-constraint UNSAT core for hyperbola completion.

Rows and columns must each contain exactly one added point.  Every ordinary
grid line has residual capacity 2 minus its load in the fixed modular
hyperbola.  Each line capacity is guarded by an assumption literal so
CP-SAT can return a sufficient infeasibility core.  A deletion pass then
shrinks that core while preserving exact UNSAT.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from typing import Iterable

from ortools.sat.python import cp_model


Point = tuple[int, int]


def hyperbola_layer(p: int, multiplier: int) -> set[Point]:
    return {
        (x - 1, multiplier * pow(x, -1, p) % p - 1)
        for x in range(1, p)
    }


def long_grid_lines(n: int) -> list[tuple[Point, ...]]:
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
    return lines


def line_record(line_id: int, line: tuple[Point, ...], fixed: set[Point]) -> dict:
    dx = line[1][0] - line[0][0]
    dy = line[1][1] - line[0][1]
    fixed_points = [point for point in line if point in fixed]
    candidate_points = [point for point in line if point not in fixed]
    return {
        "id": line_id,
        "direction": [dx, dy],
        "points": [list(point) for point in line],
        "fixed_points": [list(point) for point in fixed_points],
        "candidate_points": [list(point) for point in candidate_points],
        "fixed_load": len(fixed_points),
        "residual_capacity": 2 - len(fixed_points),
    }


def build_model(
    p: int,
    multiplier: int,
    records: list[dict],
    active_ids: set[int] | None,
    guarded: bool,
) -> tuple[cp_model.CpModel, dict[int, int]]:
    n = p - 1
    fixed = hyperbola_layer(p, multiplier)
    model = cp_model.CpModel()
    variables = {
        (row, column): model.new_bool_var(f"z_{row}_{column}")
        for row in range(n)
        for column in range(n)
        if (row, column) not in fixed
    }
    for row in range(n):
        model.add(
            sum(
                variable
                for (candidate_row, _), variable in variables.items()
                if candidate_row == row
            )
            == 1
        )
    for column in range(n):
        model.add(
            sum(
                variable
                for (_, candidate_column), variable in variables.items()
                if candidate_column == column
            )
            == 1
        )
    assumption_index_to_line: dict[int, int] = {}
    for record in records:
        line_id = record["id"]
        if active_ids is not None and line_id not in active_ids:
            continue
        terms = [
            variables[tuple(point)]
            for point in record["candidate_points"]
            if tuple(point) in variables
        ]
        capacity = record["residual_capacity"]
        if not terms or capacity >= len(terms):
            continue
        constraint = model.add(sum(terms) <= capacity)
        if guarded:
            assumption = model.new_bool_var(f"a_{line_id}")
            constraint.only_enforce_if(assumption)
            model.add_assumption(assumption)
            assumption_index_to_line[assumption.index] = line_id
    return model, assumption_index_to_line


def solve_status(
    model: cp_model.CpModel, time_limit: float, workers: int
) -> tuple[cp_model.CpSolver, int]:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.cp_model_presolve = True
    status = solver.solve(model)
    return solver, status


def extract_core(
    p: int,
    multiplier: int,
    time_limit: float,
    workers: int,
    minimize: bool,
) -> dict:
    fixed = hyperbola_layer(p, multiplier)
    records = [
        line_record(line_id, line, fixed)
        for line_id, line in enumerate(long_grid_lines(p - 1))
    ]
    started = time.perf_counter()
    model, index_map = build_model(
        p, multiplier, records, active_ids=None, guarded=True
    )
    solver, status = solve_status(model, time_limit, workers)
    result = {
        "p": p,
        "n": p - 1,
        "multiplier": multiplier,
        "status": solver.status_name(status),
        "all_line_constraint_count": len(index_map),
        "initial_solve_seconds": solver.wall_time,
    }
    if status != cp_model.INFEASIBLE:
        result["elapsed_seconds"] = time.perf_counter() - started
        return result

    raw_literals = solver.sufficient_assumptions_for_infeasibility()
    initial_core_ids = {
        index_map[literal if literal >= 0 else -literal - 1]
        for literal in raw_literals
    }
    result["initial_core_size"] = len(initial_core_ids)
    active = set(initial_core_ids)
    deletion_checks = 0
    if minimize:
        for line_id in sorted(initial_core_ids):
            trial = active - {line_id}
            trial_model, _ = build_model(
                p, multiplier, records, active_ids=trial, guarded=False
            )
            trial_solver, trial_status = solve_status(
                trial_model, time_limit, workers
            )
            deletion_checks += 1
            if trial_status == cp_model.INFEASIBLE:
                active = trial
            elif trial_status != cp_model.OPTIMAL:
                raise RuntimeError(
                    f"core minimization inconclusive for line {line_id}: "
                    f"{trial_solver.status_name(trial_status)}"
                )
    verification_model, _ = build_model(
        p, multiplier, records, active_ids=active, guarded=False
    )
    verification_solver, verification_status = solve_status(
        verification_model, time_limit, workers
    )
    result.update(
        deletion_checks=deletion_checks,
        minimized_core_size=len(active),
        minimized_core_status=verification_solver.status_name(
            verification_status
        ),
        core_lines=[records[line_id] for line_id in sorted(active)],
        elapsed_seconds=time.perf_counter() - started,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--multipliers", type=int, nargs="+")
    parser.add_argument("--time-limit", type=float, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-minimize", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    multipliers: Iterable[int] = args.multipliers or range(1, args.p)
    results = []
    for multiplier in multipliers:
        result = extract_core(
            args.p,
            multiplier % args.p,
            args.time_limit,
            args.workers,
            not args.no_minimize,
        )
        results.append(result)
        print(
            json.dumps(
                {
                    key: result.get(key)
                    for key in (
                        "p",
                        "multiplier",
                        "status",
                        "all_line_constraint_count",
                        "initial_core_size",
                        "minimized_core_size",
                        "minimized_core_status",
                        "elapsed_seconds",
                    )
                }
            ),
            flush=True,
        )
    if args.output:
        with open(args.output, "w") as stream:
            json.dump(results, stream, indent=2)


if __name__ == "__main__":
    main()
