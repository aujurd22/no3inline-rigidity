"""Independently certify a local minimum under every two-edge reconnection.

The C4 fundamental domain consists of m directed cells (x, y).  Ignoring
orientation, these are m edges of a degree-two pseudograph.  A complete
two-edge move removes two cells, reconnects their four endpoints in any of
the three pairings, and independently orients the two resulting edges.

This checker deliberately uses direct O((4m)^3) triple enumeration.  It does
not share the incremental line-count code with full_reconnection_search.cpp,
so it is useful as an independent certificate.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import re
from pathlib import Path


Cell = tuple[int, int]
Point = tuple[int, int]


def rotate(point: Point, n: int) -> Point:
    x, y = point
    return (n - 1 - y, x)


def full_points(cells: tuple[Cell, ...], m: int) -> tuple[Point, ...]:
    n = 2 * m
    result: list[Point] = []
    for cell in cells:
        point = cell
        for _ in range(4):
            result.append(point)
            point = rotate(point, n)
    return tuple(result)


def determinant(first: Point, second: Point, third: Point) -> int:
    return (second[0] - first[0]) * (third[1] - first[1]) - (
        second[1] - first[1]
    ) * (third[0] - first[0])


def energy(cells: tuple[Cell, ...], m: int) -> int:
    points = full_points(cells, m)
    if len(set(points)) != 4 * m:
        raise ValueError("the lifted point set contains duplicates")
    return sum(
        determinant(first, second, third) == 0
        for first, second, third in itertools.combinations(points, 3)
    )


def valid_fundamental_domain(cells: tuple[Cell, ...], m: int) -> bool:
    if len(cells) != m or len(set(cells)) != m:
        return False
    degree = [0] * m
    for first, second in cells:
        if not (0 <= first < m and 0 <= second < m):
            return False
        degree[first] += 1
        degree[second] += 1
    return degree == [2] * m


def oriented(first: int, second: int) -> tuple[Cell, Cell]:
    if first == second:
        return ((first, second),)
    return ((first, second), (second, first))


def reconnections(first: Cell, second: Cell) -> tuple[tuple[Cell, Cell], ...]:
    a, b = first
    c, d = second
    pairings = (
        ((a, b), (c, d)),
        ((a, c), (b, d)),
        ((a, d), (b, c)),
    )
    alternatives: set[tuple[Cell, Cell]] = set()
    old = tuple(sorted((first, second)))
    for (u, v), (w, z) in pairings:
        for edge_one in oriented(u, v):
            for edge_two in oriented(w, z):
                candidate = tuple(sorted((edge_one, edge_two)))
                if candidate != old and candidate[0] != candidate[1]:
                    alternatives.add(candidate)
    return tuple(sorted(alternatives))


def parse_cells(text: str) -> tuple[Cell, ...]:
    return tuple(
        (int(first), int(second))
        for first, second in re.findall(r"\((-?\d+),\s*(-?\d+)\)", text)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--cells")
    parser.add_argument("--cells-file", type=Path)
    args = parser.parse_args()
    if (args.cells is None) == (args.cells_file is None):
        parser.error("provide exactly one of --cells or --cells-file")
    text = args.cells if args.cells is not None else args.cells_file.read_text()
    cells = parse_cells(text)
    if not valid_fundamental_domain(cells, args.m):
        raise ValueError("input is not a balanced C4 fundamental domain")

    initial = energy(cells, args.m)
    delta_histogram: collections.Counter[int] = collections.Counter()
    distinct_neighbours: set[tuple[Cell, ...]] = set()
    minimum = None
    minimizers: list[dict] = []
    for first_index, second_index in itertools.combinations(range(args.m), 2):
        for replacement in reconnections(
            cells[first_index],
            cells[second_index],
        ):
            candidate_list = list(cells)
            candidate_list[first_index] = replacement[0]
            candidate_list[second_index] = replacement[1]
            candidate = tuple(sorted(candidate_list))
            if not valid_fundamental_domain(candidate, args.m):
                continue
            if candidate in distinct_neighbours:
                continue
            distinct_neighbours.add(candidate)
            candidate_energy = energy(candidate, args.m)
            delta = candidate_energy - initial
            delta_histogram[delta] += 1
            if minimum is None or candidate_energy < minimum:
                minimum = candidate_energy
                minimizers = [
                    {
                        "indices": (first_index, second_index),
                        "replacement": replacement,
                    }
                ]
            elif candidate_energy == minimum:
                minimizers.append(
                    {
                        "indices": (first_index, second_index),
                        "replacement": replacement,
                    }
                )

    print(
        json.dumps(
            {
                "m": args.m,
                "n": 2 * args.m,
                "cells": cells,
                "initial_energy": initial,
                "distinct_complete_reconnection_neighbours": len(
                    distinct_neighbours
                ),
                "minimum_neighbour_energy": minimum,
                "strictly_reducing_neighbours": sum(
                    count
                    for delta, count in delta_histogram.items()
                    if delta < 0
                ),
                "neutral_neighbours": delta_histogram[0],
                "delta_histogram": dict(sorted(delta_histogram.items())),
                "first_minimizers": minimizers[:10],
                "is_strict_local_minimum": (
                    minimum is not None and minimum > initial
                ),
                "is_weak_local_minimum": (
                    minimum is not None and minimum >= initial
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
