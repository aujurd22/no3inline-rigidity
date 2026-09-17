"""Decide a fixed repair layer after adding selected direction families.

The usual q-shell adds hundreds of line-orbit inequalities at once.  This
script groups them by the C4 orbit of their primitive normal and tests those
resource graphs separately.  A closed singleton or small subset is a much
more interpretable certificate than a monolithic q-shell closure.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
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


def canonical_direction(a: int, b: int) -> tuple[int, int]:
    """Canonical primitive normal under quarter turns and sign changes."""
    values = []
    for _ in range(4):
        divisor = math.gcd(abs(a), abs(b))
        a, b = a // divisor, b // divisor
        if a < 0 or (a == 0 and b < 0):
            a, b = -a, -b
        values.append((a, b))
        a, b = -b, a
    return min(values)


def solve_subset(args, base, hitting, subset, hard_lines, shell_by_direction):
    problem = build_general_model(
        base,
        hitting["defect_owner_sets"],
        candidate_blockers(base),
        args.size,
        args.adjacency_count,
        args.triple_count,
        args.loop_count,
        args.flip_count,
        None,
        args.quadruple_count,
        True,
    )
    if args.flip_min is not None:
        problem["model"].Add(
            sum(problem["flipped_reselection_terms"]) >= args.flip_min
        )
    if args.flip_max is not None:
        problem["model"].Add(
            sum(problem["flipped_reselection_terms"]) <= args.flip_max
        )
    lines = list(hard_lines)
    for direction in subset:
        lines.extend(shell_by_direction[direction])
    for key in lines:
        add_line_capacity(problem, key)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = 2026071911
    started = time.time()
    status = solver.Solve(problem["model"])
    record = {
        "directions": [list(value) for value in subset],
        "line_count": len(lines),
        "new_line_count": len(lines) - len(hard_lines),
        "status": solver.StatusName(status),
        "classification": (
            "CLOSED" if status == cp_model.INFEASIBLE else "SURVIVES"
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            else "UNRESOLVED"
        ),
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "wall_s": round(solver.WallTime(), 3),
        "elapsed_s": round(time.time() - started, 3),
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        record["solution"] = extract_solution(problem, solver)
        record["replacement_topology"] = {
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
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--adjacency-count", type=int, required=True)
    parser.add_argument("--triple-count", type=int, default=None)
    parser.add_argument("--quadruple-count", type=int, default=None)
    parser.add_argument("--loop-count", type=int, default=None)
    parser.add_argument("--flip-count", type=int, default=None)
    parser.add_argument("--flip-min", type=int, default=None)
    parser.add_argument("--flip-max", type=int, default=None)
    parser.add_argument("--hard-q", type=int, required=True)
    parser.add_argument("--shell-q", type=int, required=True)
    parser.add_argument(
        "--subset-size",
        type=int,
        default=1,
        help="test every subset of this many newly appearing directions",
    )
    parser.add_argument(
        "--direction",
        action="append",
        default=[],
        help="test only this explicit canonical direction a,b; may be repeated",
    )
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.shell_q <= args.hard_q:
        parser.error("--shell-q must be greater than --hard-q")

    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    hitting = json.loads(
        (SOURCE_OUTPUTS / f"defect_hitting_{args.base}.json").read_text(
            encoding="utf-8"
        )
    )
    hard_lines = short_direction_lines(args.hard_q)
    shell_lines = sorted(
        set(short_direction_lines(args.shell_q)) - set(hard_lines)
    )
    shell_by_direction = {}
    for key in shell_lines:
        shell_by_direction.setdefault(canonical_direction(key[0], key[1]), []).append(
            key
        )
    directions = sorted(shell_by_direction)
    if not 1 <= args.subset_size <= len(directions):
        parser.error("--subset-size is outside the shell direction count")
    if args.direction:
        selected = tuple(
            sorted(
                tuple(int(value) for value in raw.split(","))
                for raw in args.direction
            )
        )
        if len(selected) != args.subset_size:
            parser.error("explicit --direction count must equal --subset-size")
        if any(value not in shell_by_direction for value in selected):
            parser.error("an explicit direction is not in the requested shell")
        subsets = [selected]
    else:
        subsets = itertools.combinations(directions, args.subset_size)

    payload = {
        "parameters": vars(args),
        "hard_line_count": len(hard_lines),
        "shell_line_count": len(shell_lines),
        "shell_directions": {
            ",".join(map(str, direction)): len(shell_by_direction[direction])
            for direction in directions
        },
        "layers": [],
    }
    output = HERE / args.out
    for subset in subsets:
        record = solve_subset(
            args, base, hitting, subset, hard_lines, shell_by_direction
        )
        payload["layers"].append(record)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "directions": record["directions"],
                    "status": record["status"],
                    "wall_s": record["wall_s"],
                }
            ),
            flush=True,
        )

    payload["closed_subset_count"] = sum(
        item["classification"] == "CLOSED" for item in payload["layers"]
    )
    payload["surviving_subset_count"] = sum(
        item["classification"] == "SURVIVES" for item in payload["layers"]
    )
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
