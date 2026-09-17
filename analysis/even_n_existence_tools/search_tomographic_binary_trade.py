"""Search for a {-1,0,1} trade preserving all primitive directions up to Q.

A signed grid pattern h is a tomographic trade for a direction d when every
line parallel to d has signed sum zero.  Replacing the negative support by the
positive support therefore preserves all line occupancies in that direction.

The optional per-sign row/column capacity is relevant to the NTIL problem:
capacity two lets either side be embedded in a row/column-saturated candidate.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from ortools.sat.python import cp_model


def directions(q: int) -> list[tuple[int, int]]:
    result = []
    for first in range(q + 1):
        for second in range(-q, q + 1):
            if first == 0 and second <= 0:
                continue
            if (first, second) == (0, 0):
                continue
            if math.gcd(abs(first), abs(second)) != 1:
                continue
            result.append((first, second))
    return result


def lines_for_direction(
    side: int, direction: tuple[int, int]
) -> dict[int, list[tuple[int, int]]]:
    first, second = direction
    groups: dict[int, list[tuple[int, int]]] = {}
    for x in range(side):
        for y in range(side):
            intercept = second * x - first * y
            groups.setdefault(intercept, []).append((x, y))
    return groups


def solve(
    q: int,
    side: int,
    capacity: int | None,
    time_limit: float,
    workers: int,
) -> dict:
    model = cp_model.CpModel()
    positive = {}
    negative = {}
    for x in range(side):
        for y in range(side):
            positive[x, y] = model.new_bool_var(f"p_{x}_{y}")
            negative[x, y] = model.new_bool_var(f"m_{x}_{y}")
            model.add(positive[x, y] + negative[x, y] <= 1)

    selected_directions = directions(q)
    for direction in selected_directions:
        for cells in lines_for_direction(side, direction).values():
            model.add(
                sum(positive[cell] - negative[cell] for cell in cells) == 0
            )

    # Translation-normalize the bounding box, and break global sign symmetry.
    model.add(
        sum(positive[0, y] + negative[0, y] for y in range(side)) >= 1
    )
    model.add(
        sum(positive[x, 0] + negative[x, 0] for x in range(side)) >= 1
    )
    model.add(sum(positive[0, y] for y in range(side)) >= 1)

    if capacity is not None:
        for coordinate in range(side):
            model.add(
                sum(positive[coordinate, y] for y in range(side)) <= capacity
            )
            model.add(
                sum(negative[coordinate, y] for y in range(side)) <= capacity
            )
            model.add(
                sum(positive[x, coordinate] for x in range(side)) <= capacity
            )
            model.add(
                sum(negative[x, coordinate] for x in range(side)) <= capacity
            )

    # Sparse solutions are the most useful absorbers and dramatically reduce
    # otherwise irrelevant dense nullspace solutions.
    support = sum(
        positive[x, y] + negative[x, y]
        for x in range(side)
        for y in range(side)
    )
    model.minimize(support)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.log_search_progress = False
    status = solver.solve(model)
    status_name = solver.status_name(status)

    result = {
        "q": q,
        "side": side,
        "capacity_per_sign_per_row_or_column": capacity,
        "direction_count": len(selected_directions),
        "directions": selected_directions,
        "status": status_name,
        "wall_time_seconds": solver.wall_time,
        "best_objective_bound": solver.best_objective_bound,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        plus = [
            [x, y]
            for x in range(side)
            for y in range(side)
            if solver.value(positive[x, y])
        ]
        minus = [
            [x, y]
            for x in range(side)
            for y in range(side)
            if solver.value(negative[x, y])
        ]
        result.update(
            {
                "support": len(plus) + len(minus),
                "positive": plus,
                "negative": minus,
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", type=int, required=True)
    parser.add_argument("--side", type=int, required=True)
    parser.add_argument("--capacity", type=int)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = solve(
        args.q, args.side, args.capacity, args.time_limit, args.workers
    )
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
