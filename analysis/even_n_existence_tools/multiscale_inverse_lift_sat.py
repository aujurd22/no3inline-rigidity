"""General K-by-K lift of 2K translated modular hyperbola permutations.

For n=Kp and distinct shifts c_0,...,c_{2K-1}, use the base permutations

    f_t(r) = v + a/(r-u) + c_t (mod p),

where the pole is completed in the same way as in ``fibered_mobius_sat``.
There are 2K base occurrences in every residue row and column.  Each
occurrence chooses one of K^2 high-bit labels (alpha,beta).  Balance requires
exactly two occurrences in every high row alpha of each residue row and
exactly two in every high column beta of each residue column.

This is the natural K-scale extension of the exact four-permutation lift
normal form used when K=2.  The base support is algebraic and has only 2Kp
cells, while the high labels retain enough freedom to break modular
collinearities.
"""

from __future__ import annotations

import argparse
import collections
import json
import time

from ortools.sat.python import cp_model

from fibered_mobius_sat import is_prime, mobius_permutation, verify
from nearest_c4_solution_sat import long_grid_lines, parse_cells


Point = tuple[int, int]
Occurrence = tuple[int, int]  # layer, residue row
Key = tuple[int, int, int, int]  # layer, residue, high row, high column


def solve(
    k: int,
    p: int,
    shifts: list[int],
    u: int,
    v: int,
    multiplier: int,
    time_limit: float,
    workers: int,
    seed: int,
    reference_points: set[Point] | None = None,
) -> dict:
    if len(shifts) != 2 * k or len(set(shifts)) != 2 * k:
        raise ValueError("need exactly 2K distinct shifts")
    n = k * p
    base = mobius_permutation(p, u, v, multiplier)
    permutations = [
        [(value + shift) % p for value in base]
        for shift in shifts
    ]

    point_for_key: dict[Key, Point] = {}
    key_for_point: dict[Point, Key] = {}
    for layer, permutation in enumerate(permutations):
        for residue in range(p):
            for high_row in range(k):
                for high_column in range(k):
                    key = (layer, residue, high_row, high_column)
                    point = (
                        residue + high_row * p,
                        permutation[residue] + high_column * p,
                    )
                    if point in key_for_point:
                        raise AssertionError(
                            "distinct shifts unexpectedly shared a base cell"
                        )
                    point_for_key[key] = point
                    key_for_point[point] = key

    model = cp_model.CpModel()
    variables = {
        key: model.new_bool_var(
            f"z_{key[0]}_{key[1]}_{key[2]}_{key[3]}"
        )
        for key in point_for_key
    }
    # Every base occurrence chooses exactly one high-bit label.
    for layer in range(2 * k):
        for residue in range(p):
            model.add(
                sum(
                    variables[(layer, residue, high_row, high_column)]
                    for high_row in range(k)
                    for high_column in range(k)
                )
                == 1
            )

    # Two selected points in every exact row.
    for residue in range(p):
        for high_row in range(k):
            model.add(
                sum(
                    variables[(layer, residue, high_row, high_column)]
                    for layer in range(2 * k)
                    for high_column in range(k)
                )
                == 2
            )

    # Two selected points in every exact column.
    occurrences_by_base_column: dict[int, list[Occurrence]] = {
        column: [] for column in range(p)
    }
    for layer, permutation in enumerate(permutations):
        for residue, column in enumerate(permutation):
            occurrences_by_base_column[column].append((layer, residue))
    if any(len(items) != 2 * k for items in occurrences_by_base_column.values()):
        raise AssertionError("base column degree was not 2K")
    for column, occurrences in occurrences_by_base_column.items():
        for high_column in range(k):
            model.add(
                sum(
                    variables[(layer, residue, high_row, high_column)]
                    for layer, residue in occurrences
                    for high_row in range(k)
                )
                == 2
            )

    hinted_occurrences = 0
    if reference_points:
        reference_by_base_cell: dict[tuple[int, int], list[Point]] = (
            collections.defaultdict(list)
        )
        for point in reference_points:
            reference_by_base_cell[(point[0] % p, point[1] % p)].append(point)
        for layer, permutation in enumerate(permutations):
            for residue, base_column in enumerate(permutation):
                candidates = reference_by_base_cell.get((residue, base_column), [])
                if not candidates:
                    continue
                # If the reference has a repeated base cell, one occurrence in
                # this simple-support model can follow only one of its lifts.
                chosen = min(candidates)
                chosen_label = (chosen[0] // p, chosen[1] // p)
                for high_row in range(k):
                    for high_column in range(k):
                        model.add_hint(
                            variables[(layer, residue, high_row, high_column)],
                            int((high_row, high_column) == chosen_label),
                        )
                hinted_occurrences += 1

    started_lines = time.perf_counter()
    lines, line_statistics = long_grid_lines(n)
    relevant_constraints = 0
    length_histogram: collections.Counter[int] = collections.Counter()
    for line in lines:
        keys = [key_for_point[point] for point in line if point in key_for_point]
        if len(keys) < 3:
            continue
        model.add(sum(variables[key] for key in keys) <= 2)
        relevant_constraints += 1
        length_histogram[len(keys)] += 1
    line_build_seconds = time.perf_counter() - started_lines

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    started_solve = time.perf_counter()
    status = solver.solve(model)
    solve_seconds = time.perf_counter() - started_solve
    result = {
        "k": k,
        "p": p,
        "n": n,
        "shifts": shifts,
        "u": u,
        "v": v,
        "multiplier": multiplier,
        "status": solver.status_name(status),
        "variables": len(variables),
        "occurrences": 2 * k * p,
        "occurrence_constraints": 2 * k * p,
        "row_balance_constraints": k * p,
        "column_balance_constraints": k * p,
        "hinted_occurrences": hinted_occurrences,
        "relevant_line_constraints": relevant_constraints,
        "relevant_line_length_histogram": dict(sorted(length_histogram.items())),
        "all_grid_line_statistics": line_statistics,
        "line_build_seconds": line_build_seconds,
        "solve_seconds": solve_seconds,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected_keys = [
            key for key, variable in variables.items() if solver.value(variable)
        ]
        points = [point_for_key[key] for key in selected_keys]
        result["selected_labels"] = selected_keys
        result["points"] = points
        result["verification"] = verify(points, n)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--shifts", type=int, nargs="*")
    parser.add_argument("--u", type=int, default=0)
    parser.add_argument("--v", type=int, default=0)
    parser.add_argument("--multiplier", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=1800.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--reference",
        help="optional compact '(x,y)...' point set used only as a solver hint",
    )
    args = parser.parse_args()
    if args.k < 2:
        raise SystemExit("k must be at least 2")
    if not is_prime(args.p):
        raise SystemExit("p must be prime")
    if 2 * args.k > args.p:
        raise SystemExit("this simple-support model requires 2K <= p")
    shifts = args.shifts if args.shifts else list(range(2 * args.k))
    shifts = [shift % args.p for shift in shifts]
    reference_points = set(parse_cells(args.reference)) if args.reference else None
    result = solve(
        args.k,
        args.p,
        shifts,
        args.u % args.p,
        args.v % args.p,
        args.multiplier % args.p,
        args.time_limit,
        args.workers,
        args.seed,
        reference_points,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
