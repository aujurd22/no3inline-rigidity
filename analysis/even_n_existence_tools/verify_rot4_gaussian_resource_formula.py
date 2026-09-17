"""Verify the centered Gaussian-integer formula for rot4 line resources.

For a fundamental cell (u,v), put X=2u-(N-1), Y=2v-(N-1).  For a primitive
normal (a,b), the two C4 line-orbit labels touched by the cell are

    |aX+bY| and |bX-aY|.

Repeated labels have multiplicity two.  This includes non-central collisions,
which are easy to miss when the two-resource statement is phrased only in
terms of individual rotated points.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from analyze_rot4_shadow_factor import M, N, c4_lifts
from solve_joint_rot4_general_factor import short_direction_lines
from verify_rot4_multidirection_resource_model import (
    canonical_normal_orbit,
    direction_representatives,
)


HERE = Path(__file__).resolve().parent


def centered_intercept(key: tuple[int, int, int]) -> int:
    a, b, c = key
    return abs(2 * c - (N - 1) * (a + b))


def geometric_resource_labels(
    cell: tuple[int, int], bins: list[tuple[int, int, int]]
) -> Counter[int]:
    points = c4_lifts(cell)
    result = Counter()
    for key in bins:
        a, b, c = key
        count = sum(a * x + b * y == c for x, y in points)
        if count:
            result[centered_intercept(key)] += count
    return result


def predicted_resource_labels(
    cell: tuple[int, int],
    normal: tuple[int, int],
    valid_labels: set[int],
) -> tuple[Counter[int], tuple[int, int]]:
    u, v = cell
    a, b = normal
    x = 2 * u - (N - 1)
    y = 2 * v - (N - 1)
    labels = (abs(a * x + b * y), abs(b * x - a * y))
    resources = Counter()
    for label in labels:
        if label in valid_labels:
            # A centered line is invariant under the half turn, so the
            # antipodal pair of orbit points lies on that same line.
            resources[label] += 2 if label == 0 else 1
    return resources, labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", type=int, default=5)
    parser.add_argument(
        "--out", default="rot4_gaussian_resource_formula_audit.json"
    )
    args = parser.parse_args()

    bins = short_direction_lines(args.q)
    bins_by_direction = defaultdict(list)
    for key in bins:
        bins_by_direction[
            canonical_normal_orbit(key[0], key[1])
        ].append(key)
    directions = direction_representatives(args.q)
    assert set(directions) == set(bins_by_direction)

    mismatches = []
    norm_mismatches = []
    records = []
    for normal in directions:
        direction_bins = sorted(bins_by_direction[normal])
        valid_labels = {centered_intercept(key) for key in direction_bins}
        assert len(valid_labels) == len(direction_bins)
        collision_count = 0
        central_incidence_count = 0
        omitted_incidence_count = 0
        for u in range(M):
            for v in range(M):
                predicted, raw_labels = predicted_resource_labels(
                    (u, v), normal, valid_labels
                )
                geometric = geometric_resource_labels((u, v), direction_bins)
                if predicted != geometric:
                    mismatches.append(
                        {
                            "normal": list(normal),
                            "cell": [u, v],
                            "raw_labels": list(raw_labels),
                            "predicted": dict(predicted),
                            "geometric": dict(geometric),
                        }
                    )
                if raw_labels[0] == raw_labels[1]:
                    collision_count += 1
                central_incidence_count += sum(label == 0 for label in raw_labels)
                omitted_incidence_count += sum(
                    label not in valid_labels for label in raw_labels
                )
                x, y = 2 * u - (N - 1), 2 * v - (N - 1)
                left = raw_labels[0] ** 2 + raw_labels[1] ** 2
                right = (normal[0] ** 2 + normal[1] ** 2) * (
                    x * x + y * y
                )
                if left != right:
                    norm_mismatches.append(
                        {
                            "normal": list(normal),
                            "cell": [u, v],
                            "left": left,
                            "right": right,
                        }
                    )
        records.append(
            {
                "normal": list(normal),
                "line_orbit_count": len(direction_bins),
                "resource_label_min": min(valid_labels),
                "resource_label_max": max(valid_labels),
                "noncentral_double_resource_cell_count": collision_count,
                "central_double_resource_cell_count": central_incidence_count,
                "omitted_short_line_incidences": omitted_incidence_count,
            }
        )

    payload = {
        "q": args.q,
        "grid_size": N,
        "fundamental_cell_count": M * M,
        "direction_orbit_count": len(directions),
        "line_orbit_count": len(bins),
        "formula": [
            "X=2u-(N-1), Y=2v-(N-1)",
            "r=abs(aX+bY), s=abs(bX-aY)",
            "r^2+s^2=(a^2+b^2)(X^2+Y^2)",
        ],
        "directions": records,
        "resource_mismatch_count": len(mismatches),
        "norm_mismatch_count": len(norm_mismatches),
        "mismatches": mismatches[:100],
        "norm_mismatches": norm_mismatches[:100],
    }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "q": args.q,
                "directions": len(directions),
                "lines": len(bins),
                "resource_mismatches": len(mismatches),
                "norm_mismatches": len(norm_mismatches),
                "noncentral_double_resource_cells": sum(
                    item["noncentral_double_resource_cell_count"]
                    for item in records
                ),
            },
            indent=2,
        )
    )
    print(output)


if __name__ == "__main__":
    main()
