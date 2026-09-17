"""SCIP/MIP backend for the joint rot4 deletion and f-factor model."""

from __future__ import annotations

import argparse
import itertools
import json
import time
from collections import defaultdict
from pathlib import Path

from ortools.linear_solver import pywraplp

from analyze_rot4_shadow_factor import M, SOURCE_OUTPUTS, c4_lifts, directed_cell
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import (
    canonical_line_orbit,
    short_direction_lines,
)
from solve_joint_rot4_line_cuts import bad_lines


HERE = Path(__file__).resolve().parent


def status_name(status: int) -> str:
    names = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
        pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
        pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
        pywraplp.Solver.ABNORMAL: "ABNORMAL",
        pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
    }
    return names.get(status, f"STATUS_{status}")


def load_seed_lines(path: str) -> set[tuple[int, int, int]]:
    lines: set[tuple[int, int, int]] = set()
    if not path:
        return lines
    payload = json.loads(Path(path).read_text(encoding="utf-8"))

    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "line_keys":
                    lines.update(
                        canonical_line_orbit(tuple(line)) for line in item
                    )
                else:
                    collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(payload)
    return lines


def build_mip(
    base: dict,
    defects: list[list[int]],
    blockers: dict[tuple[int, int], tuple[int, ...]],
    size: int,
    adjacency_count: int | None,
    triple_count: int | None,
    loop_count: int | None,
    reselected_count: int | None,
    deficit_two_edge_count: int | None,
    line_keys: set[tuple[int, int, int]],
    workers: int,
):
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if solver is None:
        raise RuntimeError("SCIP backend is unavailable")
    solver.SetNumThreads(workers)
    edges = [tuple(edge) for edge in base["edges"]]
    incident_base = defaultdict(list)
    edge_index = {}
    for index, (u, v) in enumerate(edges):
        incident_base[u].append(index)
        incident_base[v].append(index)
        edge_index[(u, v)] = index

    removed = [solver.BoolVar(f"r_{i}") for i in range(M)]
    solver.Add(sum(removed) == size)
    for defect in defects:
        solver.Add(sum(removed[i] for i in defect) >= 1)

    adjacent = []
    for vertex in range(M):
        i, j = incident_base[vertex]
        value = solver.BoolVar(f"adj_{vertex}")
        solver.Add(value <= removed[i])
        solver.Add(value <= removed[j])
        solver.Add(value >= removed[i] + removed[j] - 1)
        adjacent.append(value)
    if adjacency_count is not None:
        solver.Add(sum(adjacent) == adjacency_count)

    triples = []
    for index, (u, v) in enumerate(edges):
        previous = next(i for i in incident_base[u] if i != index)
        following = next(i for i in incident_base[v] if i != index)
        value = solver.BoolVar(f"triple_{index}")
        solver.Add(value <= removed[previous])
        solver.Add(value <= removed[index])
        solver.Add(value <= removed[following])
        solver.Add(
            value
            >= removed[previous] + removed[index] + removed[following] - 2
        )
        triples.append(value)
    if triple_count is not None:
        solver.Add(sum(triples) == triple_count)

    cells = []
    selected = []
    cell_variable = {}
    incident_terms = defaultdict(list)
    loop_variables = []
    for u in range(M):
        cell = (u, u)
        variable = solver.BoolVar(f"x_{u}_{u}")
        cells.append(cell)
        selected.append(variable)
        cell_variable[cell] = variable
        loop_variables.append(variable)
        incident_terms[u].append(2 * variable)
        for blocker in blockers[cell]:
            solver.Add(
                variable
                <= sum(removed[i] for i in range(M) if (blocker >> i) & 1)
            )
    if loop_count is not None:
        solver.Add(sum(loop_variables) == loop_count)

    reselected = []
    deficit_two_edges = []
    for u, v in itertools.combinations(range(M), 2):
        pair = []
        for cell in ((u, v), (v, u)):
            variable = solver.BoolVar(f"x_{cell[0]}_{cell[1]}")
            cells.append(cell)
            selected.append(variable)
            cell_variable[cell] = variable
            pair.append(variable)
            incident_terms[u].append(variable)
            incident_terms[v].append(variable)
            for blocker in blockers[cell]:
                solver.Add(
                    variable
                    <= sum(
                        removed[i] for i in range(M) if (blocker >> i) & 1
                    )
                )
        pair_on = sum(pair)
        solver.Add(pair_on <= 1)
        if deficit_two_edge_count is not None:
            both = solver.BoolVar(f"def2edge_{u}_{v}")
            solver.Add(both <= pair_on)
            solver.Add(both <= adjacent[u])
            solver.Add(both <= adjacent[v])
            solver.Add(both >= pair_on + adjacent[u] + adjacent[v] - 2)
            deficit_two_edges.append(both)
        if (u, v) in edge_index:
            solver.Add(pair_on <= removed[edge_index[(u, v)]])
            reselected.extend(pair)
    if reselected_count is not None:
        solver.Add(sum(reselected) == reselected_count)
    if deficit_two_edge_count is not None:
        solver.Add(sum(deficit_two_edges) == deficit_two_edge_count)

    for vertex in range(M):
        solver.Add(
            sum(incident_terms[vertex])
            == sum(removed[i] for i in incident_base[vertex])
        )
    solver.Add(sum(selected) == size)

    base_cells = [
        directed_cell(edge, bit) for edge, bit in zip(edges, base["bits"])
    ]
    base_orbits = [c4_lifts(cell) for cell in base_cells]
    candidate_orbits = {cell: c4_lifts(cell) for cell in cells}

    def add_line(key: tuple[int, int, int]):
        a, b, c = key
        old_counts = [
            sum(a * x + b * y == c for x, y in orbit)
            for orbit in base_orbits
        ]
        new_counts = {
            cell: sum(a * x + b * y == c for x, y in orbit)
            for cell, orbit in candidate_orbits.items()
        }
        solver.Add(
            sum(
                count * cell_variable[cell]
                for cell, count in new_counts.items()
                if count
            )
            - sum(
                count * removed[i]
                for i, count in enumerate(old_counts)
                if count
            )
            <= 2 - sum(old_counts)
        )

    for key in sorted(line_keys):
        add_line(key)
    return {
        "solver": solver,
        "edges": edges,
        "removed": removed,
        "cells": cells,
        "selected": selected,
        "base_cells": base_cells,
        "add_line": add_line,
    }


