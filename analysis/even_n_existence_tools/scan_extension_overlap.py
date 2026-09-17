"""Measure how much of a known n-solution survives in known (n+2)-solutions.

This is an inexpensive upper-bound experiment for bounded-surgery induction.
For every pair of inserted row coordinates and inserted column coordinates,
embed a known n by n solution order-preservingly in the larger board.  Then
compare it with cached exact (n+2)-solutions and report the largest point
overlap.  If the overlap is 2n-r, deleting r old points and adding r+4 new
points suffices for that concrete transition.

The scan does not prove optimality because the target cache is only a sample.
It is useful as a quick test before running an exact nearest-extension model.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from analyze_determinant_product import decode_record


Point = tuple[int, int]


def candidate_paths(cache: Path, n: int) -> list[Path]:
    names = [f"n{n}_rot4", f"n{n}_rot4.few", f"n{n}_rot4.mvr"]
    return [cache / name for name in names if (cache / name).exists()]


def read_records(cache: Path, n: int, limit: int) -> list[tuple[str, int, set[Point]]]:
    records: list[tuple[str, int, set[Point]]] = []
    for path in candidate_paths(cache, n):
        coordinate_format = path.suffix == ".mvr"
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            points = set(decode_record(line, n, coordinate_format))
            if len(points) != 2 * n:
                raise ValueError(f"{path}:{line_number}: expected {2*n} points")
            records.append((str(path), line_number, points))
            if len(records) >= limit:
                return records
    return records


def complement_maps(n: int) -> list[tuple[tuple[int, int], tuple[int, ...]]]:
    N = n + 2
    result = []
    for first in range(N):
        for second in range(first + 1, N):
            mapping = tuple(
                coordinate
                for coordinate in range(N)
                if coordinate not in (first, second)
            )
            result.append(((first, second), mapping))
    return result


def d4_images(points: set[Point], n: int) -> list[set[Point]]:
    def rotate(point: Point) -> Point:
        x, y = point
        return n - 1 - y, x

    images: list[set[Point]] = []
    current = set(points)
    for _ in range(4):
        images.append(current)
        images.append({(x, n - 1 - y) for x, y in current})
        current = {rotate(point) for point in current}
    unique: list[set[Point]] = []
    seen: set[frozenset[Point]] = set()
    for image in images:
        key = frozenset(image)
        if key not in seen:
            seen.add(key)
            unique.append(image)
    return unique


def scan_transition(
    cache: Path, n: int, source_limit: int, target_limit: int
) -> dict:
    sources = read_records(cache, n, source_limit)
    targets_raw = read_records(cache, n + 2, target_limit)
    targets = []
    for path, line, points in targets_raw:
        for image_number, image in enumerate(d4_images(points, n + 2)):
            targets.append((path, line, image_number, image))
    maps = complement_maps(n)

    best: dict | None = None
    tested = 0
    for source_path, source_line, source in sources:
        for row_gaps, row_map in maps:
            row_mapped = [(row_map[x], y) for x, y in source]
            for column_gaps, column_map in maps:
                embedded = {(x, column_map[y]) for x, y in row_mapped}
                for target_path, target_line, image_number, target in targets:
                    overlap = len(embedded & target)
                    tested += 1
                    if best is None or overlap > best["overlap"]:
                        best = {
                            "overlap": overlap,
                            "old_points_removed": 2 * n - overlap,
                            "new_points_added": 2 * (n + 2) - overlap,
                            "source": source_path,
                            "source_line": source_line,
                            "target": target_path,
                            "target_line": target_line,
                            "target_d4_image": image_number,
                            "row_gaps": row_gaps,
                            "column_gaps": column_gaps,
                            "embedded_old_points": sorted(embedded),
                            "target_points": sorted(target),
                        }
    return {
        "n": n,
        "N": n + 2,
        "source_records": len(sources),
        "target_records": len(targets_raw),
        "target_images": len(targets),
        "comparisons": tested,
        "best": best,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--minimum-n", type=int, default=6)
    parser.add_argument("--maximum-n", type=int, default=24)
    parser.add_argument("--source-limit", type=int, default=1)
    parser.add_argument("--target-limit", type=int, default=20)
    args = parser.parse_args()

    results = []
    for n in range(args.minimum_n, args.maximum_n + 1, 2):
        if not candidate_paths(args.cache, n) or not candidate_paths(args.cache, n + 2):
            continue
        result = scan_transition(
            args.cache, n, args.source_limit, args.target_limit
        )
        results.append(result)
        best = result["best"]
        print(
            json.dumps(
                {
                    "n": n,
                    "sources": result["source_records"],
                    "targets": result["target_records"],
                    "comparisons": result["comparisons"],
                    "best_overlap": best["overlap"] if best else None,
                    "old_points_removed": (
                        best["old_points_removed"] if best else None
                    ),
                }
            ),
            flush=True,
        )
    print("JSON_BEGIN")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
