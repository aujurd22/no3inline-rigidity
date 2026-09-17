#!/usr/bin/env python3
"""Exact C4-NTIL feasibility inside a Hamming ball around an m=37 seed."""

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
    ap.add_argument("--radius", type=int, default=8)
    ap.add_argument("--time-limit", type=float, default=600.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, default=here / "results" /
                    "pair_codegree_37" / "exact_hamming_ball_r8_m37.json")
    args = ap.parse_args()

    sys.path.insert(0, str(here / "even_n_existence_tools"))
    from nearest_c4_solution_sat import build_model, verify

    seed = json.loads(args.seed_input.read_text(encoding="utf-8"))
    edges = tuple(map(tuple, seed["edges"]))
    bits = tuple(map(int, seed["bits"]))
    cells = {(v, u) if bit else (u, v)
             for (u, v), bit in zip(edges, bits)}
    build_started = time.time()
    model, variables, changes, statistics = build_model(
        37, cells, minimize_changes=False, hint_reference=True)
    model.Add(changes <= args.radius)
    build_seconds = time.time() - build_started

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = args.workers
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.log_search_progress = False
    solve_started = time.time()
    status = solver.Solve(model)
    solve_seconds = time.time() - solve_started
    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    solution_cells = None
    verification = None
    distance = None
    if feasible:
        solution_cells = tuple(cell for cell, var in variables.items()
                               if solver.Value(var))
        verification = verify(solution_cells, 37)
        distance = int(solver.Value(changes))
    payload = {
        "definition": "exact C4-NTIL feasibility with selected-cell Hamming distance bound",
        "seed_input": str(args.seed_input),
        "seed_objective": seed.get("objective", seed.get("verified_board_total")),
        "radius": args.radius,
        "model_statistics": statistics,
        "build_seconds": build_seconds,
        "status": solver.StatusName(status),
        "feasible": feasible,
        "best_objective_bound": float(solver.BestObjectiveBound()),
        "solve_seconds": solve_seconds,
        "workers": args.workers,
        "distance": distance,
        "solution_cells": ([list(cell) for cell in solution_cells]
                           if solution_cells else None),
        "verification": verification,
        "interpretation": (f"INFEASIBLE proves every C4-NTIL solution has selected-cell "
                           f"distance at least {args.radius + 1} from this seed"),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "radius", "build_seconds", "status", "feasible",
        "best_objective_bound", "solve_seconds", "distance", "verification")}, indent=2))


if __name__ == "__main__":
    main()
