"""Lift four permutations of F_p to an exact NTIL candidate on a 2p grid.

The reduction modulo p of any 4p-point extremal configuration on a 2p x 2p
grid is a 4-regular bipartite multigraph on base rows and base columns.
Conversely, start with four base permutations f_0,...,f_3.  For every base
edge (x,f_i(x)), choose a row bit r_{i,x} and a column bit c_{i,x}, producing

    (x + p*r_{i,x}, f_i(x) + p*c_{i,x}).

Requiring two 0-bits and two 1-bits at each base row and column gives exactly
two points in every lifted row and column.  All remaining forbidden patterns
are exact integer collinearities.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from dataclasses import dataclass

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class Edge:
    layer: int
    x: int
    y: int


def inverse_permutation(p: int) -> list[int]:
    return [0] + [pow(x, -1, p) for x in range(1, p)]


def collinear(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> bool:
    return (b[0] - a[0]) * (c[1] - a[1]) == (b[1] - a[1]) * (c[0] - a[0])


def verify(points: list[tuple[int, int]], n: int) -> dict:
    rows = [0] * n
    cols = [0] * n
    for x, y in points:
        rows[x] += 1
        cols[y] += 1
    bad = []
    for triple in itertools.combinations(points, 3):
        if collinear(*triple):
            bad.append(triple)
            if len(bad) == 10:
                break
    return {
        "point_count": len(points),
        "unique_count": len(set(points)),
        "rows_exactly_two": all(v == 2 for v in rows),
        "cols_exactly_two": all(v == 2 for v in cols),
        "collinear_triples_sample": bad,
        "valid": (
            len(points) == 2 * n
            and len(set(points)) == 2 * n
            and all(v == 2 for v in rows)
            and all(v == 2 for v in cols)
            and not bad
        ),
    }


def solve(
    p: int,
    permutations: list[list[int]],
    time_limit: float,
    workers: int,
) -> dict:
    if len(permutations) != 4:
        raise ValueError("exactly four base permutations are required")
    if any(sorted(f) != list(range(p)) for f in permutations):
        raise ValueError("every base layer must be a permutation")

    edges = [
        Edge(layer=i, x=x, y=permutations[i][x])
        for i in range(4)
        for x in range(p)
    ]
    model = cp_model.CpModel()
    row_bit = {
        (edge.layer, edge.x): model.new_bool_var(f"r_{edge.layer}_{edge.x}")
        for edge in edges
    }
    col_bit = {
        (edge.layer, edge.x): model.new_bool_var(f"c_{edge.layer}_{edge.x}")
        for edge in edges
    }

    # Exactly two points go to each of the two lifted rows over x.
    for x in range(p):
        model.add(sum(row_bit[(i, x)] for i in range(4)) == 2)

    # Exactly two points go to each of the two lifted columns over y.
    for y in range(p):
        incident = [
            col_bit[(edge.layer, edge.x)]
            for edge in edges
            if edge.y == y
        ]
        model.add(sum(incident) == 2)

    # Parallel base edges must receive distinct bit pairs.
    by_base: dict[tuple[int, int], list[Edge]] = {}
    for edge in edges:
        by_base.setdefault((edge.x, edge.y), []).append(edge)
    for parallel in by_base.values():
        for e1, e2 in itertools.combinations(parallel, 2):
            k1 = (e1.layer, e1.x)
            k2 = (e2.layer, e2.x)
            # Not (r1=r2 and c1=c2), encoded by forbidding all four equal pairs.
            for rv, cv in itertools.product((0, 1), repeat=2):
                literals = [
                    row_bit[k1].Not() if rv else row_bit[k1],
                    row_bit[k2].Not() if rv else row_bit[k2],
                    col_bit[k1].Not() if cv else col_bit[k1],
                    col_bit[k2].Not() if cv else col_bit[k2],
                ]
                model.add_bool_or(literals)

    modular_triples = 0
    forbidden_patterns = 0
    for triple in itertools.combinations(edges, 3):
        det_mod = (
            (triple[1].x - triple[0].x) * (triple[2].y - triple[0].y)
            - (triple[1].y - triple[0].y) * (triple[2].x - triple[0].x)
        ) % p
        if det_mod:
            continue
        modular_triples += 1

        keys = sorted({(edge.layer, edge.x) for edge in triple})
        bit_keys = [(kind, key) for key in keys for kind in (0, 1)]
        for values in itertools.product((0, 1), repeat=len(bit_keys)):
            assignment = dict(zip(bit_keys, values))
            points = [
                (
                    edge.x + p * assignment[(0, (edge.layer, edge.x))],
                    edge.y + p * assignment[(1, (edge.layer, edge.x))],
                )
                for edge in triple
            ]
            if not collinear(*points):
                continue
            literals = []
            for (kind, key), value in zip(bit_keys, values):
                var = row_bit[key] if kind == 0 else col_bit[key]
                literals.append(var.Not() if value else var)
            model.add_bool_or(literals)
            forbidden_patterns += 1

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    started = time.perf_counter()
    status = solver.solve(model)
    elapsed = time.perf_counter() - started
    result = {
        "p": p,
        "n": 2 * p,
        "status": solver.status_name(status),
        "elapsed_seconds": elapsed,
        "modular_triples": modular_triples,
        "forbidden_boolean_patterns": forbidden_patterns,
        "branches": solver.num_branches,
        "conflicts": solver.num_conflicts,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        points = [
            (
                edge.x + p * solver.value(row_bit[(edge.layer, edge.x)]),
                edge.y + p * solver.value(col_bit[(edge.layer, edge.x)]),
            )
            for edge in edges
        ]
        result["points"] = points
        result["row_bits"] = [
            [solver.value(row_bit[(i, x)]) for x in range(p)]
            for i in range(4)
        ]
        result["col_bits"] = [
            [solver.value(col_bit[(i, x)]) for x in range(p)]
            for i in range(4)
        ]
        result["verification"] = verify(points, 2 * p)
    return result


def is_prime(p: int) -> bool:
    if p < 2:
        return False
    return all(p % d for d in range(2, math.isqrt(p) + 1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument(
        "--shifts",
        type=int,
        nargs=4,
        default=(0, 1, 2, 3),
        metavar=("S0", "S1", "S2", "S3"),
    )
    parser.add_argument("--time-limit", type=float, default=120.0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not is_prime(args.p):
        raise SystemExit("p must be prime")
    inv = inverse_permutation(args.p)
    permutations = [
        [(value + shift) % args.p for value in inv]
        for shift in args.shifts
    ]
    result = solve(args.p, permutations, args.time_limit, args.workers)
    result["shifts"] = args.shifts
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
