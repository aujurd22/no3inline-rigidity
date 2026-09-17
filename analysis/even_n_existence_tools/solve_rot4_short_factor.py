"""Decide a normalized fixed-shape f-factor with all short-line capacities."""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
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


def factor_cycle_edge_components(edges: list[tuple[int, int]]):
    incident = defaultdict(list)
    for index, (u, v) in enumerate(edges):
        incident[u].append((v, index))
        incident[v].append((u, index))
    unseen = set(range(len(edges)))
    components = []
    while unseen:
        root_edge = min(unseen)
        stack = [edges[root_edge][0]]
        vertices = set()
        edge_indices = set()
        while stack:
            vertex = stack.pop()
            if vertex in vertices:
                continue
            vertices.add(vertex)
            for neighbour, edge_index in incident[vertex]:
                edge_indices.add(edge_index)
                stack.append(neighbour)
        unseen.difference_update(edge_indices)
        components.append(
            {
                "length": len(edge_indices),
                "vertices": sorted(vertices),
                "edge_indices": sorted(edge_indices),
            }
        )
    return sorted(
        components,
        key=lambda item: (item["length"], item["vertices"]),
    )


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
    parser.add_argument(
        "--reselected-count",
        type=int,
        default=None,
        help="with normalization, this is exactly the orientation-flip count",
    )
    parser.add_argument(
        "--flip-min",
        type=int,
        default=None,
        help="optional valid lower bound on the orientation-flip count",
    )
    parser.add_argument(
        "--flip-max",
        type=int,
        default=None,
        help="optional valid upper bound on the orientation-flip count",
    )
    parser.add_argument("--deficit-two-edge-count", type=int, default=None)
    parser.add_argument(
        "--cycle-length-deletion",
        action="append",
        default=[],
        help="fix removed edges in a uniquely sized factor cycle, as length:count",
    )
    parser.add_argument("--direction-q", type=int, required=True)
    parser.add_argument("--allow-exact-reselection", action="store_true")
    parser.add_argument(
        "--forbid-antiparallel",
        action="store_true",
        help="legacy simple-underlying-graph restriction; not valid for the full multigraph model",
    )
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
        args.reselected_count,
        args.deficit_two_edge_count,
        args.quadruple_count,
        not args.allow_exact_reselection,
        args.forbid_antiparallel,
    )
    lines = short_direction_lines(args.direction_q)
    if args.adjacency_min is not None:
        problem["model"].Add(
            sum(problem["adjacent_pairs"]) >= args.adjacency_min
        )
    if args.adjacency_max is not None:
        problem["model"].Add(
            sum(problem["adjacent_pairs"]) <= args.adjacency_max
        )
    if args.flip_min is not None:
        problem["model"].Add(
            sum(problem["flipped_reselection_terms"]) >= args.flip_min
        )
    if args.flip_max is not None:
        problem["model"].Add(
            sum(problem["flipped_reselection_terms"]) <= args.flip_max
        )
    components = factor_cycle_edge_components(problem["edges"])
    for raw in args.cycle_length_deletion:
        length, count = (int(value) for value in raw.split(":"))
        matching = [
            component
            for component in components
            if component["length"] == length
        ]
        if len(matching) != 1:
            parser.error(
                f"cycle length {length} matches {len(matching)} components"
            )
        problem["model"].Add(
            sum(
                problem["removed"][index]
                for index in matching[0]["edge_indices"]
            )
            == count
        )
    for key in lines:
        add_line_capacity(problem, key)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = 2026071908
    started = time.time()
    status = solver.Solve(problem["model"])
    payload = {
        "parameters": vars(args),
        "status": solver.StatusName(status),
        "short_line_count": len(lines),
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "wall_s": round(solver.WallTime(), 3),
        "elapsed_s": round(time.time() - started, 3),
        "factor_cycle_components": components,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        payload["solution"] = extract_solution(problem, solver)
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
            "selected_antiparallel_pairs": sum(
                solver.Value(variable)
                for variable in problem["antiparallel_pair_terms"]
            ),
            "reverse_orbits_added_alongside_retained_old_edge": sum(
                solver.Value(reverse) * (1 - solver.Value(problem["removed"][i]))
                for i, reverse in enumerate(
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
                "short_line_count": payload["short_line_count"],
                "wall_s": payload["wall_s"],
            },
            indent=2,
        )
    )
    print(output)


if __name__ == "__main__":
    main()
