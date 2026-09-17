"""Classify pairwise compatibility in the single-conic fibre model.

Each residue r carries a K by K label grid from which an exact 2K-point
NTIL 2-factor must be selected.  For two residues r,s we ask whether both
fibres can be selected simultaneously without a Euclidean collinear triple.
The modular-conic property makes these pair constraints the dominant local
objects.  Fast pair classification diagnoses whether global infeasibility is
already a two-fibre obstruction or a genuinely higher-order CSP.
"""

from __future__ import annotations

import argparse
import itertools
import json
import time

from ortools.sat.python import cp_model

from fibered_mobius_sat import is_prime, mobius_permutation, verify


Point = tuple[int, int]
Key = tuple[int, int, int]  # residue, high row, high column


def determinant(first: Point, second: Point, third: Point) -> int:
    return (second[0] - first[0]) * (third[1] - first[1]) - (
        second[1] - first[1]
    ) * (third[0] - first[0])


def pair_solve(
    k: int,
    p: int,
    permutation: list[int],
    residues: tuple[int, ...],
    time_limit: float,
) -> dict:
    model = cp_model.CpModel()
    variables = {}
    points = {}
    for residue in residues:
        for high_row in range(k):
            for high_column in range(k):
                key = (residue, high_row, high_column)
                variables[key] = model.new_bool_var(
                    f"z_{residue}_{high_row}_{high_column}"
                )
                points[key] = (
                    residue + high_row * p,
                    permutation[residue] + high_column * p,
                )
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

    constraints = set()
    keys = list(points)
    for triple in itertools.combinations(keys, 3):
        if determinant(*(points[key] for key in triple)) == 0:
            constraints.add(tuple(sorted(triple)))
    for triple in constraints:
        model.add(sum(variables[key] for key in triple) <= 2)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    result = {
        "residues": residues,
        "status": solver.status_name(status),
        "line_triple_constraints": len(constraints),
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected = [
            points[key] for key, variable in variables.items() if solver.value(variable)
        ]
        result["points"] = selected
        result["verification"] = verify(selected, k * p)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--u", type=int, default=0)
    parser.add_argument("--v", type=int, default=0)
    parser.add_argument("--multiplier", type=int, default=1)
    parser.add_argument("--affine-slope", type=int)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--group-size", type=int, default=2)
    args = parser.parse_args()
    if not is_prime(args.p):
        raise SystemExit("p must be prime")
    if args.affine_slope is None:
        permutation = mobius_permutation(
            args.p,
            args.u % args.p,
            args.v % args.p,
            args.multiplier % args.p,
        )
    else:
        slope = args.affine_slope % args.p
        if slope == 0:
            raise SystemExit("affine slope must be nonzero")
        permutation = [
            (slope * residue + args.v) % args.p
            for residue in range(args.p)
        ]
    counts: dict[str, int] = {}
    results = []
    started = time.perf_counter()
    for residues in itertools.combinations(range(args.p), args.group_size):
        result = pair_solve(
            args.k,
            args.p,
            permutation,
            residues,
            args.time_limit,
        )
        results.append(result)
        counts[result["status"]] = counts.get(result["status"], 0) + 1
        print(json.dumps(result), flush=True)
    print(
        json.dumps(
            {
                "summary": True,
                "k": args.k,
                "p": args.p,
                "base_permutation": permutation,
                "status_counts": counts,
                "elapsed_seconds": time.perf_counter() - started,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
