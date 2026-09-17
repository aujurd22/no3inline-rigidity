"""Select an exact NTIL 2-factor from K modular-hyperbola layers.

The candidate cells on the n=p-1 board are

    X_A = {(x-1,y-1): x*y mod p belongs to A},

where A is a set of K nonzero residues.  X_A is the disjoint union of K
permutation hyperbolas and is K-regular in rows and columns.  This exact
line-packing model selects two cells in each row/column and at most two cells
on every Euclidean line.
"""

from __future__ import annotations

import argparse
import itertools
import json
import time

from ortools.sat.python import cp_model

from three_hyperbola_cover_sat import rich_lines, verify


Point = tuple[int, int]


def candidate_points(p: int, multipliers: tuple[int, ...]) -> set[Point]:
    points: set[Point] = set()
    for multiplier in multipliers:
        for residue_x in range(1, p):
            residue_y = multiplier * pow(residue_x, -1, p) % p
            points.add((residue_x - 1, residue_y - 1))
    expected = len(multipliers) * (p - 1)
    if len(points) != expected:
        raise ValueError("multipliers must be distinct and nonzero modulo p")
    return points


def solve(
    p: int,
    multipliers: tuple[int, ...],
    workers: int,
    time_limit: float,
    seed: int,
    symmetry: str = "none",
) -> dict:
    n = p - 1
    points = candidate_points(p, multipliers)
    started = time.perf_counter()
    lines = rich_lines(points)
    build_seconds = time.perf_counter() - started

    model = cp_model.CpModel()
    selected = {
        point: model.new_bool_var(f"x_{point[0]}_{point[1]}") for point in points
    }
    rows: list[list[Point]] = [[] for _ in range(n)]
    columns: list[list[Point]] = [[] for _ in range(n)]
    for point in points:
        rows[point[0]].append(point)
        columns[point[1]].append(point)
    for row in rows:
        model.add(sum(selected[point] for point in row) == 2)
    for column in columns:
        model.add(sum(selected[point] for point in column) == 2)
    for line in lines:
        model.add(sum(selected[point] for point in line) <= 2)
    if symmetry == "c2":
        for point in points:
            rotated = (n - 1 - point[0], n - 1 - point[1])
            if rotated not in selected:
                raise AssertionError("hyperbola-layer candidate is not C2-invariant")
            if point < rotated:
                model.add(selected[point] == selected[rotated])
    elif symmetry != "none":
        raise ValueError(f"unknown symmetry mode {symmetry}")

    # Hint with the first two complete layers.
    hint_multipliers = set(multipliers[:2])
    for point, variable in selected.items():
        residue_product = ((point[0] + 1) * (point[1] + 1)) % p
        model.add_hint(variable, int(residue_product in hint_multipliers))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    status = solver.solve(model)
    result = {
        "p": p,
        "n": n,
        "layer_count": len(multipliers),
        "multipliers": multipliers,
        "symmetry": symmetry,
        "status": solver.status_name(status),
        "candidate_points": len(points),
        "rich_lines": len(lines),
        "rich_line_size_histogram": {
            size: sum(len(line) == size for line in lines)
            for size in sorted({len(line) for line in lines})
        },
        "line_build_seconds": build_seconds,
        "solve_wall_seconds": solver.wall_time,
        "branches": solver.num_branches,
        "conflicts": solver.num_conflicts,
        "best_objective_bound": solver.best_objective_bound,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = {
            point for point, variable in selected.items() if solver.value(variable)
        }
        layer_histogram = {
            multiplier: sum(
                ((x + 1) * (y + 1)) % p == multiplier for x, y in chosen
            )
            for multiplier in multipliers
        }
        result.update(
            {
                "selected_layer_histogram": layer_histogram,
                "selected_points": sorted(chosen),
                "verification": verify(chosen, n),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--multipliers", type=int, nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--symmetry", choices=("none", "c2"), default="none")
    args = parser.parse_args()
    multipliers = tuple(value % args.p for value in args.multipliers)
    if len(multipliers) < 2 or 0 in multipliers or len(set(multipliers)) != len(
        multipliers
    ):
        raise ValueError("need at least two distinct nonzero multipliers")
    result = solve(
        args.p,
        multipliers,
        args.workers,
        args.time_limit,
        args.seed,
        args.symmetry,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
