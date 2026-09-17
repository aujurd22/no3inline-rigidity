"""Scan fixed deletion shapes against the corrected multigraph f-factor.

The monolithic CP model must choose a deletion mask and a replacement factor
simultaneously.  This script separates those layers: enumerate masks satisfying
the defect and run-window constraints, then solve the much smaller factor model
with each mask fixed.  This is both a search tool and a way to identify whether
the obstruction already occurs before line-capacity constraints are added.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import M, SOURCE_OUTPUTS
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import (
    build_general_model,
    short_direction_lines,
)
from solve_joint_rot4_line_cuts import add_line_capacity, extract_solution


HERE = Path(__file__).resolve().parent


class MaskCollector(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables, limit: int):
        super().__init__()
        self.variables = variables
        self.limit = limit
        self.masks: list[list[int]] = []

    def on_solution_callback(self) -> None:
        self.masks.append(
            [
                index
                for index, variable in enumerate(self.variables)
                if self.Value(variable)
            ]
        )
        if len(self.masks) >= self.limit:
            self.StopSearch()


def deletion_model(
    edges: list[tuple[int, int]],
    defects: list[list[int]],
    size: int,
    adjacency_count: int,
    triple_count: int,
    quadruple_count: int,
):
    incident = defaultdict(list)
    for index, (u, v) in enumerate(edges):
        incident[u].append(index)
        incident[v].append(index)
    model = cp_model.CpModel()
    removed = [model.NewBoolVar(f"r_{i}") for i in range(M)]
    model.Add(sum(removed) == size)
    for defect in defects:
        model.Add(sum(removed[i] for i in defect) >= 1)
    adjacent = []
    for vertex in range(M):
        first, second = incident[vertex]
        value = model.NewBoolVar(f"A_{vertex}")
        model.Add(value <= removed[first])
        model.Add(value <= removed[second])
        model.Add(value >= removed[first] + removed[second] - 1)
        adjacent.append(value)
    model.Add(sum(adjacent) == adjacency_count)
    triples = []
    for index, (u, v) in enumerate(edges):
        previous = next(i for i in incident[u] if i != index)
        following = next(i for i in incident[v] if i != index)
        value = model.NewBoolVar(f"B_{index}")
        model.Add(value <= removed[previous])
        model.Add(value <= removed[index])
        model.Add(value <= removed[following])
        model.Add(value >= removed[previous] + removed[index] + removed[following] - 2)
        triples.append(value)
    model.Add(sum(triples) == triple_count)
    quadruples = []
    for vertex in range(M):
        first, second = incident[vertex]
        value = model.NewBoolVar(f"C_{vertex}")
        model.Add(value <= triples[first])
        model.Add(value <= triples[second])
        model.Add(value >= triples[first] + triples[second] - 1)
        quadruples.append(value)
    model.Add(sum(quadruples) == quadruple_count)
    return model, removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, default=12)
    parser.add_argument("--adjacency-count", type=int, default=6)
    parser.add_argument("--triple-count", type=int, default=1)
    parser.add_argument("--quadruple-count", type=int, default=0)
    parser.add_argument("--direction-q", type=int, default=0)
    parser.add_argument("--mask-limit", type=int, default=1000)
    parser.add_argument("--enumeration-time", type=float, default=60.0)
    parser.add_argument("--factor-time", type=float, default=2.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    started = time.time()

    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    hitting = json.loads(
        (SOURCE_OUTPUTS / f"defect_hitting_{args.base}.json").read_text(
            encoding="utf-8"
        )
    )
    edges = [tuple(edge) for edge in base["edges"]]
    model, removed_variables = deletion_model(
        edges,
        hitting["defect_owner_sets"],
        args.size,
        args.adjacency_count,
        args.triple_count,
        args.quadruple_count,
    )
    collector = MaskCollector(removed_variables, args.mask_limit)
    deletion_solver = cp_model.CpSolver()
    deletion_solver.parameters.max_time_in_seconds = args.enumeration_time
    deletion_solver.parameters.num_search_workers = 1
    deletion_solver.parameters.enumerate_all_solutions = True
    enumeration_status = deletion_solver.Solve(model, collector)

    blockers = candidate_blockers(base)
    line_keys = short_direction_lines(args.direction_q)
    status_histogram = defaultdict(int)
    factor_wall_total = 0.0
    records = []
    feasible_record = None
    for number, removed_indices in enumerate(collector.masks, 1):
        problem = build_general_model(
            base,
            hitting["defect_owner_sets"],
            blockers,
            args.size,
            args.adjacency_count,
            args.triple_count,
            None,
            None,
            None,
            args.quadruple_count,
            True,
            False,
        )
        removed_set = set(removed_indices)
        for index, variable in enumerate(problem["removed"]):
            problem["model"].Add(variable == (index in removed_set))
        for key in line_keys:
            add_line_capacity(problem, key)
        factor_solver = cp_model.CpSolver()
        factor_solver.parameters.max_time_in_seconds = args.factor_time
        factor_solver.parameters.num_search_workers = 1
        factor_solver.parameters.random_seed = 2026071916 + number
        status = factor_solver.Solve(problem["model"])
        name = factor_solver.StatusName(status)
        status_histogram[name] += 1
        factor_wall_total += factor_solver.WallTime()
        if number <= 20 or status != cp_model.INFEASIBLE:
            records.append(
                {
                    "number": number,
                    "removed_indices": removed_indices,
                    "status": name,
                    "wall_s": round(factor_solver.WallTime(), 4),
                    "branches": factor_solver.NumBranches(),
                    "conflicts": factor_solver.NumConflicts(),
                }
            )
        if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
            feasible_record = {
                "number": number,
                "removed_indices": removed_indices,
                "solution": extract_solution(problem, factor_solver),
                "selected_antiparallel_pairs": sum(
                    factor_solver.Value(value)
                    for value in problem["antiparallel_pair_terms"]
                ),
                "reverse_along_retained_old": sum(
                    factor_solver.Value(reverse)
                    * (1 - factor_solver.Value(problem["removed"][index]))
                    for index, reverse in enumerate(
                        problem["reverse_parallel_by_old_index"]
                    )
                ),
            }
            break
        if number % 100 == 0:
            print(
                f"{args.base}: tested={number} statuses={dict(status_histogram)} "
                f"factor_wall={factor_wall_total:.2f}s",
                flush=True,
            )

    payload = {
        "parameters": vars(args),
        "enumeration_status": deletion_solver.StatusName(enumeration_status),
        "enumeration_wall_s": round(deletion_solver.WallTime(), 3),
        "collected_mask_count": len(collector.masks),
        "tested_mask_count": sum(status_histogram.values()),
        "factor_status_histogram": dict(status_histogram),
        "factor_wall_total_s": round(factor_wall_total, 3),
        "first_feasible": feasible_record,
        "sample_records": records,
        "elapsed_s": round(time.time() - started, 3),
    }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "enumeration_status",
        "collected_mask_count",
        "tested_mask_count",
        "factor_status_histogram",
        "factor_wall_total_s",
        "first_feasible",
        "elapsed_s",
    )}, indent=2))
    print(output)


if __name__ == "__main__":
    main()
