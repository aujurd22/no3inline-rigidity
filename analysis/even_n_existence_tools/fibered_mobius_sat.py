"""Exact test of a fibre-over-a-modular-conic construction.

Let n=Kp with p prime.  Choose the permutation of F_p

    f(u) = v,
    f(x) = v + a/(x-u)  (x != u).

Away from the exceptional point (u,v), its graph is a modular hyperbola,
so a modular line meets it in at most two points.  We restrict the n by n
grid to the p fibres

    F_r = {(r+alpha*p, f(r)+beta*p): alpha,beta in [K]}.

In every fibre we select a 2-regular bipartite graph on the K high-row and
K high-column labels.  Consequently every exact row and column of the n-grid
contains exactly two selected points, automatically and independently of the
other fibres.  Euclidean line-capacity constraints then decide whether the
result is an exact 2n-point NTIL configuration.

This is a deliberately narrow exact experiment.  A feasible result is
independently checked; infeasibility only rules out the specified (K,p,u,v,a)
fibre family.
"""

from __future__ import annotations

import argparse
import collections
import json
import time

from ortools.sat.python import cp_model

from nearest_c4_solution_sat import long_grid_lines


Point = tuple[int, int]
Key = tuple[int, int, int]  # residue r, high row alpha, high column beta


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 1
    return True


def mobius_permutation(p: int, u: int, v: int, multiplier: int) -> list[int]:
    result = []
    for x in range(p):
        if x == u:
            result.append(v)
        else:
            inverse = pow((x - u) % p, p - 2, p)
            result.append((v + multiplier * inverse) % p)
    if sorted(result) != list(range(p)):
        raise AssertionError("completed Mobius graph was not a permutation")
    return result


def determinant(first: Point, second: Point, third: Point) -> int:
    return (second[0] - first[0]) * (third[1] - first[1]) - (
        second[1] - first[1]
    ) * (third[0] - first[0])


def verify(points: list[Point], n: int) -> dict:
    distinct = len(set(points)) == len(points)
    rows = collections.Counter(x for x, _ in points)
    columns = collections.Counter(y for _, y in points)
    bad = None
    for first_index, first in enumerate(points):
        directions = {}
        for second_index, second in enumerate(points):
            if first_index == second_index:
                continue
            dx = second[0] - first[0]
            dy = second[1] - first[1]
            divisor = __import__("math").gcd(abs(dx), abs(dy))
            direction = (dx // divisor, dy // divisor)
            if direction[0] < 0 or (
                direction[0] == 0 and direction[1] < 0
            ):
                direction = (-direction[0], -direction[1])
            if direction in directions:
                bad = (
                    first,
                    points[directions[direction]],
                    second,
                )
                break
            directions[direction] = second_index
        if bad:
            break
    return {
        "point_count": len(points),
        "distinct": distinct,
        "all_rows_two": all(rows[row] == 2 for row in range(n)),
        "all_columns_two": all(columns[column] == 2 for column in range(n)),
        "collinear_witness": bad,
        "valid": (
            len(points) == 2 * n
            and distinct
            and all(rows[row] == 2 for row in range(n))
            and all(columns[column] == 2 for column in range(n))
            and bad is None
        ),
    }


def solve(
    k: int,
    p: int,
    u: int,
    v: int,
    multiplier: int,
    time_limit: float,
    workers: int,
    affine_slope: int | None = None,
    supplied_permutation: list[int] | None = None,
    block_fibres: bool = False,
) -> dict:
    n = k * p
    if supplied_permutation is not None:
        if len(supplied_permutation) != p or sorted(supplied_permutation) != list(
            range(p)
        ):
            raise ValueError("supplied base permutation is invalid")
        permutation = supplied_permutation
        base_mode = "supplied_permutation"
    elif affine_slope is None:
        permutation = mobius_permutation(p, u, v, multiplier)
        base_mode = "completed_mobius"
    else:
        permutation = [
            (affine_slope * residue + v) % p for residue in range(p)
        ]
        if sorted(permutation) != list(range(p)):
            raise ValueError("affine slope must be nonzero modulo p")
        base_mode = "affine"
    point_for_key: dict[Key, Point] = {}
    key_for_point: dict[Point, Key] = {}
    for residue in range(p):
        for high_row in range(k):
            for high_column in range(k):
                key = (residue, high_row, high_column)
                if block_fibres:
                    point = (
                        k * residue + high_row,
                        k * permutation[residue] + high_column,
                    )
                else:
                    point = (
                        residue + high_row * p,
                        permutation[residue] + high_column * p,
                    )
                point_for_key[key] = point
                key_for_point[point] = key

    model = cp_model.CpModel()
    variables = {
        key: model.new_bool_var(f"z_{key[0]}_{key[1]}_{key[2]}")
        for key in point_for_key
    }
    for residue in range(p):
        for high_row in range(k):
            model.add(
                sum(
                    variables[(residue, high_row, high_column)]
                    for high_column in range(k)
                )
                == 2
            )
        for high_column in range(k):
            model.add(
                sum(
                    variables[(residue, high_row, high_column)]
                    for high_row in range(k)
                )
                == 2
            )

    started_lines = time.perf_counter()
    lines, line_statistics = long_grid_lines(n)
    relevant_line_constraints = 0
    relevant_length_histogram: collections.Counter[int] = collections.Counter()
    for line in lines:
        keys = [key_for_point[point] for point in line if point in key_for_point]
        if len(keys) < 3:
            continue
        model.add(sum(variables[key] for key in keys) <= 2)
        relevant_line_constraints += 1
        relevant_length_histogram[len(keys)] += 1
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
        "base_mode": base_mode,
        "digit_order": "block_fibres" if block_fibres else "interleaved_fibres",
        "affine_slope": affine_slope,
        "base_permutation": permutation,
        "status": solver.status_name(status),
        "variables": len(variables),
        "degree_constraints": 2 * k * p,
        "relevant_line_constraints": relevant_line_constraints,
        "relevant_line_length_histogram": dict(
            sorted(relevant_length_histogram.items())
        ),
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
        result["fibres"] = {
            str(residue): [
                [high_row, high_column]
                for (r, high_row, high_column), variable in variables.items()
                if r == residue and solver.value(variable)
            ]
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
    parser.add_argument(
        "--affine-slope",
        type=int,
        help="use f(r)=slope*r+v mod p instead of the completed Mobius graph",
    )
    parser.add_argument(
        "--base-permutation",
        type=int,
        nargs="+",
        help="use this explicit permutation; its length defines the base order p",
    )
    parser.add_argument(
        "--block-fibres",
        action="store_true",
        help="use coordinates (k*r+alpha,k*f(r)+beta) instead of interleaving",
    )
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.k < 2:
        raise SystemExit("k must be at least 2")
    if args.base_permutation is None and not is_prime(args.p):
        raise SystemExit("p must be prime")
    if args.multiplier % args.p == 0:
        raise SystemExit("multiplier must be nonzero modulo p")
    result = solve(
        args.k,
        args.p,
        args.u % args.p,
        args.v % args.p,
        args.multiplier % args.p,
        args.time_limit,
        args.workers,
        None if args.affine_slope is None else args.affine_slope % args.p,
        args.base_permutation,
        args.block_fibres,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
