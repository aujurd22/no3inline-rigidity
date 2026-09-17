"""Analyse exact 2p-grid solutions after reduction modulo p.

For an exact 4p-point solution on the 2p by 2p grid, reduction modulo p
produces a 4-regular bipartite multigraph.  Every edge retains its two high
bits, so the original point is recovered exactly.

This program checks that statement on known solutions, decomposes the
4-regular multigraph into four perfect matchings, and measures the modular
collinearity pressure that a lift must break.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
from pathlib import Path


ALPHABET = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "#$%&@?!()[]<>{}=*+|-/~^_:;,.|"
)
VALUE = {character: index for index, character in enumerate(ALPHABET)}
SYMMETRY_MARKERS = set(".:/-ocx+*")


def decode_first(cache: Path, n: int) -> list[tuple[int, int]]:
    for suffix in ("", ".few"):
        path = cache / f"n{n}_rot4{suffix}"
        if not path.exists():
            continue
        line = next(text.strip() for text in path.read_text().splitlines() if text.strip())
        body = line[1:] if line[0] in SYMMETRY_MARKERS else line
        points: list[tuple[int, int]] = []
        for row in range(n):
            points.append((row, VALUE[body[2 * row]]))
            points.append((row, VALUE[body[2 * row + 1]]))
        return points
    raise FileNotFoundError(f"no rot4 file for n={n} below {cache}")


def determinant(
    a: tuple[int, int],
    b: tuple[int, int],
    c: tuple[int, int],
) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (
        b[1] - a[1]
    ) * (c[0] - a[0])


def matching_from_support(
    multiplicity: collections.Counter[tuple[int, int]],
    p: int,
) -> list[int]:
    """Find one perfect matching in the support of a regular multigraph."""

    match_y = [-1] * p

    def augment(x: int, seen: list[bool]) -> bool:
        for y in range(p):
            if multiplicity[(x, y)] <= 0 or seen[y]:
                continue
            seen[y] = True
            if match_y[y] < 0 or augment(match_y[y], seen):
                match_y[y] = x
                return True
        return False

    for x in range(p):
        if not augment(x, [False] * p):
            raise RuntimeError("regular bipartite support unexpectedly has no perfect matching")
    permutation = [-1] * p
    for y, x in enumerate(match_y):
        permutation[x] = y
    return permutation


def decompose_into_four_permutations(
    base_edges: list[tuple[int, int]],
    p: int,
) -> list[list[int]]:
    multiplicity: collections.Counter[tuple[int, int]] = collections.Counter(base_edges)
    permutations: list[list[int]] = []
    for _ in range(4):
        permutation = matching_from_support(multiplicity, p)
        permutations.append(permutation)
        for x, y in enumerate(permutation):
            multiplicity[(x, y)] -= 1
    if any(value for value in multiplicity.values()):
        raise RuntimeError("four matchings did not exhaust the base multigraph")
    return permutations


def line_pressure(
    base_edges: list[tuple[int, int]],
    p: int,
) -> dict:
    occupancies: list[int] = []
    by_direction: dict[str, int] = {}
    for slope in range(p):
        contribution = 0
        for intercept in range(p):
            count = sum((y - slope * x) % p == intercept for x, y in base_edges)
            occupancies.append(count)
            contribution += math.comb(count, 3)
        by_direction[str(slope)] = contribution
    vertical = 0
    for x0 in range(p):
        count = sum(x == x0 for x, _ in base_edges)
        occupancies.append(count)
        vertical += math.comb(count, 3)
    by_direction["vertical"] = vertical
    return {
        "maximum_weighted_line_occupancy": max(occupancies),
        "weighted_line_triple_sum": sum(math.comb(value, 3) for value in occupancies),
        "directional_weighted_triple_sum": by_direction,
    }


def analyse(points: list[tuple[int, int]], p: int) -> dict:
    n = 2 * p
    if len(points) != 4 * p or len(set(points)) != 4 * p:
        raise ValueError("input is not a 4p-point set")
    base_edges = [(x % p, y % p) for x, y in points]
    labels = [(x // p, y // p) for x, y in points]

    row_degrees = collections.Counter(x for x, _ in base_edges)
    column_degrees = collections.Counter(y for _, y in base_edges)
    multiplicity = collections.Counter(base_edges)

    row_label_balance = all(
        collections.Counter(
            labels[index][0]
            for index, (x, _) in enumerate(base_edges)
            if x == base_x
        )
        == {0: 2, 1: 2}
        for base_x in range(p)
    )
    column_label_balance = all(
        collections.Counter(
            labels[index][1]
            for index, (_, y) in enumerate(base_edges)
            if y == base_y
        )
        == {0: 2, 1: 2}
        for base_y in range(p)
    )
    parallel_labels_distinct = all(
        len(
            {
                labels[index]
                for index, edge_at_index in enumerate(base_edges)
                if edge_at_index == edge
            }
        )
        == count
        for edge, count in multiplicity.items()
    )

    modular_by_distinct_cells = collections.Counter()
    exact_integer_triples = 0
    modular_triples = 0
    for indices in itertools.combinations(range(4 * p), 3):
        base = [base_edges[index] for index in indices]
        if determinant(*base) % p:
            continue
        modular_triples += 1
        modular_by_distinct_cells[len(set(base))] += 1
        lifted = [points[index] for index in indices]
        if determinant(*lifted) == 0:
            exact_integer_triples += 1

    permutations = decompose_into_four_permutations(base_edges, p)
    return {
        "p": p,
        "n": n,
        "point_count": len(points),
        "integer_solution_valid": exact_integer_triples == 0,
        "integer_collinear_triples": exact_integer_triples,
        "base_is_4_regular": (
            all(row_degrees[x] == 4 for x in range(p))
            and all(column_degrees[y] == 4 for y in range(p))
        ),
        "row_high_bits_balanced": row_label_balance,
        "column_high_bits_balanced": column_label_balance,
        "parallel_edge_labels_distinct": parallel_labels_distinct,
        "unique_base_cells": len(multiplicity),
        "base_multiplicity_histogram": dict(
            sorted(collections.Counter(multiplicity.values()).items())
        ),
        "modular_collinear_triples": modular_triples,
        "modular_triples_by_distinct_base_cells": dict(
            sorted(modular_by_distinct_cells.items())
        ),
        "four_permutation_decomposition": permutations,
        **line_pressure(base_edges, p),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--primes", type=int, nargs="+", default=(5, 7, 11))
    args = parser.parse_args()
    results = []
    for p in args.primes:
        points = decode_first(args.cache, 2 * p)
        results.append(analyse(points, p))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
