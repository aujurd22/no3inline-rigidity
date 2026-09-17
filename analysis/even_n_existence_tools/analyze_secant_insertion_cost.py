"""Analyze local insertion cost and low-cost alternating cycles.

For an empty cell z, old secants through z form a matching because the old
configuration has no three collinear points.  Inserting z while protecting
directions below Q therefore requires deleting one endpoint from each of
d_Q(z) disjoint non-axis secants, in addition to row/column balancing.

The script also finds the smallest threshold t for which empty cells of cost
at most t, together with occupied row-column edges, contain an alternating
cycle.  Below t no balanced switch can use only low-cost inserted cells.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from analyze_large_prime_carries import decode_solution, locate
from analyze_switch_scale_safety import secant_index


Point = tuple[int, int]


def nonaxis_costs(points: list[Point], n: int, q: int) -> dict[Point, int]:
    occupied = set(points)
    index = secant_index(points, n)
    costs = {}
    for x in range(n):
        for y in range(n):
            cell = (x, y)
            if cell in occupied:
                continue
            cost = 0
            for first, second, scale in index.get(cell, ()):
                dx = points[second][0] - points[first][0]
                dy = points[second][1] - points[first][1]
                if dx != 0 and dy != 0 and scale < q:
                    cost += 1
            costs[cell] = cost
    return costs


def directed_cycle(
    points: list[Point],
    costs: dict[Point, int],
    n: int,
    threshold: int,
) -> list[int] | None:
    """Return a row/column-node directed cycle, if one exists."""

    adjacency: list[list[int]] = [[] for _ in range(2 * n)]
    # New empty edges are oriented row -> column.
    for (row, column), cost in costs.items():
        if cost <= threshold:
            adjacency[row].append(n + column)
    # Old occupied edges are oriented column -> row.
    for row, column in points:
        adjacency[n + column].append(row)

    state = [0] * (2 * n)
    parent = [-1] * (2 * n)

    def visit(start: int) -> list[int] | None:
        stack: list[tuple[int, int]] = [(start, 0)]
        state[start] = 1
        while stack:
            node, next_index = stack[-1]
            if next_index == len(adjacency[node]):
                state[node] = 2
                stack.pop()
                continue
            target = adjacency[node][next_index]
            stack[-1] = (node, next_index + 1)
            if state[target] == 0:
                state[target] = 1
                parent[target] = node
                stack.append((target, 0))
                continue
            if state[target] == 1:
                cycle = [node]
                while cycle[-1] != target:
                    cycle.append(parent[cycle[-1]])
                cycle.reverse()
                return cycle
        return None

    for node in range(2 * n):
        if state[node] == 0:
            cycle = visit(node)
            if cycle is not None:
                return cycle
    return None


def shortest_alternating_trade(
    points: list[Point],
    costs: dict[Point, int],
    n: int,
    threshold: int,
) -> dict | None:
    """Find a minimum-edge balanced alternating trade at this cost threshold."""

    old_by_column: list[list[int]] = [[] for _ in range(n)]
    for row, column in points:
        old_by_column[column].append(row)

    # Contract each new row->column edge followed by an old column->row edge.
    # An arc stores (target row, added cell, removed cell).
    adjacency: list[list[tuple[int, Point, Point]]] = [[] for _ in range(n)]
    for (row, column), cost in costs.items():
        if cost > threshold:
            continue
        for target_row in old_by_column[column]:
            adjacency[row].append(
                (target_row, (row, column), (target_row, column))
            )

    best: dict | None = None
    for start in range(n):
        distance = [-1] * n
        parent: list[tuple[int, Point, Point] | None] = [None] * n
        distance[start] = 0
        queue = collections.deque([start])
        closing: tuple[int, Point, Point] | None = None
        closing_node = -1
        while queue and closing is None:
            node = queue.popleft()
            if best is not None and distance[node] + 1 >= best["removed_count"]:
                continue
            for target, added, removed in adjacency[node]:
                if target == start:
                    closing = (target, added, removed)
                    closing_node = node
                    break
                if distance[target] < 0:
                    distance[target] = distance[node] + 1
                    parent[target] = (node, added, removed)
                    queue.append(target)
        if closing is None:
            continue

        path_arcs: list[tuple[Point, Point]] = []
        node = closing_node
        while node != start:
            entry = parent[node]
            assert entry is not None
            previous, added, removed = entry
            path_arcs.append((added, removed))
            node = previous
        path_arcs.reverse()
        path_arcs.append((closing[1], closing[2]))
        candidate = {
            "removed_count": len(path_arcs),
            "removed": [list(removed) for _, removed in path_arcs],
            "added": [list(added) for added, _ in path_arcs],
        }
        if best is None or candidate["removed_count"] < best["removed_count"]:
            best = candidate
    return best


def decode_cycle(
    cycle: list[int], points: list[Point], n: int
) -> dict:
    occupied = set(points)
    added = []
    removed = []
    for index, node in enumerate(cycle):
        target = cycle[(index + 1) % len(cycle)]
        if node < n and target >= n:
            added.append([node, target - n])
        elif node >= n and target < n:
            edge = (target, node - n)
            if edge not in occupied:
                raise AssertionError("directed red edge is not occupied")
            removed.append(list(edge))
        else:
            raise AssertionError("cycle is not bipartite alternating")
    return {
        "cycle_node_count": len(cycle),
        "removed_count": len(removed),
        "removed": removed,
        "added": added,
    }


def analyze(points: list[Point], n: int, q: int) -> dict:
    costs = nonaxis_costs(points, n, q)
    histogram = collections.Counter(costs.values())
    first_cycle = None
    first_threshold = None
    radius_certificate = None
    for threshold in sorted(histogram):
        cycle = directed_cycle(points, costs, n, threshold)
        if cycle is not None:
            first_threshold = threshold
            first_cycle = decode_cycle(cycle, points, n)
            break
    for threshold in sorted(histogram):
        trade = shortest_alternating_trade(points, costs, n, threshold)
        if trade is None:
            continue
        radius = max(trade["removed_count"], threshold + 2)
        candidate = {
            "lower_bound_candidate": radius,
            "cost_threshold": threshold,
            "shortest_balanced_trade_at_threshold": trade,
        }
        if (
            radius_certificate is None
            or radius < radius_certificate["lower_bound_candidate"]
        ):
            radius_certificate = candidate
    values = sorted(costs.values())
    return {
        "n": n,
        "q": q,
        "empty_cell_count": len(values),
        "minimum_nonaxis_secant_cost": min(values),
        "median_nonaxis_secant_cost": values[len(values) // 2],
        "mean_nonaxis_secant_cost": sum(values) / len(values),
        "maximum_nonaxis_secant_cost": max(values),
        "cost_histogram": dict(sorted(histogram.items())),
        "minimum_bottleneck_cost_for_an_alternating_cycle": first_threshold,
        "consequent_removed_count_lower_bound": (
            first_threshold + 2 if first_threshold is not None else None
        ),
        "first_alternating_cycle": first_cycle,
        "combined_cycle_length_and_insertion_cost_lower_bound": (
            radius_certificate["lower_bound_candidate"]
            if radius_certificate is not None
            else None
        ),
        "combined_lower_bound_certificate": radius_certificate,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--n", type=int, nargs="+", required=True)
    parser.add_argument("--q", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    results = []
    for n in args.n:
        points = decode_solution(locate(args.cache, n), n)
        for q in args.q:
            results.append(analyze(points, n, q))
    payload = {"results": results}
    text = json.dumps(payload, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
