"""Exact bounded-surgery experiment for the affine n -> n+2 embedding.

Embed a known n by n NTIL set into the (n+2) by (n+2) board by translating
all old coordinates by row_shift,column_shift in {0,1,2}.  The two missing
rows and columns are therefore at the boundary (or one at each boundary).

On the larger board solve the exact line-packing model:

    two selected points in every row and column;
    at most two selected points on every maximal grid line.

The objective maximises the number of embedded old points retained.  Thus
2n-overlap is the exact number of old points that must be replaced for this
fixed affine embedding when OPTIMAL is returned.
"""

from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

from ortools.sat.python import cp_model

from analyze_determinant_product import decode_record
from nearest_c4_solution_sat import long_grid_lines


Point = tuple[int, int]


def source_path(cache: Path, n: int) -> Path:
    for name in (f"n{n}_rot4", f"n{n}_rot4.few", f"n{n}_rot4.mvr"):
        path = cache / name
        if path.exists():
            return path
    raise FileNotFoundError(f"no C4 source for n={n}")


def load_source(cache: Path, n: int) -> tuple[Path, set[Point]]:
    path = source_path(cache, n)
    text = next(line for line in path.read_text().splitlines() if line.strip())
    points = set(decode_record(text, n, path.suffix == ".mvr"))
    if len(points) != 2 * n:
        raise ValueError(f"{path}: expected {2*n} points")
    return path, points


def build_base(N: int) -> tuple[cp_model.CpModel, dict[Point, cp_model.IntVar], dict]:
    model = cp_model.CpModel()
    variables = {
        (x, y): model.new_bool_var(f"x_{x}_{y}")
        for x in range(N)
        for y in range(N)
    }
    for x in range(N):
        model.add(sum(variables[(x, y)] for y in range(N)) == 2)
    for y in range(N):
        model.add(sum(variables[(x, y)] for x in range(N)) == 2)

    lines, statistics = long_grid_lines(N)
    signatures: set[tuple[Point, ...]] = set()
    for points in lines:
        signature = tuple(sorted(points))
        if signature in signatures:
            continue
        signatures.add(signature)
        model.add(sum(variables[point] for point in points) <= 2)
    statistics["variables"] = N * N
    statistics["line_constraints"] = len(signatures)
    return model, variables, statistics


def determinant(a: Point, b: Point, c: Point) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (
        b[1] - a[1]
    )


def verify(points: set[Point], N: int) -> dict:
    bad = sum(
        determinant(a, b, c) == 0
        for a, b, c in itertools.combinations(points, 3)
    )
    rows = [sum(x == row for x, _ in points) for row in range(N)]
    columns = [sum(y == column for _, y in points) for column in range(N)]
    return {
        "points": len(points),
        "distinct": len(points),
        "rows_two": rows == [2] * N,
        "columns_two": columns == [2] * N,
        "collinear_triples": bad,
        "valid": (
            len(points) == 2 * N
            and rows == [2] * N
            and columns == [2] * N
            and bad == 0
        ),
    }


def solve_embedding(
    base: cp_model.CpModel,
    variables: dict[Point, cp_model.IntVar],
    old_points: set[Point],
    n: int,
    row_shift: int,
    column_shift: int,
    workers: int,
    time_limit: float,
) -> dict:
    embedded = {
        (x + row_shift, y + column_shift) for x, y in old_points
    }
    model = base.clone()
    overlap = sum(variables[point] for point in embedded)
    model.maximize(overlap)
    for point, variable in variables.items():
        model.add_hint(variable, int(point in embedded))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = (
        1000003 * n + 101 * row_shift + column_shift
    )
    started = time.perf_counter()
    status = solver.solve(model)
    result = {
        "n": n,
        "N": n + 2,
        "row_shift": row_shift,
        "column_shift": column_shift,
        "status": solver.status_name(status),
        "wall_seconds": time.perf_counter() - started,
        "best_objective_bound": solver.best_objective_bound,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected = {
            point for point, variable in variables.items() if solver.value(variable)
        }
        retained = len(selected & embedded)
        result.update(
            {
                "retained_old_points": retained,
                "old_points_removed": 2 * n - retained,
                "new_points_added": 2 * (n + 2) - retained,
                "embedded_old_points": sorted(embedded),
                "selected_points": sorted(selected),
                "verification": verify(selected, n + 2),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--minimum-n", type=int, default=6)
    parser.add_argument("--maximum-n", type=int, default=24)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--time-limit", type=float, default=30.0)
    args = parser.parse_args()

    for n in range(args.minimum_n, args.maximum_n + 1, 2):
        path, old_points = load_source(args.cache, n)
        N = n + 2
        base, variables, statistics = build_base(N)
        # Reflections and transposition make these four shift types sufficient.
        shift_types = ((0, 0), (0, 1), (0, 2), (1, 1))
        print(
            json.dumps(
                {
                    "event": "model_built",
                    "n": n,
                    "source": str(path),
                    **statistics,
                }
            ),
            flush=True,
        )
        for row_shift, column_shift in shift_types:
            result = solve_embedding(
                base,
                variables,
                old_points,
                n,
                row_shift,
                column_shift,
                args.workers,
                args.time_limit,
            )
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
