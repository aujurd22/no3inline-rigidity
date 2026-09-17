#!/usr/bin/env python3
"""Exhaust every 2-switch neighbour using orientations inherited from a seed.

For each legal one-switch factor, keep every unchanged edge orientation, try
all four orientations of the two new edges, and run exact steepest descent on
the true per-line objective sum C(s, 3).  This is a complete audit of this
specific inherited-orientation descent channel, not a proof of the globally
optimal orientation of every neighbouring factor.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from pathlib import Path

import numpy as np

from one_switch_landscape_m37 import all_one_switches
from solver_theory_m37 import Board
from weighted_prefilter_ab_m37 import exact_line_model, line_cost


M = 37


def prepare_descent(edges, constraints, incidence):
    factors, _occurrence, constant = exact_line_model(edges, constraints, incidence)
    effects = [[] for _ in edges]
    for fidx, options in enumerate(factors):
        for edge, w0, w1 in options:
            if w0 != w1:
                effects[edge].append((fidx, w1 - w0))
    return factors, effects, constant


def exact_descent(initial_bits, prepared):
    factors, effects, constant = prepared
    bits = np.asarray(initial_bits, dtype=np.int8).copy()
    sums = np.asarray([
        sum(w1 if bits[edge] else w0 for edge, w0, w1 in options)
        for options in factors
    ], dtype=np.int16)
    cost = int(sum(line_cost(int(value)) for value in sums))
    initial_cost = cost
    flips = []
    while True:
        best_delta = 0
        best_edge = None
        for edge in range(len(effects)):
            sign = 1 if bits[edge] == 0 else -1
            delta = 0
            for fidx, effect in effects[edge]:
                before = int(sums[fidx])
                after = before + sign * effect
                delta += line_cost(after) - line_cost(before)
            if delta < best_delta:
                best_delta = delta
                best_edge = edge
        if best_edge is None:
            break
        sign = 1 if bits[best_edge] == 0 else -1
        bits[best_edge] ^= 1
        cost += best_delta
        for fidx, effect in effects[best_edge]:
            sums[fidx] += sign * effect
        flips.append(best_edge)
    return {
        "initial": initial_cost,
        "cost": int(cost),
        "bits": bits.tolist(),
        "flips": flips,
        "relevant_lines": len(factors),
        "constant_bad": int(constant),
    }


def inherited_starts(parent_edges, parent_bits, child_edges):
    orientation = {edge: bit for edge, bit in zip(parent_edges, parent_bits)}
    new_indices = [i for i, edge in enumerate(child_edges) if edge not in orientation]
    if len(new_indices) != 2:
        raise AssertionError(f"expected two new edges, got {len(new_indices)}")
    for mask in range(4):
        bits = [orientation.get(edge, 0) for edge in child_edges]
        bits[new_indices[0]] = mask & 1
        bits[new_indices[1]] = (mask >> 1) & 1
        yield mask, bits


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--seed-input", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=here / "results" /
                    "pair_codegree_37" / "exhaustive_inherited_from60_m37.json")
    args = ap.parse_args()
    began = time.time()
    source = json.loads(args.seed_input.read_text(encoding="utf-8"))
    parent_edges = tuple(sorted(tuple(edge) for edge in source["edges"]))
    source_bit_by_edge = {
        tuple(edge): int(bit) for edge, bit in zip(source["edges"], source["bits"])
    }
    parent_bits = [source_bit_by_edge[edge] for edge in parent_edges]
    with (here / "line_cons_m37.pkl").open("rb") as handle:
        constraints, incidence = pickle.load(handle)

    rows = []
    best = None
    partial_path = args.out.with_suffix(".partial.json")
    for number, (edges, removed, added) in enumerate(all_one_switches(parent_edges), 1):
        prepared = prepare_descent(edges, constraints, incidence)
        starts = []
        for mask, bits in inherited_starts(parent_edges, parent_bits, edges):
            result = exact_descent(bits, prepared)
            starts.append({"new_edge_mask": mask, **result})
        local = min(starts, key=lambda row: row["cost"])
        row = {
            "edges": [list(edge) for edge in edges],
            "removed": removed,
            "added": added,
            "best": local,
            "start_costs": [entry["initial"] for entry in starts],
            "descent_costs": [entry["cost"] for entry in starts],
        }
        rows.append(row)
        if best is None or local["cost"] < best["best"]["cost"]:
            best = row
        if number % 100 == 0:
            print(f"  audited {number}; best={best['best']['cost']}", flush=True)
        if number % 250 == 0:
            partial_path.parent.mkdir(parents=True, exist_ok=True)
            partial_path.write_text(json.dumps({
                "completed": number,
                "best": best,
                "rows": rows,
            }, indent=2), encoding="utf-8")

    costs = np.asarray([row["best"]["cost"] for row in rows], dtype=int)
    best_edges = tuple(map(tuple, best["edges"]))
    best_bits = best["best"]["bits"]
    cells = [(v, u) if bit else (u, v)
             for (u, v), bit in zip(best_edges, best_bits)]
    board = Board(M)
    board.build(best_edges, cells)
    verified = board.verify_total()
    if verified != best["best"]["cost"]:
        raise AssertionError(f"line model {best['best']['cost']} != Board {verified}")

    payload = {
        "definition": "complete one-switch inherited-orientation steepest-descent audit",
        "scope_warning": "complete for four inherited starts per neighbour; not global orientation optimization",
        "seed_input": str(args.seed_input),
        "seed_objective": source.get("objective", source.get("verified_board_total")),
        "pool_size": len(rows),
        "summary": {
            "best": int(costs.min()),
            "median": float(np.median(costs)),
            "mean": float(costs.mean()),
            "at_most_seed": int(np.sum(costs <= source.get("objective", 60))),
            "below_seed": int(np.sum(costs < source.get("objective", 60))),
        },
        "best": best,
        "best_cells": [list(cell) for cell in cells],
        "verified_board_total": int(verified),
        "rows": rows,
        "seconds": time.time() - began,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "pool_size": payload["pool_size"],
        "summary": payload["summary"],
        "verified_board_total": payload["verified_board_total"],
        "best_removed": best["removed"],
        "best_added": best["added"],
        "seconds": payload["seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
