"""Analyze prime labels on the eight determinants from three occupied rows.

Every occupied row contains two points.  For rows r1 < r2 < r3, choosing one
point from each row gives an affine Boolean cube of eight determinants

    D(e1,e2,e3) = D0 + e1 A + e2 B + e3 C,

where, with u=r2-r1 and v=r3-r2,

    A = v * delta_1, B = -(u+v) * delta_2, C = u * delta_3.

The script records how primes at least sqrt(n), and especially primes at least
n, occupy these cubes.  For p >= n the three increments are nonzero modulo p.
Consequently a nonzero affine form can vanish on at most three Boolean
vertices (for odd p); the output explicitly checks this and classifies every
three-vertex mask by the normal of its supporting cube plane.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
from pathlib import Path

from analyze_large_prime_carries import (
    decode_solution,
    determinant,
    locate,
    primes_below,
)


Point = tuple[int, int]
Vertex = tuple[int, int, int]
VERTICES: tuple[Vertex, ...] = tuple(itertools.product((0, 1), repeat=3))


def prime_factors_by_value(limit: int) -> list[tuple[int, ...]]:
    """Return the distinct prime factors of every integer in [0, limit]."""

    factors: list[list[int]] = [[] for _ in range(limit + 1)]
    for prime in primes_below(limit + 1):
        for value in range(prime, limit + 1, prime):
            factors[value].append(prime)
    return [tuple(row) for row in factors]


def primitive_normal(vertices: tuple[Vertex, Vertex, Vertex]) -> tuple[int, int, int]:
    first, second, third = vertices
    a = tuple(second[i] - first[i] for i in range(3))
    b = tuple(third[i] - first[i] for i in range(3))
    normal = (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )
    divisor = math.gcd(math.gcd(abs(normal[0]), abs(normal[1])), abs(normal[2]))
    if divisor == 0:
        raise AssertionError("three distinct Boolean vertices were collinear")
    normal = tuple(value // divisor for value in normal)
    for value in normal:
        if value:
            if value < 0:
                normal = tuple(-entry for entry in normal)
            break
    return normal


def mask_name(indices: list[int]) -> str:
    return ",".join("".join(map(str, VERTICES[index])) for index in indices)


def row_points(points: list[Point], n: int) -> list[tuple[int, int]]:
    by_row: list[list[int]] = [[] for _ in range(n)]
    for row, column in points:
        by_row[row].append(column)
    if any(len(columns) != 2 for columns in by_row):
        raise ValueError("the configuration is not two-per-row saturated")
    return [tuple(sorted(columns)) for columns in by_row]  # type: ignore[return-value]


def summarize_threshold(
    label_maps: list[dict[int, list[int]]],
    rough_counts: list[int],
    coefficient_data: list[tuple[int, int, int]],
    threshold: int,
) -> dict:
    occupancy_histogram: collections.Counter[int] = collections.Counter()
    mask_histogram: collections.Counter[str] = collections.Counter()
    normal_histogram: collections.Counter[str] = collections.Counter()
    degenerate_increment_incidences = 0
    nondegenerate_maximum = 0
    total_prime_vertex_incidences = 0
    total_prime_cube_incidences = 0
    violation_examples = []

    for cube_index, labels in enumerate(label_maps):
        a, b, c = coefficient_data[cube_index]
        for prime, indices in labels.items():
            if prime < threshold:
                continue
            occupancy = len(indices)
            occupancy_histogram[occupancy] += 1
            total_prime_vertex_incidences += occupancy
            total_prime_cube_incidences += 1
            degenerate = a % prime == 0 or b % prime == 0 or c % prime == 0
            if degenerate:
                degenerate_increment_incidences += 1
            else:
                nondegenerate_maximum = max(nondegenerate_maximum, occupancy)
            if occupancy >= 2:
                mask_histogram[mask_name(indices)] += 1
            if occupancy == 3:
                normal = primitive_normal(
                    tuple(VERTICES[index] for index in indices)  # type: ignore[arg-type]
                )
                normal_histogram[str(normal)] += 1
            if not degenerate and occupancy > 3 and len(violation_examples) < 10:
                violation_examples.append(
                    {
                        "cube_index": cube_index,
                        "prime": prime,
                        "vertices": [list(VERTICES[index]) for index in indices],
                        "coefficients": [a, b, c],
                    }
                )

    rough_histogram = collections.Counter(rough_counts)
    cube_count = len(label_maps)
    return {
        "threshold": threshold,
        "cube_count": cube_count,
        "rough_vertex_count_histogram": dict(sorted(rough_histogram.items())),
        "mean_rough_vertices_per_cube": sum(rough_counts) / cube_count,
        "prime_cube_occupancy_histogram": dict(sorted(occupancy_histogram.items())),
        "prime_cube_incidence_count": total_prime_cube_incidences,
        "prime_vertex_incidence_count": total_prime_vertex_incidences,
        "mean_occupancy_conditioned_on_prime_cube_incidence": (
            total_prime_vertex_incidences / total_prime_cube_incidences
            if total_prime_cube_incidences
            else None
        ),
        "increment_degenerate_prime_cube_incidences": (
            degenerate_increment_incidences
        ),
        "maximum_occupancy_with_all_three_increments_nonzero_mod_p": (
            nondegenerate_maximum
        ),
        "nondegenerate_occupancy_above_three_examples": violation_examples,
        "multi_vertex_mask_histogram": dict(mask_histogram.most_common()),
        "three_vertex_supporting_normal_histogram": dict(
            normal_histogram.most_common()
        ),
    }


def analyze(points: list[Point], n: int) -> dict:
    rows = row_points(points, n)
    factors = prime_factors_by_value((n - 1) ** 2)
    medium_threshold = math.ceil(math.sqrt(n))

    label_maps: list[dict[int, list[int]]] = []
    medium_rough_counts: list[int] = []
    large_rough_counts: list[int] = []
    coefficient_data: list[tuple[int, int, int]] = []
    ordinary = 0
    determinant_count = 0

    for first_row, second_row, third_row in itertools.combinations(range(n), 3):
        first_columns = rows[first_row]
        second_columns = rows[second_row]
        third_columns = rows[third_row]
        u = second_row - first_row
        v = third_row - second_row
        delta_first = first_columns[1] - first_columns[0]
        delta_second = second_columns[1] - second_columns[0]
        delta_third = third_columns[1] - third_columns[0]
        coefficients = (
            v * delta_first,
            -(u + v) * delta_second,
            u * delta_third,
        )
        coefficient_data.append(coefficients)

        labels: dict[int, list[int]] = collections.defaultdict(list)
        medium_rough = 0
        large_rough = 0
        for vertex_index, (e1, e2, e3) in enumerate(VERTICES):
            triple = (
                (first_row, first_columns[e1]),
                (second_row, second_columns[e2]),
                (third_row, third_columns[e3]),
            )
            value = determinant(*triple)
            determinant_count += 1
            if value == 0:
                ordinary += 1
                continue
            selected_factors = factors[abs(value)]
            for prime in selected_factors:
                labels[prime].append(vertex_index)
            if any(prime >= medium_threshold for prime in selected_factors):
                medium_rough += 1
            if any(prime >= n for prime in selected_factors):
                large_rough += 1
        label_maps.append(dict(labels))
        medium_rough_counts.append(medium_rough)
        large_rough_counts.append(large_rough)

    if ordinary:
        raise ValueError(f"input has {ordinary} ordinary collinear row triples")

    medium = summarize_threshold(
        label_maps,
        medium_rough_counts,
        coefficient_data,
        medium_threshold,
    )
    large = summarize_threshold(
        label_maps,
        large_rough_counts,
        coefficient_data,
        n,
    )
    return {
        "n": n,
        "point_count": len(points),
        "row_cube_count": len(label_maps),
        "determinants_in_row_cubes": determinant_count,
        "ordinary_collinear_row_triples": ordinary,
        "medium_primes": medium,
        "large_primes": large,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--n", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = {
        "results": [
            analyze(decode_solution(locate(args.cache, n), n), n) for n in args.n
        ]
    }
    text = json.dumps(payload, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