def extract(problem: dict) -> dict:
    removed_indices = [
        i for i, variable in enumerate(problem["removed"])
        if variable.solution_value() > 0.5
    ]
    chosen_cells = [
        cell
        for cell, variable in zip(problem["cells"], problem["selected"])
        if variable.solution_value() > 0.5
    ]
    removed_set = set(removed_indices)
    active = [
        cell
        for i, cell in enumerate(problem["base_cells"])
        if i not in removed_set
    ] + chosen_cells
    points = [point for cell in active for point in c4_lifts(cell)]
    lines = bad_lines(points)
    return {
        "removed_indices": removed_indices,
        "removed_edges": [
            list(problem["edges"][i]) for i in removed_indices
        ],
        "chosen_cells": [list(cell) for cell in chosen_cells],
        "bad_line_count": len(lines),
        "bad_lines": [list(line) for line in lines],
        "exact": not lines,
        "points": [list(point) for point in points] if not lines else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="v40_01")
    parser.add_argument("--size", type=int, default=11)
    parser.add_argument("--adjacency-count", type=int, default=None)
    parser.add_argument("--triple-count", type=int, default=None)
    parser.add_argument("--loop-count", type=int, default=None)
    parser.add_argument("--reselected-count", type=int, default=None)
    parser.add_argument("--deficit-two-edge-count", type=int, default=None)
    parser.add_argument("--short-direction-q", type=int, default=1)
    parser.add_argument("--seed-json", default="")
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--time-per-round", type=float, default=300.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", default="rot4_general_mip.json")
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
    known_lines = set(short_direction_lines(args.short_direction_q))
    known_lines.update(load_seed_lines(args.seed_json))
    problem = build_mip(
        base,
        hitting["defect_owner_sets"],
        blockers,
        args.size,
        args.adjacency_count,
        args.triple_count,
        args.loop_count,
        args.reselected_count,
        args.deficit_two_edge_count,
        known_lines,
        args.workers,
    )
    payload = {"parameters": vars(args), "rounds": []}
    output = HERE / args.out
    started = time.time()
    for round_no in range(1, args.rounds + 1):
        problem["solver"].SetTimeLimit(round(args.time_per_round * 1000))
        status = problem["solver"].Solve()
        record = {
            "round": round_no,
            "status": status_name(status),
            "wall_ms": problem["solver"].wall_time(),
            "iterations": problem["solver"].iterations(),
            "nodes": problem["solver"].nodes(),
            "line_count_before": len(known_lines),
        }
        print(
            f"round={round_no} status={record['status']} "
            f"nodes={record['nodes']} lines={len(known_lines)}",
            flush=True,
        )
        if status == pywraplp.Solver.INFEASIBLE:
            payload["status"] = "INFEASIBLE"
            payload["rounds"].append(record)
            break
        if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            payload["status"] = record["status"]
            payload["rounds"].append(record)
            break
        solution = extract(problem)
        record["bad_line_count"] = solution["bad_line_count"]
        record["solution"] = solution
        if solution["exact"]:
            payload["status"] = "EXACT_SOLUTION"
            payload["solution"] = solution
            payload["rounds"].append(record)
            break
        new_lines = sorted(
            {
                canonical_line_orbit(tuple(line))
                for line in solution["bad_lines"]
            }
            - known_lines
        )
        for key in new_lines:
            known_lines.add(key)
            problem["add_line"](key)
        record["new_line_count"] = len(new_lines)
        record["line_count_after"] = len(known_lines)
        payload["rounds"].append(record)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        payload["status"] = "ROUND_LIMIT"
    payload["elapsed_s"] = round(time.time() - started, 3)
    payload["line_keys"] = [list(key) for key in sorted(known_lines)]
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
