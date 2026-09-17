"""Exact two-conic fibre construction on an n=Kp grid.

Take two disjoint completed modular hyperbola permutations

    f_0(x) = v + a/(x-u),  f_1(x) = f_0(x) + shift  (mod p),

with the pole completed by f_i(u)=v+i*shift.  Above every base cell
(r,f_i(r)) we select a perfect matching between the K high-row and K
high-column labels.  Thus each of the two fibres contributes one point to
every exact row and one point to every exact column; their union has exactly
2n points and row/column saturation is automatic.

The remaining constraints are precisely Euclidean line capacities.  This
tests a new algebraic family; it does not assume C4 symmetry.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import time

from ortools.sat.python import cp_model

from fibered_mobius_sat import is_prime, mobius_permutation, verify
from nearest_c4_solution_sat import long_grid_lines


Point = tuple[int, int]
Key = tuple[int, int, int, int]  # layer, residue, high row, high column


def solve(
    k: int,
    p: int,
    u: int,
    v: int,
    multiplier: int,
    shift: int,
    time_limit: float,
    workers: int,
    global_degree_only: bool = False,
) -> dict:
    n = k * p
    first = mobius_permutation(p, u, v, multiplier)
    second = [(value + shift) % p for value in first]
    permutations = [first, second]
    if any(first[row] == second[row] for row in range(p)):
        raise ValueError("the two base graphs are not disjoint")

    point_for_key: dict[Key, Point] = {}
    keys_for_point: dict[Point, list[Key]] = collections.defaultdict(list)
    for layer, permutation in enumerate(permutations):
        for residue in range(p):
            for high_row in range(k):
                for high_column in range(k):
                    key = (layer, residue, high_row, high_column)
                    point = (
                        residue + high_row * p,
                        permutation[residue] + high_column * p,
                    )
                    point_for_key[key] = point
                    keys_for_point[point].append(key)
    if any(len(keys) != 1 for keys in keys_for_point.values()):
        raise AssertionError("disjoint base graphs unexpectedly shared exact points")

    model = cp_model.CpModel()
    variables = {
        key: model.new_bool_var(
            f"z_{key[0]}_{key[1]}_{key[2]}_{key[3]}"
        )
        for key in point_for_key
    }
    if global_degree_only:
        # Allow the two base fibres in a residue row/column to exchange load.
        # This keeps exact row/column degree two but removes the stronger
        # requirement that each individual fibre be a perfect matching.
        for residue_row in range(p):
            for high_row in range(k):
                model.add(
                    sum(
                        variables[(layer, residue_row, high_row, high_column)]
                        for layer in range(2)
                        for high_column in range(k)
                    )
                    == 2
                )
        inverse_rows = [
            {
                column: next(
                    row for row, value in enumerate(permutation) if value == column
                )
                for column in range(p)
            }
            for permutation in permutations
        ]
        for residue_column in range(p):
            for high_column in range(k):
                model.add(
                    sum(
                        variables[
                            (
                                layer,
                                inverse_rows[layer][residue_column],
                                high_row,
                                high_column,
                            )
                        ]
                        for layer in range(2)
                        for high_row in range(k)
                    )
                    == 2
                )
    else:
        # Each base-cell fibre is a perfect matching on the high labels.
        for layer in range(2):
            for residue in range(p):
                for high_row in range(k):
                    model.add(
                        sum(
                            variables[(layer, residue, high_row, high_column)]
                            for high_column in range(k)
                        )
                        == 1
                    )
                for high_column in range(k):
                    model.add(
                        sum(
                            variables[(layer, residue, high_row, high_column)]
                            for high_row in range(k)
                        )
                        == 1
                    )

    started_lines = time.perf_counter()
    lines, line_statistics = long_grid_lines(n)
    relevant_constraints = 0
    length_histogram: collections.Counter[int] = collections.Counter()
    point_to_key = {point: keys[0] for point, keys in keys_for_point.items()}
    for line in lines:
        keys = [point_to_key[point] for point in line if point in point_to_key]
        if len(keys) < 3:
            continue
        model.add(sum(variables[key] for key in keys) <= 2)
        relevant_constraints += 1
        length_histogram[len(keys)] += 1
    line_build_seconds = time.perf_counter() - started_lines

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    started_solve = time.perf_counter()
    status = solver.solve(model)
    solve_seconds = time.perf_counter() - started_solve
    result = {
        "k": k,
        "p": p,
        "n": n,
        "u": u,
        "v": v,
        "multiplier": multiplier,
        "shift": shift,
        "global_degree_only": global_degree_only,
        "base_permutations": permutations,
        "status": solver.status_name(status),
        "variables": len(variables),
        "degree_constraints": 2 * k * p if global_degree_only else 4 * k * p,
        "relevant_line_constraints": relevant_constraints,
        "relevant_line_length_histogram": dict(sorted(length_histogram.items())),
        "all_grid_line_statistics": line_statistics,
        "line_build_seconds": line_build_seconds,
        "solve_seconds": solve_seconds,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        points = [
            point_for_key[key]
            for key, variable in variables.items()
            if solver.value(variable)
        ]
        result["points"] = points
        result["fibre_permutations"] = {
            f"{layer}:{residue}": [
                high_column
                for high_row in range(k)
                for high_column in range(k)
                if solver.value(
                    variables[(layer, residue, high_row, high_column)]
                )
            ]
            for layer in range(2)
            for residue in range(p)
        }
        result["verification"] = verify(points, n)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--u", type=int, default=0)
    parser.add_argument("--v", type=int, default=0)
    parser.add_argument("--multiplier", type=int, default=1)
    parser.add_argument("--shift", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--global-degree-only", action="store_true")
    args = parser.parse_args()
    if args.k < 2:
        raise SystemExit("k must be at least 2")
    if not is_prime(args.p):
        raise SystemExit("p must be prime")
    if args.multiplier % args.p == 0 or args.shift % args.p == 0:
        raise SystemExit("multiplier and shift must be nonzero modulo p")
    result = solve(
        args.k,
        args.p,
        args.u % args.p,
        args.v % args.p,
        args.multiplier % args.p,
        args.shift % args.p,
        args.time_limit,
        args.workers,
        args.global_degree_only,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
