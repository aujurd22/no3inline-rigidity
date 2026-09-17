"""Test the strongest natural doubling recurrence.

Given an exact 2m-point solution on an m by m grid, its row-column graph is
2-regular and decomposes into two permutations f and g.  Doubling every base
edge gives the 4-regular multigraph represented by [f, g, f, g].  The exact
lift solver then asks whether *any* balanced two-bit labelling of this doubled
graph yields a 4m-point solution on the 2m by 2m grid.

This strictly contains the previously tested fixed-parity copy construction.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from analyze_modp_reductions import SYMMETRY_MARKERS, VALUE, matching_from_support
from four_permutation_lift_sat import solve, verify


def decode_first_available(cache: Path, n: int) -> tuple[list[tuple[int, int]], str]:
    preferred = (
        "rot4",
        "iden",
        "rot2",
        "dia1",
        "dia2",
        "rct4",
        "full",
        "ort1",
    )
    for kind in preferred:
        for suffix in ("", ".few"):
            path = cache / f"n{n}_{kind}{suffix}"
            if not path.exists():
                continue
            for text in path.read_text().splitlines():
                line = text.strip()
                if not line:
                    continue
                body = line[1:] if line[0] in SYMMETRY_MARKERS else line
                if len(body) < 2 * n:
                    continue
                points: list[tuple[int, int]] = []
                try:
                    for row in range(n):
                        points.append((row, VALUE[body[2 * row]]))
                        points.append((row, VALUE[body[2 * row + 1]]))
                except KeyError:
                    continue
                if verify(points, n)["valid"]:
                    return points, path.name
    raise FileNotFoundError(f"no decodable exact solution for n={n}")


def two_permutation_decomposition(
    points: list[tuple[int, int]],
    m: int,
) -> list[list[int]]:
    multiplicity = collections.Counter(points)
    permutations = []
    for _ in range(2):
        permutation = matching_from_support(multiplicity, m)
        permutations.append(permutation)
        for x, y in enumerate(permutation):
            multiplicity[(x, y)] -= 1
    if any(multiplicity.values()):
        raise RuntimeError("two perfect matchings did not exhaust the solution graph")
    return permutations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--orders", type=int, nargs="+", required=True)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    summary = []
    for m in args.orders:
        try:
            points, source = decode_first_available(args.cache, m)
        except FileNotFoundError as error:
            summary.append({"m": m, "status": "NO_SOURCE", "detail": str(error)})
            continue
        first, second = two_permutation_decomposition(points, m)
        result = solve(
            m,
            [first, second, first, second],
            time_limit=args.time_limit,
            workers=args.workers,
        )
        record = {
            "m": m,
            "target_n": 2 * m,
            "source": source,
            "source_permutations": [first, second],
            "status": result["status"],
            "elapsed_seconds": result["elapsed_seconds"],
            "branches": result["branches"],
            "conflicts": result["conflicts"],
            "verification": result.get("verification"),
            "points": result.get("points"),
        }
        summary.append(record)
        print(json.dumps(record, indent=2), flush=True)
    print(json.dumps({"summary": summary}, indent=2))


if __name__ == "__main__":
    main()
