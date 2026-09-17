#!/usr/bin/env python3
"""Describe the exact conflict core of a certified m=37 rot4 factor."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import pickle
from collections import Counter, defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from solver_theory_m37 import Board, c4, line_of
from weighted_prefilter_ab_m37 import exact_line_model, line_cost


M = 37
N = 74


def rotate_line(signature, points, rotation):
    p, q = points[:2]
    return line_of(c4(*p, rotation, N), c4(*q, rotation, N))


def minimum_hitting_set(edge_sets, edge_count):
    model = cp_model.CpModel()
    take = [model.NewBoolVar(f"take_{i}") for i in range(edge_count)]
    for edge_set in edge_sets:
        model.Add(sum(take[i] for i in edge_set) >= 1)
    model.Minimize(sum(take))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    return {
        "size": int(round(solver.ObjectiveValue())),
        "edge_indices": [i for i, var in enumerate(take) if solver.Value(var)],
        "optimal": status == cp_model.OPTIMAL,
    }


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=here / "results" /
                    "pair_codegree_37" / "exact60_conflict_core.json")
    args = ap.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    edges = tuple(map(tuple, source["edges"]))
    bits = list(map(int, source["bits"]))
    cells = [(v, u) if bit else (u, v) for (u, v), bit in zip(edges, bits)]
    board = Board(M)
    board.build(edges, cells)
    verified = board.verify_total()

    bad_lines = []
    orbit_groups = defaultdict(list)
    incidence = Counter()
    conflict_edge_sets = set()
    for signature, point_counts in board.line_pts.items():
        point_ids = sorted(point_counts)
        if len(point_ids) < 3:
            continue
        points = [board.lifts[i] for i in point_ids]
        contribution = math.comb(len(points), 3)
        edge_ids = sorted({i >> 2 for i in point_ids})
        for edge_id in edge_ids:
            incidence[edge_id] += contribution
        for triple in itertools.combinations(point_ids, 3):
            conflict_edge_sets.add(tuple(sorted({i >> 2 for i in triple})))
        orbit = tuple(sorted(rotate_line(signature, points, r) for r in range(4)))
        orbit_key = orbit[0]
        row = {
            "signature": list(signature),
            "points": [list(point) for point in points],
            "point_ids": point_ids,
            "edge_indices": edge_ids,
            "edges": [list(edges[i]) for i in edge_ids],
            "point_count": len(points),
            "contribution": contribution,
        }
        bad_lines.append(row)
        orbit_groups[orbit_key].append(row)

    with (here / "line_cons_m37.pkl").open("rb") as handle:
        constraints, cell_incidence = pickle.load(handle)
    factors, _occurrence, constant = exact_line_model(edges, constraints, cell_incidence)
    base_cost = sum(line_cost(sum(w1 if bits[e] else w0
                                  for e, w0, w1 in options))
                    for options in factors)
    flip_deltas = []
    for edge in range(len(edges)):
        flipped = bits.copy()
        flipped[edge] ^= 1
        cost = sum(line_cost(sum(w1 if flipped[e] else w0
                                 for e, w0, w1 in options))
                   for options in factors)
        flip_deltas.append({
            "edge_index": edge,
            "edge": list(edges[edge]),
            "delta": int(cost - base_cost),
            "cost": int(cost),
        })

    cover = minimum_hitting_set(conflict_edge_sets, len(edges))
    if cover:
        cover["edges"] = [list(edges[i]) for i in cover["edge_indices"]]
    payload = {
        "input": str(args.input),
        "verified_board_total": int(verified),
        "bad_line_count": len(bad_lines),
        "bad_line_size_histogram": dict(sorted(Counter(
            row["point_count"] for row in bad_lines).items())),
        "line_orbit_count": len(orbit_groups),
        "line_orbit_sizes": sorted(len(rows) for rows in orbit_groups.values()),
        "distinct_conflict_edge_sets": len(conflict_edge_sets),
        "minimum_edge_hitting_set": cover,
        "edge_conflict_incidence": [
            {"edge_index": i, "edge": list(edges[i]), "weight": incidence[i]}
            for i in sorted(range(len(edges)), key=lambda i: (-incidence[i], i))
        ],
        "single_orientation_flip_deltas": sorted(flip_deltas, key=lambda row: row["delta"]),
        "bad_lines": bad_lines,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "verified_board_total", "bad_line_count", "bad_line_size_histogram",
        "line_orbit_count", "line_orbit_sizes", "distinct_conflict_edge_sets",
        "minimum_edge_hitting_set")}, indent=2))
    print("lowest flip deltas:")
    print(json.dumps(payload["single_orientation_flip_deltas"][:10], indent=2))


if __name__ == "__main__":
    main()
