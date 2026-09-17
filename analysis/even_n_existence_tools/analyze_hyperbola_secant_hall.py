"""Extract Hall certificates from the integer secants of one modular hyperbola.

Fix H_a={(x-1,a/x-1): x in F_p^*} in the (p-1)-square.  Any point added to
an NTIL completion must avoid every ordinary grid line containing two points
of H_a.  The remaining cells form a bipartite graph between rows and columns.
If this graph has no perfect matching, alternating reachability from unmatched
rows gives an explicit Hall-deficient set S with |N(S)|<|S|.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter, deque


Point = tuple[int, int]


def hyperbola_layer(p: int, multiplier: int) -> set[Point]:
    return {
        (x - 1, multiplier * pow(x, -1, p) % p - 1)
        for x in range(1, p)
    }


def long_grid_lines(
    n: int,
) -> tuple[list[tuple[Point, ...]], dict[str, int | float]]:
    """Enumerate maximal ordinary grid lines containing at least three cells."""

    started = time.perf_counter()
    maximum_step = (n - 1) // 2
    directions = [(0, 1)]
    directions.extend(
        (dx, dy)
        for dx in range(1, maximum_step + 1)
        for dy in range(-maximum_step, maximum_step + 1)
        if math.gcd(dx, abs(dy)) == 1
    )
    lines: list[tuple[Point, ...]] = []
    for dx, dy in directions:
        for x in range(n):
            for y in range(n):
                if 0 <= x - dx < n and 0 <= y - dy < n:
                    continue
                if not (0 <= x + 2 * dx < n and 0 <= y + 2 * dy < n):
                    continue
                points = []
                current_x, current_y = x, y
                while 0 <= current_x < n and 0 <= current_y < n:
                    points.append((current_x, current_y))
                    current_x += dx
                    current_y += dy
                lines.append(tuple(points))
    return lines, {
        "primitive_directions_with_possible_three_point_lines": len(
            directions
        ),
        "lines_with_at_least_three_grid_points": len(lines),
        "line_enumeration_seconds": time.perf_counter() - started,
    }


def allowed_graph(p: int, multiplier: int) -> tuple[list[list[int]], dict]:
    n = p - 1
    fixed = hyperbola_layer(p, multiplier)
    forbidden: set[Point] = set(fixed)
    secants = []
    lines, line_statistics = long_grid_lines(n)
    for line in lines:
        fixed_points = [point for point in line if point in fixed]
        if len(fixed_points) >= 2:
            forbidden.update(line)
            secants.append(
                {
                    "fixed_load": len(fixed_points),
                    "fixed_points": sorted(fixed_points),
                    "line_points": sorted(line),
                }
            )
    adjacency = [
        [column for column in range(n) if (row, column) not in forbidden]
        for row in range(n)
    ]
    metadata = {
        "p": p,
        "n": n,
        "multiplier": multiplier,
        "fixed_points": sorted(fixed),
        "line_statistics": line_statistics,
        "secant_line_count": len(secants),
        "secant_fixed_load_histogram": dict(
            sorted(Counter(item["fixed_load"] for item in secants).items())
        ),
        "forbidden_cell_count": len(forbidden),
        "allowed_cell_count": sum(map(len, adjacency)),
        "row_degrees": [len(neighbors) for neighbors in adjacency],
        "column_degrees": [
            sum(column in neighbors for neighbors in adjacency)
            for column in range(n)
        ],
        "secants": secants,
    }
    return adjacency, metadata


def maximum_matching(adjacency: list[list[int]]) -> tuple[list[int], list[int]]:
    """Hopcroft-Karp; returns row->column and column->row, with -1 unmatched."""

    n_left = len(adjacency)
    n_right = n_left
    pair_left = [-1] * n_left
    pair_right = [-1] * n_right
    distance = [0] * n_left
    infinity = n_left + 1

    def bfs() -> bool:
        queue: deque[int] = deque()
        found = False
        for row in range(n_left):
            if pair_left[row] == -1:
                distance[row] = 0
                queue.append(row)
            else:
                distance[row] = infinity
        while queue:
            row = queue.popleft()
            for column in adjacency[row]:
                matched_row = pair_right[column]
                if matched_row == -1:
                    found = True
                elif distance[matched_row] == infinity:
                    distance[matched_row] = distance[row] + 1
                    queue.append(matched_row)
        return found

    def dfs(row: int) -> bool:
        for column in adjacency[row]:
            matched_row = pair_right[column]
            if matched_row == -1 or (
                distance[matched_row] == distance[row] + 1 and dfs(matched_row)
            ):
                pair_left[row] = column
                pair_right[column] = row
                return True
        distance[row] = infinity
        return False

    while bfs():
        for row in range(n_left):
            if pair_left[row] == -1:
                dfs(row)
    return pair_left, pair_right


def hall_certificate(
    adjacency: list[list[int]], pair_left: list[int], pair_right: list[int]
) -> tuple[list[int], list[int]]:
    """Alternating-reachability Hall set from every unmatched left vertex."""

    seen_left = {row for row, column in enumerate(pair_left) if column == -1}
    seen_right: set[int] = set()
    queue: deque[tuple[bool, int]] = deque(
        (True, row) for row in sorted(seen_left)
    )
    while queue:
        on_left, vertex = queue.popleft()
        if on_left:
            row = vertex
            for column in adjacency[row]:
                # Traverse only unmatched edges left -> right.
                if pair_left[row] == column or column in seen_right:
                    continue
                seen_right.add(column)
                queue.append((False, column))
        else:
            column = vertex
            row = pair_right[column]
            # Traverse the matched edge right -> left.
            if row != -1 and row not in seen_left:
                seen_left.add(row)
                queue.append((True, row))
    return sorted(seen_left), sorted(seen_right)


def analyze(p: int, multiplier: int, include_secants: bool) -> dict:
    adjacency, metadata = allowed_graph(p, multiplier)
    pair_left, pair_right = maximum_matching(adjacency)
    matching = [
        [row, column] for row, column in enumerate(pair_left) if column != -1
    ]
    result = {
        key: value
        for key, value in metadata.items()
        if include_secants or key != "secants"
    }
    result["matching_size"] = len(matching)
    result["matching"] = matching
    result["perfect_matching"] = len(matching) == p - 1
    if len(matching) < p - 1:
        rows, columns = hall_certificate(adjacency, pair_left, pair_right)
        actual_neighbors = sorted(
            {column for row in rows for column in adjacency[row]}
        )
        assert actual_neighbors == columns
        assert len(columns) < len(rows)
        result["hall_rows"] = rows
        result["hall_neighbor_columns"] = columns
        result["hall_deficiency"] = len(rows) - len(columns)
        result["hall_row_allowed_columns"] = {
            str(row): adjacency[row] for row in rows
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--multipliers", type=int, nargs="+")
    parser.add_argument("--include-secants", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    multipliers = args.multipliers or list(range(1, args.p))
    records = []
    for multiplier in multipliers:
        result = analyze(args.p, multiplier % args.p, args.include_secants)
        records.append(result)
        compact = {
            key: result[key]
            for key in (
                "p",
                "multiplier",
                "secant_line_count",
                "forbidden_cell_count",
                "allowed_cell_count",
                "row_degrees",
                "matching_size",
                "perfect_matching",
            )
        }
        if not result["perfect_matching"]:
            compact.update(
                hall_rows=result["hall_rows"],
                hall_neighbor_columns=result["hall_neighbor_columns"],
                hall_deficiency=result["hall_deficiency"],
            )
        print(json.dumps(compact), flush=True)
    if args.output:
        with open(args.output, "w") as stream:
            json.dump(records, stream, indent=2)


if __name__ == "__main__":
    main()
