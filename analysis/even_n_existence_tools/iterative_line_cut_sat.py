"""Solve the C4 line-packing model by iterative constraint generation.

The monolithic m=37 model has roughly three hundred thousand distinct C4
line constraints.  This solver starts with heavy directions and all constraints
having a coefficient two, solves the degree-two model, then adds every line
constraint violated by the returned integral candidate.  Every accepted final
candidate is exact because it is checked against the complete line list.
"""

from __future__ import annotations

import argparse
import collections
import json
import time

from ortools.sat.python import cp_model

from nearest_c4_solution_sat import (
    long_grid_lines,
    parse_cells,
    point_cell_map,
    verify,
)


Cell = tuple[int, int]
Signature = tuple[tuple[Cell, int], ...]


def signatures(m: int) -> tuple[dict[Signature, int], dict]:
    n = 2 * m
    point_to_cell = point_cell_map(m)
    lines, line_statistics = long_grid_lines(n)
    result: dict[Signature, int] = {}
    coefficient_histogram: collections.Counter[int] = collections.Counter()
    for points in lines:
        counts: collections.Counter[Cell] = collections.Counter(
            point_to_cell[point] for point in points
        )
        signature = tuple(sorted(counts.items()))
        first, second = points[:2]
        scale = max(
            abs(first[0] - second[0]),
            abs(first[1] - second[1]),
        )
        if signature not in result or scale < result[signature]:
            result[signature] = scale
    for signature in result:
        coefficient_histogram.update(coefficient for _, coefficient in signature)
    return result, {
        **line_statistics,
        "distinct_c4_line_signatures": len(result),
        "coefficient_histogram": dict(sorted(coefficient_histogram.items())),
    }


def add_degree_model(
    m: int,
) -> tuple[cp_model.CpModel, dict[Cell, cp_model.IntVar]]:
    model = cp_model.CpModel()
    variables = {
        (x, y): model.new_bool_var(f"z_{x}_{y}")
        for x in range(m)
        for y in range(m)
    }
    for vertex in range(m):
        terms = []
        for second in range(m):
            terms.append(variables[(vertex, second)])
        for first in range(m):
            terms.append(variables[(first, vertex)])
        model.add(sum(terms) == 2)
    return model, variables


def add_line_constraint(
    model: cp_model.CpModel,
    variables: dict[Cell, cp_model.IntVar],
    signature: Signature,
) -> None:
    model.add(
        sum(coefficient * variables[cell] for cell, coefficient in signature)
        <= 2
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--heavy-scale", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--iteration-time", type=float, default=30.0)
    parser.add_argument("--maximum-iterations", type=int, default=1000)
    parser.add_argument("--total-time", type=float, default=3600.0)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    reference = set(parse_cells(args.reference))
    if len(reference) != args.m:
        raise ValueError("reference must contain m distinct cells")
    all_signatures, statistics = signatures(args.m)
    model, variables = add_degree_model(args.m)
    added: set[Signature] = set()

    for signature, scale in all_signatures.items():
        if scale <= args.heavy_scale or any(
            coefficient == 2 for _, coefficient in signature
        ):
            add_line_constraint(model, variables, signature)
            added.add(signature)

    for cell, variable in variables.items():
        model.add_hint(variable, int(cell in reference))

    print(
        json.dumps(
            {
                "start": True,
                "m": args.m,
                "n": 2 * args.m,
                "initial_constraints": len(added),
                "model_statistics": statistics,
            }
        ),
        flush=True,
    )

    started = time.perf_counter()
    best_violation_count: int | None = None
    best_cells: tuple[Cell, ...] | None = None
    for iteration in range(args.maximum_iterations):
        elapsed = time.perf_counter() - started
        if elapsed >= args.total_time:
            break
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = args.workers
        solver.parameters.max_time_in_seconds = min(
            args.iteration_time,
            args.total_time - elapsed,
        )
        solver.parameters.random_seed = args.seed + iteration
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(
                json.dumps(
                    {
                        "iteration": iteration,
                        "status": solver.status_name(status),
                        "constraints": len(added),
                        "elapsed_seconds": time.perf_counter() - started,
                    }
                ),
                flush=True,
            )
            if status == cp_model.INFEASIBLE:
                break
            continue

        cells = tuple(
            cell
            for cell, variable in variables.items()
            if solver.value(variable)
        )
        selected = set(cells)
        violated = []
        excess = 0
        for signature in all_signatures:
            load = sum(
                coefficient
                for cell, coefficient in signature
                if cell in selected
            )
            if load > 2:
                violated.append(signature)
                excess += load - 2
        if best_violation_count is None or len(violated) < best_violation_count:
            best_violation_count = len(violated)
            best_cells = cells
        print(
            json.dumps(
                {
                    "iteration": iteration,
                    "status": solver.status_name(status),
                    "violated_line_signatures": len(violated),
                    "total_excess": excess,
                    "new_constraints": sum(
                        signature not in added for signature in violated
                    ),
                    "constraints": len(added),
                    "best_violations": best_violation_count,
                    "elapsed_seconds": time.perf_counter() - started,
                }
            ),
            flush=True,
        )
        if not violated:
            result = {
                "found": True,
                "m": args.m,
                "n": 2 * args.m,
                "cells": cells,
                "verification": verify(cells, args.m),
                "iterations": iteration + 1,
                "constraints": len(added),
                "elapsed_seconds": time.perf_counter() - started,
            }
            print(json.dumps(result, indent=2), flush=True)
            return

        new_violations = [
            signature for signature in violated if signature not in added
        ]
        for signature in new_violations:
            add_line_constraint(model, variables, signature)
            added.add(signature)
        if not new_violations:
            raise AssertionError("solver returned a candidate violating an added cut")
        if iteration == 0 and hasattr(model, "clear_hints"):
            model.clear_hints()

    print(
        json.dumps(
            {
                "found": False,
                "m": args.m,
                "best_violations": best_violation_count,
                "best_cells": best_cells,
                "constraints": len(added),
                "elapsed_seconds": time.perf_counter() - started,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
