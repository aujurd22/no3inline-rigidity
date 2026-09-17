"""RANSAC search for large low-degree modular-curve subsets of NTIL sets.

Green's suggested inverse direction asks whether a large no-three-in-line set
must have a large subset that lies on a low-degree curve after reduction
modulo a prime tied to the board order.  This script samples conics and cubics
through the minimum number of residue points and reports their largest
weighted inlier set.  It also evaluates random disjoint permutation-pair
baselines with the same row/column marginals.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

from analyze_determinant_product import decode_record


Point = tuple[int, int]


def monomials(degree: int) -> list[tuple[int, int]]:
    return [
        (x_power, y_power)
        for total in range(degree + 1)
        for x_power in range(total + 1)
        for y_power in (total - x_power,)
    ]


def evaluation(point: Point, powers: list[tuple[int, int]], p: int) -> list[int]:
    x, y = point
    return [
        pow(x, x_power, p) * pow(y, y_power, p) % p
        for x_power, y_power in powers
    ]


def null_vector(matrix: list[list[int]], p: int) -> tuple[int, ...] | None:
    if not matrix:
        return None
    rows = [row[:] for row in matrix]
    row_count = len(rows)
    column_count = len(rows[0])
    pivot_columns = []
    pivot_row = 0
    for column in range(column_count):
        chosen = next(
            (row for row in range(pivot_row, row_count) if rows[row][column] % p),
            None,
        )
        if chosen is None:
            continue
        rows[pivot_row], rows[chosen] = rows[chosen], rows[pivot_row]
        inverse = pow(rows[pivot_row][column] % p, -1, p)
        rows[pivot_row] = [value * inverse % p for value in rows[pivot_row]]
        for row in range(row_count):
            if row == pivot_row:
                continue
            multiplier = rows[row][column] % p
            if multiplier:
                rows[row] = [
                    (value - multiplier * pivot) % p
                    for value, pivot in zip(rows[row], rows[pivot_row])
                ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == row_count:
            break
    free_columns = [
        column for column in range(column_count) if column not in pivot_columns
    ]
    if not free_columns:
        return None
    free = free_columns[0]
    vector = [0] * column_count
    vector[free] = 1
    for row, pivot in reversed(list(enumerate(pivot_columns))):
        vector[pivot] = -sum(
            rows[row][column] * vector[column]
            for column in free_columns
        ) % p
    if not any(vector):
        return None
    return tuple(vector)


def polynomial_value(
    point: Point, coefficients: tuple[int, ...], powers: list[tuple[int, int]], p: int
) -> int:
    return sum(
        coefficient * value
        for coefficient, value in zip(coefficients, evaluation(point, powers, p))
    ) % p


def ransac(
    points: list[Point],
    p: int,
    degree: int,
    samples: int,
    seed: int,
) -> dict:
    weights = collections.Counter((x % p, y % p) for x, y in points)
    residues = list(weights)
    powers = monomials(degree)
    sample_size = len(powers) - 1
    if len(residues) < sample_size:
        raise ValueError("not enough distinct residues")
    rng = random.Random(seed)
    best = None
    seen_polynomials: set[tuple[int, ...]] = set()
    rank_deficient = 0
    for _ in range(samples):
        chosen = rng.sample(residues, sample_size)
        coefficients = null_vector(
            [evaluation(point, powers, p) for point in chosen], p
        )
        if coefficients is None:
            rank_deficient += 1
            continue
        # Canonicalise scalar multiples.
        first = next(value for value in coefficients if value)
        inverse = pow(first, -1, p)
        coefficients = tuple(value * inverse % p for value in coefficients)
        if coefficients in seen_polynomials:
            continue
        seen_polynomials.add(coefficients)
        inlier_residues = [
            point
            for point in residues
            if polynomial_value(point, coefficients, powers, p) == 0
        ]
        weighted_inliers = sum(weights[point] for point in inlier_residues)
        candidate = {
            "weighted_inliers": weighted_inliers,
            "distinct_residue_inliers": len(inlier_residues),
            "coefficients": coefficients,
            "monomials": powers,
            "inlier_residues": sorted(inlier_residues),
        }
        if best is None or (
            candidate["weighted_inliers"],
            candidate["distinct_residue_inliers"],
        ) > (
            best["weighted_inliers"],
            best["distinct_residue_inliers"],
        ):
            best = candidate
    return {
        "p": p,
        "degree": degree,
        "original_points": len(points),
        "distinct_residues": len(residues),
        "samples": samples,
        "distinct_polynomials_tested": len(seen_polynomials),
        "rank_deficient_samples": rank_deficient,
        "best": best,
    }


def random_disjoint_permutation_pair(n: int, rng: random.Random) -> list[Point]:
    first = list(range(n))
    second = list(range(n))
    rng.shuffle(first)
    while True:
        rng.shuffle(second)
        if all(first[row] != second[row] for row in range(n)):
            break
    return [
        point
        for row in range(n)
        for point in ((row, first[row]), (row, second[row]))
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--solution", type=Path, required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--primes", type=int, nargs="+", required=True)
    parser.add_argument("--degrees", type=int, nargs="+", default=[2, 3])
    parser.add_argument("--samples", type=int, default=50_000)
    parser.add_argument("--baselines", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--compact",
        action="store_true",
        help="print only one-line summaries; use --output for the full JSON",
    )
    args = parser.parse_args()

    text = next(line for line in args.solution.read_text().splitlines() if line.strip())
    points = decode_record(text, args.n, args.solution.suffix == ".mvr")
    rng = random.Random(args.seed)
    records = []
    for p in args.primes:
        for degree in args.degrees:
            exact = ransac(
                points,
                p,
                degree,
                args.samples,
                args.seed + 1009 * p + degree,
            )
            baselines = []
            for baseline_index in range(args.baselines):
                random_points = random_disjoint_permutation_pair(args.n, rng)
                baselines.append(
                    ransac(
                        random_points,
                        p,
                        degree,
                        args.samples,
                        args.seed
                        + 1_000_003 * (baseline_index + 1)
                        + 1009 * p
                        + degree,
                    )
                )
            record = {
                "source": str(args.solution),
                "n": args.n,
                "p": p,
                "degree": degree,
                "exact": exact,
                "random_baselines": baselines,
            }
            records.append(record)
            print(
                json.dumps(
                    {
                        "n": args.n,
                        "p": p,
                        "degree": degree,
                        "exact_best": exact["best"]["weighted_inliers"],
                        "baseline_best": [
                            item["best"]["weighted_inliers"] for item in baselines
                        ],
                        "exact_distinct_residues": exact["distinct_residues"],
                    }
                ),
                flush=True,
            )
    if args.output is not None:
        args.output.write_text(json.dumps(records, indent=2))
    if not args.compact:
        print("JSON_BEGIN")
        print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
