#!/usr/bin/env python3
"""Exact CP-SAT orientation optimizer for one fixed m=37 undirected factor.

Uses the original per-line weighted constraints.  If a line contains s chosen
lifted points, its objective contribution is C(s,3), so the objective is
exactly Board.verify_total(), not a duplicated 3-CNF proxy.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from pathlib import Path

from ortools.sat.python import cp_model

from solver_theory_m37 import Board
from weighted_prefilter_ab_m37 import exact_line_model


M = 37


def choose_factor(data, group):
    if "groups" in data:
        rows = data["groups"][group]
        return min(rows, key=lambda r: r["exact"]["best_geometric_bad"])
    if "best" in data and "edges" not in data:
        return data["best"]
    return data


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--group", default="raw_prefilter")
    ap.add_argument("--time-limit", type=float, default=120.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, default=here / "results" /
                    "pair_codegree_37" / "exact_orient_candidate_m37.json")
    args = ap.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    row = choose_factor(source, args.group)
    edges = tuple(sorted(tuple(e) for e in row["edges"]))
    hint = (row.get("exact", {}).get("bits") or
            row.get("best", {}).get("bits") or row.get("bits"))
    with (here / "line_cons_m37.pkl").open("rb") as f:
        constraints, incidence = pickle.load(f)
    factors, _, constant = exact_line_model(edges, constraints, incidence)

    model = cp_model.CpModel()
    bits = [model.NewBoolVar(f"b_{i}") for i in range(len(edges))]
    costs = []
    for line_no, options in enumerate(factors):
        maximum = sum(max(w0, w1) for _, w0, w1 in options)
        minimum = sum(min(w0, w1) for _, w0, w1 in options)
        s = model.NewIntVar(minimum, maximum, f"s_{line_no}")
        model.Add(s == sum(w0 + (w1 - w0) * bits[e]
                           for e, w0, w1 in options))
        max_cost = math.comb(maximum, 3) if maximum >= 3 else 0
        c = model.NewIntVar(0, max_cost, f"c_{line_no}")
        model.AddAllowedAssignments([s, c], [
            (value, math.comb(value, 3) if value >= 3 else 0)
            for value in range(minimum, maximum + 1)
        ])
        costs.append(c)
    model.Minimize(sum(costs))
    if hint and len(hint) == len(bits):
        for var, value in zip(bits, hint):
            model.AddHint(var, int(value))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.num_search_workers = args.workers
    solver.parameters.log_search_progress = False
    began = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - began
    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    solution = [int(solver.Value(v)) for v in bits] if feasible else None
    cells = None
    verified = None
    if solution is not None:
        cells = [(v, u) if bit else (u, v)
                 for (u, v), bit in zip(edges, solution)]
        board = Board(M)
        board.build(edges, cells)
        verified = board.verify_total()
    payload = {
        "source": str(args.input), "source_group": args.group,
        "edges": edges,
        "source_sa_bad": (row.get("exact", {}).get("best_geometric_bad") or
                          row.get("best", {}).get("cost")),
        "relevant_lines": len(factors), "constant_bad": constant,
        "status": solver.StatusName(status), "optimal": status == cp_model.OPTIMAL,
        "objective": int(round(solver.ObjectiveValue())) if feasible else None,
        "best_bound": float(solver.BestObjectiveBound()),
        "verified_board_total": verified, "bits": solution, "cells": cells,
        "wall_seconds": elapsed, "workers": args.workers,
    }
    if feasible and payload["objective"] != verified:
        raise AssertionError(f"CP objective {payload['objective']} != Board {verified}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in
                      ("status", "optimal", "objective", "best_bound",
                       "verified_board_total", "wall_seconds")}, indent=2))


if __name__ == "__main__":
    main()
