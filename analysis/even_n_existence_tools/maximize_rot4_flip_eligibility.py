"""Maximize locally safe orientation flips using deletion constraints only.

This deliberately omits the replacement f-factor and every line-capacity
constraint.  It asks whether the deletion segment shape plus the one-orbit
blocker oracle already bounds the number of old cells whose reversed
orientation can be safely reinserted.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_rot4_shadow_factor import M, SOURCE_OUTPUTS, directed_cell
from search_rot4_shadow_escape_radius import candidate_blockers


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--adjacency-count", type=int, required=True)
    parser.add_argument("--triple-count", type=int, default=None)
    parser.add_argument("--quadruple-count", type=int, default=None)
    parser.add_argument("--time-limit", type=float, default=300.0)
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
    blockers = candidate_blockers(base)
    edges = [tuple(edge) for edge in base["edges"]]
    incident = defaultdict(list)
    for index, (u, v) in enumerate(edges):
        incident[u].append(index)
        incident[v].append(index)
    assert all(len(incident[u]) == 2 for u in range(M))

    model = cp_model.CpModel()
    removed = [model.NewBoolVar(f"r_{i}") for i in range(M)]
    model.Add(sum(removed) == args.size)
    for defect in hitting["defect_owner_sets"]:
        model.Add(sum(removed[index] for index in defect) >= 1)

    adjacent = []
    for vertex in range(M):
        first, second = incident[vertex]
        value = model.NewBoolVar(f"A_{vertex}")
        model.Add(value <= removed[first])
        model.Add(value <= removed[second])
        model.Add(value >= removed[first] + removed[second] - 1)
        adjacent.append(value)
    model.Add(sum(adjacent) == args.adjacency_count)

    triples = []
    for index, (u, v) in enumerate(edges):
        previous = next(item for item in incident[u] if item != index)
        following = next(item for item in incident[v] if item != index)
        value = model.NewBoolVar(f"B_{index}")
        model.Add(value <= removed[previous])
        model.Add(value <= removed[index])
        model.Add(value <= removed[following])
        model.Add(
            value
            >= removed[previous] + removed[index] + removed[following] - 2
        )
        triples.append(value)
    if args.triple_count is not None:
        model.Add(sum(triples) == args.triple_count)

    quadruples = []
    for vertex in range(M):
        first, second = incident[vertex]
        value = model.NewBoolVar(f"C_{vertex}")
        model.Add(value <= triples[first])
        model.Add(value <= triples[second])
        model.Add(value >= triples[first] + triples[second] - 1)
        quadruples.append(value)
    if args.quadruple_count is not None:
        model.Add(sum(quadruples) == args.quadruple_count)

    eligible = []
    for index, (edge, bit) in enumerate(zip(edges, base["bits"])):
        old_cell = directed_cell(edge, bit)
        reverse_cell = (old_cell[1], old_cell[0])
        value = model.NewBoolVar(f"flip_eligible_{index}")
        model.Add(value <= removed[index])
        for blocker in blockers[reverse_cell]:
            model.Add(
                value
                <= sum(
                    removed[owner]
                    for owner in range(M)
                    if (blocker >> owner) & 1
                )
            )
        eligible.append(value)
    model.Maximize(sum(eligible))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = 2026071913
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
        payload["removed_indices"] = [
            index for index, value in enumerate(removed) if solver.Value(value)
        ]
        payload["eligible_flip_indices"] = [
            index for index, value in enumerate(eligible) if solver.Value(value)
        ]
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(output)


if __name__ == "__main__":
    main()
