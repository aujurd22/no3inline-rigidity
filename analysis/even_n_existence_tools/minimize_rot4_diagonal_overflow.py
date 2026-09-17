"""Minimize total short-direction line overflow in a deletion-shape layer."""

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
    canonical_line_orbit,
    short_direction_lines,
)
from solve_joint_rot4_line_cuts import extract_solution


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="v40_01")
    parser.add_argument("--size", type=int, default=11)
    parser.add_argument("--adjacency-count", type=int, required=True)
    parser.add_argument(
        "--triple-count",
        type=int,
        default=None,
        help="optional number of three-consecutive deletion windows",
    )
    parser.add_argument(
        "--loop-count",
        type=int,
        default=None,
        help="optional number of replacement loops",
    )
    parser.add_argument("--reselected-count", type=int, default=None)
    parser.add_argument("--deficit-two-edge-count", type=int, default=None)
    parser.add_argument("--quadruple-count", type=int, default=None)
    parser.add_argument(
        "--forbid-exact-reselection",
        action="store_true",
        help="Normalize Hamming distance by forbidding delete-then-identical-reinsert.",
    )
    parser.add_argument(
        "--direction-q",
        type=int,
        default=1,
        help="primitive line-normal coordinate bound (1 means diagonals only)",
    )
    parser.add_argument(
        "--hard-direction-q",
        type=int,
        default=0,
        help="hard-enforce all line capacities through this smaller bound",
    )
    parser.add_argument(
        "--objective-line",
        action="append",
        default=[],
        help="optional explicit objective line a,b,c; may be repeated",
    )
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", default="rot4_diagonal_overflow.json")
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
    blockers = candidate_blockers(base)
    problem = build_general_model(
        base,
        hitting["defect_owner_sets"],
        blockers,
        args.size,
        args.adjacency_count,
        args.triple_count,
        args.loop_count,
        args.reselected_count,
        args.deficit_two_edge_count,
        args.quadruple_count,
        args.forbid_exact_reselection,
    )
    model = problem["model"]
    if not 0 <= args.hard_direction_q < args.direction_q:
        parser.error("--hard-direction-q must satisfy 0 <= hard q < direction q")
    overflow_vars = []
    line_records = []
    hard_lines = set(short_direction_lines(args.hard_direction_q))
    explicit_lines = {
        canonical_line_orbit(
            tuple(int(value) for value in raw_key.split(","))
        )
        for raw_key in args.objective_line
    }
    if explicit_lines:
        short_lines = sorted(hard_lines | explicit_lines)
    else:
        short_lines = short_direction_lines(args.direction_q)
    for line_no, key in enumerate(short_lines):
        a, b, c = key
        old_counts = [
            sum(a * x + b * y == c for x, y in orbit)
            for orbit in problem["base_orbits"]
        ]
        new_counts = {
            cell: sum(a * x + b * y == c for x, y in orbit)
            for cell, orbit in problem["candidate_orbits"].items()
        }
        occupancy = (
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
        if key in hard_lines:
            model.Add(occupancy <= 2)
        else:
            overflow = model.NewIntVar(0, 2 * M, f"line_overflow_{line_no}")
            model.Add(overflow >= occupancy - 2)
            overflow_vars.append(overflow)
            line_records.append(key)
    total_overflow = sum(overflow_vars)
    model.Minimize(total_overflow)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = 2026071905
    started = time.time()
    status = solver.Solve(model)
    payload = {
        "parameters": vars(args),
        "status": solver.StatusName(status),
        "objective": (
            round(solver.ObjectiveValue())
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            else None
        ),
        "best_bound": solver.BestObjectiveBound(),
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "wall_s": round(solver.WallTime(), 3),
        "elapsed_s": round(time.time() - started, 3),
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        solution = extract_solution(problem, solver)
        active_overflows = [
            {
                "line": list(key),
                "overflow": solver.Value(variable),
            }
            for key, variable in zip(line_records, overflow_vars)
            if solver.Value(variable)
        ]
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
        payload["short_line_count"] = len(short_lines)
        payload["hard_line_count"] = len(hard_lines)
        payload["objective_line_keys"] = [
            list(key) for key in sorted(explicit_lines)
        ]
        payload["active_short_line_overflows"] = active_overflows
        assert sum(item["overflow"] for item in active_overflows) == round(
            solver.ObjectiveValue()
        )
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("status", "objective", "best_bound", "wall_s")}, indent=2))
    print(output)


if __name__ == "__main__":
    main()
