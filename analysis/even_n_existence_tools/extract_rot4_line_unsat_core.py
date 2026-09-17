"""Extract an assumption UNSAT core of short-line capacities."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import M, SOURCE_OUTPUTS, c4_lifts
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import (
    build_general_model,
    short_direction_lines,
)


HERE = Path(__file__).resolve().parent


def occupancy_expression(problem: dict, key: tuple[int, int, int]):
    a, b, c = key
    old_counts = [
        sum(a * x + b * y == c for x, y in orbit)
        for orbit in problem["base_orbits"]
    ]
    new_counts = {
        cell: sum(a * x + b * y == c for x, y in orbit)
        for cell, orbit in problem["candidate_orbits"].items()
    }
    return (
        sum(old_counts)
        - sum(
            count * problem["removed"][i]
            for i, count in enumerate(old_counts)
            if count
        )
        + sum(
            count * problem["cell_variable"][cell]
            for cell, count in new_counts.items()
            if count
        )
    )


def solve(model: cp_model.CpModel, seconds: float, workers: int):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = 2026071906
    status = solver.Solve(model)
    return solver, status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, default=11)
    parser.add_argument("--adjacency-count", type=int, required=True)
    parser.add_argument("--triple-count", type=int, default=None)
    parser.add_argument("--quadruple-count", type=int, default=None)
    parser.add_argument("--hard-q", type=int, required=True)
    parser.add_argument("--full-q", type=int, required=True)
    parser.add_argument("--time-limit", type=float, default=1200.0)
    parser.add_argument("--validation-time", type=float, default=1200.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not 0 <= args.hard_q < args.full_q:
        parser.error("require 0 <= hard-q < full-q")

    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    hitting = json.loads(
        (SOURCE_OUTPUTS / f"defect_hitting_{args.base}.json").read_text(
            encoding="utf-8"
        )
    )
    problem = build_general_model(
        base,
        hitting["defect_owner_sets"],
        candidate_blockers(base),
        args.size,
        args.adjacency_count,
        args.triple_count,
        None,
        None,
        None,
        args.quadruple_count,
    )
    model = problem["model"]
    hard_lines = set(short_direction_lines(args.hard_q))
    full_lines = set(short_direction_lines(args.full_q))
    new_lines = sorted(full_lines - hard_lines)
    for key in sorted(hard_lines):
        model.Add(occupancy_expression(problem, key) <= 2)

    assumption_by_index = {}
    for line_no, key in enumerate(new_lines):
        literal = model.NewBoolVar(f"assume_line_{line_no}")
        model.Add(occupancy_expression(problem, key) <= 2).OnlyEnforceIf(literal)
        model.AddAssumption(literal)
        assumption_by_index[literal.Index()] = (literal, key)

    started = time.time()
    solver, status = solve(model, args.time_limit, args.workers)
    payload = {
        "parameters": vars(args),
        "status": solver.StatusName(status),
        "hard_line_count": len(hard_lines),
        "new_line_count": len(new_lines),
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "wall_s": round(solver.WallTime(), 3),
        "elapsed_s": round(time.time() - started, 3),
    }
    if status == cp_model.INFEASIBLE:
        core_indices = list(solver.SufficientAssumptionsForInfeasibility())
        core_pairs = [assumption_by_index[index] for index in core_indices]
        payload["core_line_count"] = len(core_pairs)
        payload["core_line_keys"] = [list(key) for _, key in core_pairs]

        model.ClearAssumptions()
        model.AddAssumptions([literal for literal, _ in core_pairs])
        validation_solver, validation_status = solve(
            model, args.validation_time, args.workers
        )
        payload["core_validation"] = {
            "status": validation_solver.StatusName(validation_status),
            "branches": validation_solver.NumBranches(),
            "conflicts": validation_solver.NumConflicts(),
            "wall_s": round(validation_solver.WallTime(), 3),
        }
        assert validation_status == cp_model.INFEASIBLE
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in ("status", "core_line_count", "wall_s")
            },
            indent=2,
        )
    )
    print(output)


if __name__ == "__main__":
    main()
