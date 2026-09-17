"""Exact line-cut closure of the joint rot4 deletion/shadow-factor model.

At fixed independent deletion radius k, CP-SAT first solves the polynomial
one-orbit shadow model.  Every bad geometric line in the returned 37-orbit
factor is then converted into the globally valid capacity inequality

    sum_c |O(c) intersect L| z_c <= 2,

where retained base orbit i has z_i = 1-r_i and replacement orbit c has
z_c = x_c.  The loop stops at a genuine m=37 solution, an exact UNSAT proof,
or a user-specified round/time limit.
"""

from __future__ import annotations

import argparse
import itertools
import json
import time
from collections import defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import (
    M,
    SOURCE_OUTPUTS,
    c4_lifts,
    directed_cell,
    has_collinear_triple,
    line_key,
)
from search_rot4_shadow_escape_radius import candidate_blockers


HERE = Path(__file__).resolve().parent


def bad_lines(points: list[tuple[int, int]]) -> list[tuple[int, int, int]]:
    masks = {}
    for i, j in itertools.combinations(range(len(points)), 2):
        key = line_key(points[i], points[j])
        assert key is not None
        masks[key] = masks.get(key, 0) | (1 << i) | (1 << j)
    return sorted(key for key, mask in masks.items() if mask.bit_count() >= 3)


def build_model(
    base: dict,
    defects: list[list[int]],
    blockers: dict[tuple[int, int], tuple[int, ...]],
    size: int,
):
    edges = [tuple(edge) for edge in base["edges"]]
    incident_base = defaultdict(list)
    edge_index = {}
    for index, (u, v) in enumerate(edges):
        incident_base[u].append(index)
        incident_base[v].append(index)
        edge_index[(u, v)] = index

    model = cp_model.CpModel()
    removed = [model.NewBoolVar(f"r_{i}") for i in range(M)]
    model.Add(sum(removed) == size)
    for defect in defects:
        model.Add(sum(removed[i] for i in defect) >= 1)
    for vertex in range(M):
        model.Add(sum(removed[i] for i in incident_base[vertex]) <= 1)

    cells = []
    selected = []
    cell_variable = {}
    incident_cells = defaultdict(list)
    for u, v in itertools.combinations(range(M), 2):
        pair = []
        for cell in ((u, v), (v, u)):
            variable = model.NewBoolVar(f"x_{cell[0]}_{cell[1]}")
            cells.append(cell)
            selected.append(variable)
            cell_variable[cell] = variable
            pair.append(variable)
            incident_cells[u].append(variable)
            incident_cells[v].append(variable)
            for blocker in blockers[cell]:
                model.Add(
                    variable
                    <= sum(
                        removed[i] for i in range(M) if (blocker >> i) & 1
                    )
                )
        model.Add(sum(pair) <= 1)
        if (u, v) in edge_index:
            model.Add(sum(pair) <= removed[edge_index[(u, v)]])
    for vertex in range(M):
        model.Add(
            sum(incident_cells[vertex])
            == sum(removed[i] for i in incident_base[vertex])
        )

    base_cells = [
        directed_cell(edge, bit) for edge, bit in zip(edges, base["bits"])
    ]
    base_orbits = [c4_lifts(cell) for cell in base_cells]
    candidate_orbits = {cell: c4_lifts(cell) for cell in cells}
    return {
        "model": model,
        "edges": edges,
        "removed": removed,
        "cells": cells,
        "selected": selected,
        "cell_variable": cell_variable,
        "base_cells": base_cells,
        "base_orbits": base_orbits,
        "candidate_orbits": candidate_orbits,
    }


def add_line_capacity(problem: dict, key: tuple[int, int, int]) -> dict:
    a, b, c = key
    old_counts = [
        sum(a * x + b * y == c for x, y in orbit)
        for orbit in problem["base_orbits"]
    ]
    new_counts = {
        cell: sum(a * x + b * y == c for x, y in orbit)
        for cell, orbit in problem["candidate_orbits"].items()
    }
    old_total = sum(old_counts)
    # sum old_count*(1-r) + sum new_count*x <= 2
    problem["model"].Add(
        sum(
            count * problem["cell_variable"][cell]
            for cell, count in new_counts.items()
            if count
        )
        - sum(
            count * problem["removed"][i]
            for i, count in enumerate(old_counts)
            if count
        )
        <= 2 - old_total
    )
    return {
        "old_orbit_terms": sum(bool(count) for count in old_counts),
        "new_orbit_terms": sum(bool(count) for count in new_counts.values()),
        "old_point_capacity": old_total,
        "potential_new_point_capacity": sum(new_counts.values()),
    }


def extract_solution(problem: dict, solver: cp_model.CpSolver) -> dict:
    removed_indices = [
        i
        for i, variable in enumerate(problem["removed"])
        if solver.Value(variable)
    ]
    chosen_cells = [
        cell
        for cell, variable in zip(problem["cells"], problem["selected"])
        if solver.Value(variable)
    ]
    removed_set = set(removed_indices)
    active_cells = [
        cell
        for i, cell in enumerate(problem["base_cells"])
        if i not in removed_set
    ] + chosen_cells
    points = [point for cell in active_cells for point in c4_lifts(cell)]
    assert len(active_cells) == M
    assert len(points) == 4 * M
    assert len(points) == len(set(points))
    lines = bad_lines(points)
    return {
        "removed_indices": removed_indices,
        "removed_edges": [
            list(problem["edges"][i]) for i in removed_indices
        ],
        "chosen_cells": [list(cell) for cell in chosen_cells],
        "bad_line_count": len(lines),
        "bad_lines": [list(key) for key in lines],
        "exact": not lines,
        "points": [list(point) for point in points] if not lines else None,
    }


