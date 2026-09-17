#!/usr/bin/env python3
"""Enumerate only FDR-feasible matchings at an exact switch distance."""

from __future__ import annotations

import argparse
import itertools
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from directed_cell_lns import directed_cell
from matching_orientation_probe import matching_key, solve_orientation
from signed_nae_core import c4_lifts


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def build_master(
    base,
    removed_indices,
    distance,
    partition_parts=1,
    partition_index=0,
):
    edges = [tuple(edge) for edge in base["edges"]]
    bits = list(base["bits"])
    removed = set(removed_indices)
    fixed_indices = [index for index in range(37) if index not in removed]
    fixed_edges = {tuple(sorted(edges[index])) for index in fixed_indices}
    original_matching = matching_key(edges[index] for index in removed_indices)
    affected = sorted(vertex for edge in original_matching for vertex in edge)

    cells = []
    edge_to_cells = defaultdict(list)
    for u, v in itertools.combinations(affected, 2):
        edge = (u, v)
        if edge in fixed_edges:
            continue
        for cell in ((u, v), (v, u)):
            cell_index = len(cells)
            cells.append(cell)
            edge_to_cells[edge].append(cell_index)

    model = cp_model.CpModel()
    selected = [model.NewBoolVar(f"cell_{u}_{v}") for u, v in cells]
    for edge, indices in edge_to_cells.items():
        model.Add(sum(selected[index] for index in indices) <= 1)
    for vertex in affected:
        model.Add(
            sum(
                selected[index]
                for index, (u, v) in enumerate(cells)
                if vertex == u or vertex == v
            )
            == 1
        )

    partition = None
    if partition_parts > 1:
        branch_vertex = affected[0]
        partner_edges = sorted(edge for edge in edge_to_cells if branch_vertex in edge)
        groups = [
            partner_edges[index::partition_parts] for index in range(partition_parts)
        ]
        if not (0 <= partition_index < partition_parts):
            raise ValueError("partition index must be in 0..partition_parts-1")
        if not groups[partition_index]:
            raise ValueError("selected partition is empty")
        model.Add(
            sum(
                selected[cell_index]
                for edge in groups[partition_index]
                for cell_index in edge_to_cells[edge]
            )
            == 1
        )
        partition = {
            "vertex": branch_vertex,
            "parts": partition_parts,
            "index": partition_index,
            "all_partner_count": len(partner_edges),
            "partner_edges": [list(edge) for edge in groups[partition_index]],
        }

    fixed_cells = [directed_cell(edges[index], bits[index]) for index in fixed_indices]
    fixed_points = [point for cell in fixed_cells for point in c4_lifts(37, cell)]
    variable_points = [c4_lifts(37, cell) for cell in cells]
    fixed_plus = Counter(x - y for x, y in fixed_points)
    fixed_minus = Counter(x + y for x, y in fixed_points)
    variable_plus = defaultdict(Counter)
    variable_minus = defaultdict(Counter)
    for index, orbit in enumerate(variable_points):
        for x, y in orbit:
            variable_plus[x - y][index] += 1
            variable_minus[x + y][index] += 1
    for fixed, variable in ((fixed_plus, variable_plus), (fixed_minus, variable_minus)):
        for key in set(fixed) | set(variable):
            model.Add(
                fixed.get(key, 0)
                + sum(count * selected[index] for index, count in variable[key].items())
                <= 2
            )

    retained = [
        selected[cell_index]
        for edge in original_matching
        for cell_index in edge_to_cells[edge]
    ]
    model.Add(sum(retained) == len(original_matching) - distance)
    return model, selected, cells, edge_to_cells, original_matching, partition


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="v40_02")
    parser.add_argument(
        "--indices", default="2,5,7,8,11,13,16,18,20,24,26,29,32"
    )
    parser.add_argument("--distance", type=int, default=2)
    parser.add_argument("--max-matchings", type=int, default=100000)
    parser.add_argument("--master-time-limit", type=float, default=10.0)
    parser.add_argument("--orientation-time-limit", type=float, default=1.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--partition-parts", type=int, default=1)
    parser.add_argument("--partition-index", type=int, default=0)
    parser.add_argument("--out", default="matching_master_enumerate.json")
    args = parser.parse_args()
    if args.partition_parts < 1:
        parser.error("--partition-parts must be positive")
    if not 0 <= args.partition_index < args.partition_parts:
        parser.error("--partition-index must be in 0..partition-parts-1")

    archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    removed_indices = tuple(sorted(int(item) for item in args.indices.split(",")))
    model, selected, cells, edge_to_cells, original_matching, partition = build_master(
        base,
        removed_indices,
        args.distance,
        args.partition_parts,
        args.partition_index,
    )

    payload = {
        "parameters": vars(args),
        "removed_indices": list(removed_indices),
        "original_matching": [list(edge) for edge in original_matching],
        "partition": partition,
        "runs": [],
        "objective_histogram": {},
        "best_candidate": None,
        "enumeration_closed": False,
        "final_master_status": None,
    }
    histogram = Counter()
    best_value = None
    out_path = OUT / args.out
    started = time.time()

    for enumeration_index in range(args.max_matchings):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = args.master_time_limit
        solver.parameters.num_search_workers = args.workers
        solver.parameters.random_seed = (
            20260717 + 100000 * args.partition_index + enumeration_index
        )
        solve_started = time.time()
        status = solver.Solve(model)
        master_s = time.time() - solve_started
        status_name = solver.StatusName(status)
        payload["final_master_status"] = status_name
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            payload["enumeration_closed"] = status == cp_model.INFEASIBLE
            break

        matching = matching_key(
            tuple(sorted(cells[index]))
            for index, var in enumerate(selected)
            if solver.Value(var)
        )
        if len(matching) != 13:
            raise AssertionError("master did not return a 13-edge matching")
        orientation = solve_orientation(
            base,
            removed_indices,
            matching,
            args.orientation_time_limit,
            args.workers,
        )
        if orientation["objective"] is None:
            raise AssertionError("master matching failed the orientation subproblem")
        value = orientation["objective"]
        histogram[str(value)] += 1
        record = {
            "enumeration_index": enumeration_index,
            "master_s": round(master_s, 4),
            **orientation,
        }
        payload["runs"].append(record)
        if best_value is None or value < best_value:
            best_value = value
            payload["best_candidate"] = record
            print(
                f"best index={enumeration_index} objective={value} "
                f"matching_count={len(payload['runs'])}",
                flush=True,
            )

        model.Add(
            sum(
                selected[cell_index]
                for edge in matching
                for cell_index in edge_to_cells[edge]
            )
            <= 12
        )
        payload["objective_histogram"] = dict(sorted(histogram.items()))
        payload["matching_count"] = len(payload["runs"])
        payload["elapsed_s"] = round(time.time() - started, 3)
        if (
            args.checkpoint_every > 0
            and len(payload["runs"]) % args.checkpoint_every == 0
        ):
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(
                f"count={len(payload['runs'])} best={best_value} "
                f"elapsed={payload['elapsed_s']}s",
                flush=True,
            )

    payload["objective_histogram"] = dict(sorted(histogram.items()))
    payload["matching_count"] = len(payload["runs"])
    payload["elapsed_s"] = round(time.time() - started, 3)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"done count={payload['matching_count']} closed={payload['enumeration_closed']} "
        f"status={payload['final_master_status']} elapsed={payload['elapsed_s']}s",
        flush=True,
    )
    print(out_path)


if __name__ == "__main__":
    main()
