#!/usr/bin/env python3
"""Exact zero-conflict LNS around the certified m=37 score-60 factor."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from ortools.sat.python import cp_model


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--seed-input", type=Path, required=True)
    ap.add_argument("--core-input", type=Path, required=True)
    ap.add_argument("--time-limit", type=float, default=600.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, default=here / "results" /
                    "pair_codegree_37" / "conflict_core_lns8_m37.json")
    args = ap.parse_args()

    tools = here / "even_n_existence_tools"
    sys.path.insert(0, str(tools))
    from nearest_c4_solution_sat import build_model, verify

    seed = json.loads(args.seed_input.read_text(encoding="utf-8"))
    core = json.loads(args.core_input.read_text(encoding="utf-8"))
    edges = tuple(map(tuple, seed["edges"]))
    bits = tuple(map(int, seed["bits"]))
    cells = tuple((v, u) if bit else (u, v)
                  for (u, v), bit in zip(edges, bits))
    active = set(core["minimum_edge_hitting_set"]["edge_indices"])
    fixed_cells = {cell for index, cell in enumerate(cells) if index not in active}

    began_build = time.time()
    model, variables, changes, statistics = build_model(
        37, set(cells), minimize_changes=False, hint_reference=True)
    for cell in fixed_cells:
        model.Add(variables[cell] == 1)
    build_seconds = time.time() - began_build

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = args.workers
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.log_search_progress = False
    began_solve = time.time()
    status = solver.Solve(model)
    solve_seconds = time.time() - began_solve
    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    solution_cells = None
    verification = None
    if feasible:
        solution_cells = tuple(cell for cell, var in variables.items()
                               if solver.Value(var))
        verification = verify(solution_cells, 37)

    payload = {
        "definition": "exact NTIL LNS fixing all score-60 cells outside one minimum conflict-edge hitting set",
        "seed_input": str(args.seed_input),
        "core_input": str(args.core_input),
        "seed_objective": seed.get("objective", seed.get("verified_board_total")),
        "active_edge_indices": sorted(active),
        "active_edges": [list(edges[i]) for i in sorted(active)],
        "active_cells": [list(cells[i]) for i in sorted(active)],
        "fixed_cell_count": len(fixed_cells),
        "fixed_cells": [list(cell) for cell in sorted(fixed_cells)],
        "model_statistics": statistics,
        "build_seconds": build_seconds,
        "status": solver.StatusName(status),
        "feasible": feasible,
        "best_objective_bound": float(solver.BestObjectiveBound()),
        "solve_seconds": solve_seconds,
        "workers": args.workers,
        "solution_cells": ([list(cell) for cell in solution_cells]
                           if solution_cells else None),
        "verification": verification,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "active_edge_indices", "fixed_cell_count", "build_seconds", "status",
        "feasible", "best_objective_bound", "solve_seconds", "verification")}, indent=2))


if __name__ == "__main__":
    main()
