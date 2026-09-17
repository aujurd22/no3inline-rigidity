"""Decide the normalized q=1 two-resource f-factor model.

This is exactly the hard diagonal-capacity layer, expressed with the closed
form resources from ``verify_rot4_q1_resource_model.py`` rather than geometric
line enumeration or an overflow objective.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import N, SOURCE_OUTPUTS
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import build_general_model
from solve_joint_rot4_line_cuts import extract_solution
from verify_rot4_q1_resource_model import formula_resources


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--adjacency-count", type=int, default=None)
    parser.add_argument("--adjacency-min", type=int, default=None)
    parser.add_argument("--adjacency-max", type=int, default=None)
    parser.add_argument("--triple-count", type=int, default=None)
    parser.add_argument("--quadruple-count", type=int, default=None)
    parser.add_argument("--loop-count", type=int, default=None)
    parser.add_argument("--allow-exact-reselection", action="store_true")
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

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
        args.loop_count,
        None,
        None,
        args.quadruple_count,
        not args.allow_exact_reselection,
    )
    model = problem["model"]
    if args.adjacency_min is not None:
        model.Add(sum(problem["adjacent_pairs"]) >= args.adjacency_min)
    if args.adjacency_max is not None:
        model.Add(sum(problem["adjacent_pairs"]) <= args.adjacency_max)
    old_resource_counts = [
        formula_resources(cell) for cell in problem["base_cells"]
    ]
    candidate_resource_counts = {
        cell: formula_resources(cell) for cell in problem["cells"]
    }
    for resource in range(N - 2):
        old_total = sum(
            counts[resource] for counts in old_resource_counts
        )
        occupancy = (
            old_total
            - sum(
                counts[resource] * problem["removed"][index]
                for index, counts in enumerate(old_resource_counts)
                if counts[resource]
            )
            + sum(
                counts[resource] * problem["cell_variable"][cell]
                for cell, counts in candidate_resource_counts.items()
                if counts[resource]
            )
        )
        model.Add(occupancy <= 2)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = 2026071907
    started = time.time()
    status = solver.Solve(model)
    payload = {
        "parameters": vars(args),
        "status": solver.StatusName(status),
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "wall_s": round(solver.WallTime(), 3),
        "elapsed_s": round(time.time() - started, 3),
        "resource_count": N - 2,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        solution = extract_solution(problem, solver)
        occupancy = {}
        for index, cell in enumerate(problem["base_cells"]):
            if not solver.Value(problem["removed"][index]):
                occupancy.setdefault("old", []).append(cell)
        selected_cells = [
            cell
            for cell in problem["cells"]
            if solver.Value(problem["cell_variable"][cell])
        ]
        resource_occupancy = {}
        final_cells = [
            cell
            for index, cell in enumerate(problem["base_cells"])
            if not solver.Value(problem["removed"][index])
        ] + selected_cells
        for cell in final_cells:
            for resource, count in formula_resources(cell).items():
                resource_occupancy[resource] = (
                    resource_occupancy.get(resource, 0) + count
                )
        assert max(resource_occupancy.values()) <= 2
        payload["solution"] = solution
        payload["replacement_topology"] = {
            "exact_reselection_count": sum(
                solver.Value(variable)
                for variable in problem["exact_reselection_terms"]
            ),
            "orientation_flip_count": sum(
                solver.Value(variable)
                for variable in problem["flipped_reselection_terms"]
            ),
            "genuine_reconnection_count": (
                args.size
                - sum(
                    solver.Value(variable)
                    for variable in problem["reselected_terms"]
                )
            ),
        }
        payload["resource_occupancy"] = {
            str(key): value for key, value in sorted(resource_occupancy.items())
        }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "branches": payload["branches"],
                "wall_s": payload["wall_s"],
            },
            indent=2,
        )
    )
    print(output)


if __name__ == "__main__":
    main()
