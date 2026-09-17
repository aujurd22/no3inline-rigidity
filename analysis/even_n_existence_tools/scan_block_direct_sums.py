"""Scan block-direct-sum compositions of known exact NTIL solutions.

Put an n-solution and a k-solution in complementary row and column blocks of
an (n+k)-board.  Each component may be transformed by D4, and the two column
blocks may be aligned or crossed relative to the row blocks.  Row and column
saturation is automatic; only cross-component collinear triples can fail.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_determinant_product import decode_record


Point = tuple[int, int]


def first_solution(cache: Path, n: int) -> set[Point] | None:
    for name in (f"n{n}_rot4", f"n{n}_rot4.few", f"n{n}_rot4.mvr"):
        path = cache / name
        if not path.exists():
            continue
        line = next((text for text in path.read_text().splitlines() if text.strip()), None)
        if line is None:
            continue
        return set(decode_record(line, n, path.suffix == ".mvr"))
    return None


def d4_images(points: set[Point], n: int) -> list[set[Point]]:
    def rotate(point: Point) -> Point:
        x, y = point
        return n - 1 - y, x

    candidates = []
    current = points
    for _ in range(4):
        candidates.append(current)
        candidates.append({(x, n - 1 - y) for x, y in current})
        current = {rotate(point) for point in current}
    result = []
    seen = set()
    for candidate in candidates:
        key = frozenset(candidate)
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return result


def no_three(points: set[Point]) -> bool:
    import math

    ordered = list(points)
    for first_index, first in enumerate(ordered):
        directions = set()
        for second_index, second in enumerate(ordered):
            if first_index == second_index:
                continue
            dx = second[0] - first[0]
            dy = second[1] - first[1]
            divisor = math.gcd(abs(dx), abs(dy))
            direction = (dx // divisor, dy // divisor)
            if direction[0] < 0 or (
                direction[0] == 0 and direction[1] < 0
            ):
                direction = (-direction[0], -direction[1])
            if direction in directions:
                return False
            directions.add(direction)
    return True


def compose(
    first: set[Point],
    n: int,
    second: set[Point],
    k: int,
    crossed: bool,
) -> set[Point]:
    if crossed:
        # First component in lower-left row/column block, second upper-right.
        first_embedded = {(x, y + k) for x, y in first}
        second_embedded = {(x + n, y) for x, y in second}
    else:
        first_embedded = set(first)
        second_embedded = {(x + n, y + n) for x, y in second}
    return first_embedded | second_embedded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--minimum-n", type=int, default=4)
    parser.add_argument("--maximum-n", type=int, default=36)
    args = parser.parse_args()

    solutions = {
        n: first_solution(args.cache, n)
        for n in range(args.minimum_n, args.maximum_n + 1, 2)
    }
    solutions = {n: points for n, points in solutions.items() if points}
    hits = []
    tested = 0
    for n, first in solutions.items():
        for k, second in solutions.items():
            if n > k:
                continue
            first_images = d4_images(first, n)
            second_images = d4_images(second, k)
            for first_image_number, first_image in enumerate(first_images):
                for second_image_number, second_image in enumerate(second_images):
                    for crossed in (False, True):
                        tested += 1
                        candidate = compose(
                            first_image, n, second_image, k, crossed
                        )
                        if no_three(candidate):
                            hit = {
                                "n": n,
                                "k": k,
                                "N": n + k,
                                "first_d4_image": first_image_number,
                                "second_d4_image": second_image_number,
                                "crossed": crossed,
                                "points": sorted(candidate),
                            }
                            hits.append(hit)
                            print(json.dumps({"event": "hit", **hit}), flush=True)
    print(
        json.dumps(
            {
                "event": "summary",
                "orders": sorted(solutions),
                "tested": tested,
                "hits": len(hits),
                "hit_order_pairs": sorted({(hit["n"], hit["k"]) for hit in hits}),
            }
        )
    )


if __name__ == "__main__":
    main()
