"""Solve the corrected rot4 multigraph factor for one fixed deletion mask."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import SOURCE_OUTPUTS
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import (
    build_general_model,
    short_direction_lines,
)
from solve_joint_rot4_line_cuts import add_line_capacity, extract_solution


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--removed", required=True)
    parser.add_argument("--direction-q", type=int, default=0)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    removed_indices = sorted(
        {int(value) for value in args.removed.split(",") if value}
    )

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
        len(removed_indices),
        None,
        None,
        None,
        None,
        None,
        None,
        True,
        False,
    )
    removed_set = set(removed_indices)
    for index, variable in enumerate(problem["removed"]):
        problem["model"].Add(variable == (index in removed_set))
    lines = short_direction_lines(args.direction_q)
    for key in lines:
        add_line_capacity(problem, key)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = 2026071915
    started = time.time()
    status = solver.Solve(problem["model"])
    payload = {
        "parameters": vars(args),
        "removed_indices": removed_indices,
        "status": solver.StatusName(status),
        "short_line_count": len(lines),
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "wall_s": round(solver.WallTime(), 3),
        "elapsed_s": round(time.time() - started, 3),
    }
    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        solution = extract_solution(problem, solver)
        payload["solution"] = solution
        payload["topology"] = {
            "orientation_flip_count": sum(
                solver.Value(value)
                for value in problem["flipped_reselection_terms"]
            ),
            "selected_antiparallel_pairs": sum(
                solver.Value(value)
                for value in problem["antiparallel_pair_terms"]
            ),
            "reverse_along_retained_old": sum(
                solver.Value(reverse)
                * (1 - solver.Value(problem["removed"][index]))
                for index, reverse in enumerate(
                    problem["reverse_parallel_by_old_index"]
                )
            ),
        }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "wall_s": payload["wall_s"],
                "bad_lines": (
                    payload.get("solution", {}).get("bad_line_count")
                ),
                "topology": payload.get("topology"),
            },
            indent=2,
        )
    )
    print(output)


if __name__ == "__main__":
    main()
