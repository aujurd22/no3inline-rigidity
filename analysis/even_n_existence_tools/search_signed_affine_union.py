"""Search liftable unions H ∪ T(H) under signed torus-affine maps.

Here H is the two-regular row-column graph of a known exact m-grid solution.
The maps

    (x,y) -> (±x+b, ±y+d) mod m

and their coordinate-swapped analogues preserve row/column degrees.  They
strictly generalise the eight literal square symmetries while retaining a
uniform formula for every m.
"""

from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

from four_permutation_lift_sat import solve
from test_doubled_solution_lifts import (
    decode_first_available,
    two_permutation_decomposition,
)


def transform_permutation(
    permutation: list[int],
    m: int,
    swap: bool,
    row_sign: int,
    column_sign: int,
    row_shift: int,
    column_shift: int,
) -> list[int]:
    result = [-1] * m
    for x, y in enumerate(permutation):
        if swap:
            new_x = (row_sign * y + row_shift) % m
            new_y = (column_sign * x + column_shift) % m
        else:
            new_x = (row_sign * x + row_shift) % m
            new_y = (column_sign * y + column_shift) % m
        result[new_x] = new_y
    if sorted(result) != list(range(m)):
        raise AssertionError("transform did not preserve a perfect matching")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--orders", type=int, nargs="+", required=True)
    parser.add_argument("--time-limit", type=float, default=3.0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    for m in args.orders:
        points, source = decode_first_available(args.cache, m)
        base = two_permutation_decomposition(points, m)
        seen_graphs: set[tuple[tuple[int, ...], ...]] = set()
        status_counts: dict[str, int] = {}
        started = time.perf_counter()
        found = None
        for swap, row_sign, column_sign, row_shift, column_shift in itertools.product(
            (False, True),
            (-1, 1),
            (-1, 1),
            range(m),
            range(m),
        ):
            transformed = [
                transform_permutation(
                    permutation,
                    m,
                    swap,
                    row_sign,
                    column_sign,
                    row_shift,
                    column_shift,
                )
                for permutation in base
            ]
            graph_key = tuple(
                sorted(tuple(permutation) for permutation in base + transformed)
            )
            if graph_key in seen_graphs:
                continue
            seen_graphs.add(graph_key)
            result = solve(
                m,
                base + transformed,
                time_limit=args.time_limit,
                workers=args.workers,
            )
            status = result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            if status in ("OPTIMAL", "FEASIBLE"):
                found = {
                    "parameters": {
                        "swap": swap,
                        "row_sign": row_sign,
                        "column_sign": column_sign,
                        "row_shift": row_shift,
                        "column_shift": column_shift,
                    },
                    "base_permutations": base,
                    "transformed_permutations": transformed,
                    "result": result,
                }
                print(
                    json.dumps(
                        {
                            "hit": True,
                            "m": m,
                            "target_n": 2 * m,
                            "source": source,
                            **found,
                        },
                        indent=2,
                    ),
                    flush=True,
                )
                break
            if len(seen_graphs) % 100 == 0:
                print(
                    json.dumps(
                        {
                            "progress": True,
                            "m": m,
                            "tested": len(seen_graphs),
                            "status_counts": status_counts,
                            "wall_seconds": time.perf_counter() - started,
                        }
                    ),
                    flush=True,
                )
        print(
            json.dumps(
                {
                    "summary": True,
                    "m": m,
                    "target_n": 2 * m,
                    "source": source,
                    "tested": len(seen_graphs),
                    "status_counts": status_counts,
                    "found": found is not None,
                    "wall_seconds": time.perf_counter() - started,
                },
                indent=2,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