def solve_with_cuts(
    base: dict,
    defects: list[list[int]],
    blockers: dict[tuple[int, int], tuple[int, ...]],
    size: int,
    max_rounds: int,
    per_round_time: float,
    total_time: float,
    workers: int,
) -> dict:
    started = time.time()
    problem = build_model(base, defects, blockers, size)
    known_lines = set()
    rounds = []
    best_bad_lines = None
    best_solution = None
    final_status = "ROUND_LIMIT"
    for round_no in range(1, max_rounds + 1):
        remaining = total_time - (time.time() - started)
        if remaining <= 0:
            final_status = "TOTAL_TIME_LIMIT"
            break
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(per_round_time, remaining)
        solver.parameters.num_search_workers = workers
        solver.parameters.random_seed = 2026071903 + size * 1000 + round_no
        status = solver.Solve(problem["model"])
        record = {
            "round": round_no,
            "status": solver.StatusName(status),
            "wall_s": round(solver.WallTime(), 3),
            "branches": solver.NumBranches(),
            "conflicts": solver.NumConflicts(),
            "known_line_cuts_before": len(known_lines),
        }
        if status == cp_model.INFEASIBLE:
            final_status = "INFEASIBLE"
            rounds.append(record)
            break
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            final_status = solver.StatusName(status)
            rounds.append(record)
            break

        solution = extract_solution(problem, solver)
        record["bad_line_count"] = solution["bad_line_count"]
        if best_bad_lines is None or solution["bad_line_count"] < best_bad_lines:
            best_bad_lines = solution["bad_line_count"]
            best_solution = solution
        if solution["exact"]:
            assert not has_collinear_triple(
                [tuple(point) for point in solution["points"]]
            )
            final_status = "EXACT_SOLUTION"
            rounds.append(record)
            best_solution = solution
            break

        new_lines = [
            tuple(key)
            for key in solution["bad_lines"]
            if tuple(key) not in known_lines
        ]
        line_stats = []
        for key in new_lines:
            known_lines.add(key)
            line_stats.append(add_line_capacity(problem, key))
        record["new_line_cuts"] = len(new_lines)
        record["known_line_cuts_after"] = len(known_lines)
        record["cut_term_totals"] = {
            name: sum(item[name] for item in line_stats)
            for name in (
                "old_orbit_terms",
                "new_orbit_terms",
                "old_point_capacity",
                "potential_new_point_capacity",
            )
        }
        rounds.append(record)
        if not new_lines:
            final_status = "NO_NEW_CUT_BUG"
            break
        if round_no % 10 == 0 or round_no == 1:
            print(
                f"      round={round_no} bad_lines={solution['bad_line_count']} "
                f"new_cuts={len(new_lines)} total_cuts={len(known_lines)} "
                f"best={best_bad_lines}",
                flush=True,
            )
    return {
        "size": size,
        "status": final_status,
        "round_count": len(rounds),
        "line_cut_count": len(known_lines),
        "best_bad_line_count": best_bad_lines,
        "best_solution": best_solution,
        "rounds": rounds,
        "elapsed_s": round(time.time() - started, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bases", default="all")
    parser.add_argument("--min-size", type=int, default=10)
    parser.add_argument("--max-size", type=int, default=18)
    parser.add_argument("--max-rounds", type=int, default=300)
    parser.add_argument("--per-round-time", type=float, default=15.0)
    parser.add_argument("--total-time", type=float, default=600.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", default="joint_rot4_line_cuts.json")
    args = parser.parse_args()

    wanted = (
        {f"v40_{i:02d}" for i in range(1, 5)}
        if args.bases == "all"
        else set(args.bases.split(","))
    )
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = [item for item in archive["archive"] if item["id"] in wanted]
    payload = {"parameters": vars(args), "bases": []}
    output = HERE / args.out
    for base in sorted(bases, key=lambda item: item["id"]):
        hitting = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base['id']}.json").read_text(
                encoding="utf-8"
            )
        )
        print(f"{base['id']}: precomputing blockers", flush=True)
        blockers = candidate_blockers(base)
        base_result = {"base": base["id"], "runs": []}
        for size in range(args.min_size, args.max_size + 1):
            print(f"  k={size}: starting line-cut closure", flush=True)
            result = solve_with_cuts(
                base,
                hitting["defect_owner_sets"],
                blockers,
                size,
                args.max_rounds,
                args.per_round_time,
                args.total_time,
                args.workers,
            )
            base_result["runs"].append(result)
            print(
                f"    status={result['status']} rounds={result['round_count']} "
                f"cuts={result['line_cut_count']} "
                f"best_bad_lines={result['best_bad_line_count']} "
                f"elapsed={result['elapsed_s']}s",
                flush=True,
            )
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            if result["status"] == "EXACT_SOLUTION":
                break
            if result["status"] not in ("INFEASIBLE",):
                break
        payload["bases"].append(base_result)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
