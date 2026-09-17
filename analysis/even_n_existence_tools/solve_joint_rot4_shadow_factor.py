"""CP-SAT proof search for the minimum independent F0 escape radius.

Deletion and shadow-factor choice are optimized jointly.  This avoids
enumerating millions of independent hitting sets and gives an exact
SAT/UNSAT answer for a fixed deletion count k.
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
    safe_add_orbit,
)
from search_rot4_shadow_escape_radius import candidate_blockers


HERE = Path(__file__).resolve().parent


def solve_size(
    base: dict,
    defects: list[list[int]],
    blockers: dict[tuple[int, int], tuple[int, ...]],
    size: int,
    time_limit: float,
    workers: int,
) -> dict:
    started = time.time()
    edges = [tuple(edge) for edge in base["edges"]]
    incident_base = defaultdict(list)
    edge_index = {}
    for index, (u, v) in enumerate(edges):
        assert u != v
        incident_base[u].append(index)
        incident_base[v].append(index)
        edge_index[(u, v)] = index
    assert all(len(incident_base[v]) == 2 for v in range(M))

    model = cp_model.CpModel()
    removed = [model.NewBoolVar(f"r_{i}") for i in range(M)]
    model.Add(sum(removed) == size)
    for defect in defects:
        model.Add(sum(removed[i] for i in defect) >= 1)
    for vertex in range(M):
        model.Add(sum(removed[i] for i in incident_base[vertex]) <= 1)

    cells = []
    selected = []
    incident_cells = defaultdict(list)
    pair_variables = defaultdict(list)
    blocker_constraint_count = 0
    for u, v in itertools.combinations(range(M), 2):
        edge = (u, v)
        for cell in ((u, v), (v, u)):
            variable = model.NewBoolVar(f"x_{cell[0]}_{cell[1]}")
            cell_no = len(cells)
            cells.append(cell)
            selected.append(variable)
            pair_variables[edge].append(variable)
            incident_cells[u].append(variable)
            incident_cells[v].append(variable)
            for blocker in blockers[cell]:
                owners = [
                    removed[i] for i in range(M) if (blocker >> i) & 1
                ]
                model.Add(variable <= sum(owners))
                blocker_constraint_count += 1
        model.Add(sum(pair_variables[edge]) <= 1)
        if edge in edge_index:
            model.Add(sum(pair_variables[edge]) <= removed[edge_index[edge]])

    for vertex in range(M):
        model.Add(
            sum(incident_cells[vertex])
            == sum(removed[i] for i in incident_base[vertex])
        )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = 2026071902 + size
    status = solver.Solve(model)
    result = {
        "size": size,
        "status": solver.StatusName(status),
        "wall_s": round(solver.WallTime(), 3),
        "elapsed_s": round(time.time() - started, 3),
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "candidate_orientation_variables": len(selected),
        "blocker_constraints": blocker_constraint_count,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        removed_indices = [
            i for i, variable in enumerate(removed) if solver.Value(variable)
        ]
        chosen_cells = [
            cell for cell, variable in zip(cells, selected) if solver.Value(variable)
        ]
        result.update(
            {
                "removed_indices": removed_indices,
                "removed_edges": [list(edges[i]) for i in removed_indices],
                "chosen_cells": [list(cell) for cell in chosen_cells],
            }
        )

        # Independent validation against the direct geometric oracle.
        removed_set = set(removed_indices)
        retained_points = [
            point
            for i in range(M)
            if i not in removed_set
            for point in c4_lifts(directed_cell(edges[i], base["bits"][i]))
        ]
        assert not has_collinear_triple(retained_points)
        assert all(
            safe_add_orbit(retained_points, c4_lifts(cell))
            for cell in chosen_cells
        )
        assert len(chosen_cells) == size
        degree = defaultdict(int)
        for u, v in chosen_cells:
            degree[u] += 1
            degree[v] += 1
        affected = {
            vertex for i in removed_indices for vertex in edges[i]
        }
        assert set(degree) == affected
        assert all(degree[vertex] == 1 for vertex in affected)
        result["full_union_exact"] = not has_collinear_triple(
            retained_points
            + [point for cell in chosen_cells for point in c4_lifts(cell)]
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-size", type=int, default=5)
    parser.add_argument("--max-size", type=int, default=18)
    parser.add_argument("--time-limit", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", default="joint_rot4_shadow_factor.json")
    args = parser.parse_args()

    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = [
        item
        for item in archive["archive"]
        if item["id"] in {f"v40_{i:02d}" for i in range(1, 5)}
    ]
    payload = {"parameters": vars(args), "bases": []}
    output = HERE / args.out
    for base in sorted(bases, key=lambda item: item["id"]):
        hitting = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base['id']}.json").read_text(
                encoding="utf-8"
            )
        )
        lower = max(
            args.min_size,
            hitting["minimum_independent_hitting_set"]["size"],
        )
        print(f"{base['id']}: precomputing blockers", flush=True)
        blockers = candidate_blockers(base)
        runs = []
        for size in range(lower, args.max_size + 1):
            print(f"  solving k={size}", flush=True)
            result = solve_size(
                base,
                hitting["defect_owner_sets"],
                blockers,
                size,
                args.time_limit,
                args.workers,
            )
            runs.append(result)
            print(
                f"    {result['status']} wall={result['wall_s']}s "
                f"branches={result['branches']} "
                f"full_exact={result.get('full_union_exact')}",
                flush=True,
            )
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            if result["status"] in ("OPTIMAL", "FEASIBLE"):
                break
            if result["status"] != "INFEASIBLE":
                break
        payload["bases"].append({"base": base["id"], "runs": runs})
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
