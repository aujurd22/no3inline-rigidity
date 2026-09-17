"""Verify the two-resource representation for every primitive direction orbit."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from analyze_rot4_shadow_factor import M, N, c4_lifts
from solve_joint_rot4_general_factor import (
    canonical_line_orbit,
    short_direction_lines,
)


HERE = Path(__file__).resolve().parent


def normalize_normal(a: int, b: int) -> tuple[int, int]:
    if a < 0 or (a == 0 and b < 0):
        return -a, -b
    return a, b


def canonical_normal_orbit(a: int, b: int) -> tuple[int, int]:
    orbit = []
    for _ in range(4):
        orbit.append(normalize_normal(a, b))
        a, b = -b, a
    return min(orbit)


def direction_representatives(q: int):
    representatives = set()
    for a in range(q + 1):
        for b in range(-q, q + 1):
            if a == 0 and b <= 0:
                continue
            if a == 0 or b == 0:
                continue
            if math.gcd(abs(a), abs(b)) != 1:
                continue
            representatives.add(canonical_normal_orbit(a, b))
    return sorted(representatives)


def predicted_resources(
    cell: tuple[int, int],
    normal: tuple[int, int],
    valid_bins: set[tuple[int, int, int]],
):
    a, b = normal
    resources = Counter()
    for x, y in c4_lifts(cell)[:2]:
        c = a * x + b * y
        key = canonical_line_orbit((a, b, c))
        if key not in valid_bins:
            continue
        weight = 2 if 2 * c == (N - 1) * (a + b) else 1
        resources[key] += weight
    return resources


def geometric_resources(
    cell: tuple[int, int],
    bins: list[tuple[int, int, int]],
):
    points = c4_lifts(cell)
    resources = Counter()
    for key in bins:
        a, b, c = key
        count = sum(a * x + b * y == c for x, y in points)
        if count:
            resources[key] = count
    return resources


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", type=int, default=3)
    parser.add_argument(
        "--out", default="rot4_multidirection_resource_audit.json"
    )
    args = parser.parse_args()
    bins = short_direction_lines(args.q)
    bins_by_direction = defaultdict(list)
    for key in bins:
        bins_by_direction[
            canonical_normal_orbit(key[0], key[1])
        ].append(key)
    representatives = direction_representatives(args.q)
    assert set(representatives) == set(bins_by_direction)

    mismatches = []
    direction_records = []
    for normal in representatives:
        direction_bins = sorted(bins_by_direction[normal])
        valid_bins = set(direction_bins)
        mismatch_before = len(mismatches)
        for u in range(M):
            for v in range(M):
                cell = (u, v)
                predicted = predicted_resources(cell, normal, valid_bins)
                geometric = geometric_resources(cell, direction_bins)
                if predicted != geometric:
                    mismatches.append(
                        {
                            "normal": list(normal),
                            "cell": list(cell),
                            "predicted": {
                                str(key): value
                                for key, value in predicted.items()
                            },
                            "geometric": {
                                str(key): value
                                for key, value in geometric.items()
                            },
                        }
                    )
                    if len(mismatches) >= 100:
                        break
            if len(mismatches) >= 100:
                break
        direction_records.append(
            {
                "normal": list(normal),
                "line_orbit_count": len(direction_bins),
                "mismatch_count": len(mismatches) - mismatch_before,
            }
        )
        if len(mismatches) >= 100:
            break
    payload = {
        "q": args.q,
        "grid_size": N,
        "fundamental_cell_count": M * M,
        "direction_orbit_count": len(representatives),
        "line_orbit_count": len(bins),
        "directions": direction_records,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "q": args.q,
                "direction_orbit_count": len(representatives),
                "line_orbit_count": len(bins),
                "mismatch_count": len(mismatches),
            },
            indent=2,
        )
    )
    print(output)


if __name__ == "__main__":
    main()
