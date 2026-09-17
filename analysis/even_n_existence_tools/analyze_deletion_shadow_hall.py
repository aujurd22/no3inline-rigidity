"""Analyze the exact Hall board induced by a proposed deletion set.

For an exact saturated NTIL set S and R subset S, define E_R to be the
originally empty cells that do not lie on a protected secant of S\\R.  If
a_x and b_y are the numbers of removed points in row x and column y, then an
old-old-new-safe balanced switch with deletion set exactly R exists iff E_R
contains a simple bipartite b-matching with row degrees a_x and column degrees
b_y.

This script constructs that board, computes a maximum flow, reports a
minimum-cut Hall witness when deficient, and checks any added set carried by
the input switch JSON.
"""

from __future__ import annotations

import argparse
import collections
import json
from dataclasses import dataclass
from pathlib import Path

from analyze_large_prime_carries import decode_solution, locate
from analyze_switch_scale_safety import secant_index


Point = tuple[int, int]


@dataclass
class Edge:
    target: int
    reverse: int
    capacity: int


class Dinic:
    def __init__(self, size: int) -> None:
        self.graph: list[list[Edge]] = [[] for _ in range(size)]

    def add_edge(self, source: int, target: int, capacity: int) -> None:
        forward = Edge(target, len(self.graph[target]), capacity)
        reverse = Edge(source, len(self.graph[source]), 0)
        self.graph[source].append(forward)
        self.graph[target].append(reverse)

    def maximum_flow(self, source: int, sink: int) -> int:
        total = 0
        while True:
            level = [-1] * len(self.graph)
            level[source] = 0
            queue = collections.deque([source])
            while queue:
                node = queue.popleft()
                for edge in self.graph[node]:
                    if edge.capacity and level[edge.target] < 0:
                        level[edge.target] = level[node] + 1
                        queue.append(edge.target)
            if level[sink] < 0:
                return total
            cursor = [0] * len(self.graph)

            def send(node: int, amount: int) -> int:
                if node == sink:
                    return amount
                while cursor[node] < len(self.graph[node]):
                    edge = self.graph[node][cursor[node]]
                    if edge.capacity and level[edge.target] == level[node] + 1:
                        pushed = send(edge.target, min(amount, edge.capacity))
                        if pushed:
                            edge.capacity -= pushed
                            self.graph[edge.target][edge.reverse].capacity += pushed
                            return pushed
                    cursor[node] += 1
                return 0

            while pushed := send(source, 10**9):
                total += pushed

    def residual_reachable(self, source: int) -> set[int]:
        seen = {source}
        queue = collections.deque([source])
        while queue:
            node = queue.popleft()
            for edge in self.graph[node]:
                if edge.capacity and edge.target not in seen:
                    seen.add(edge.target)
                    queue.append(edge.target)
        return seen


def analyze(
    original: list[Point],
    removed: list[Point],
    added: list[Point] | None,
    n: int,
    q: int,
) -> dict:
    original_set = set(original)
    removed_set = set(removed)
    if not removed_set <= original_set:
        raise ValueError("the deletion set is not a subset of the original")
    retained = [point for point in original if point not in removed_set]
    row_demand = collections.Counter(row for row, _ in removed)
    column_demand = collections.Counter(column for _, column in removed)

    blocked = set()
    secants = secant_index(retained, n)
    for cell, pairs in secants.items():
        if any(scale < q for _, _, scale in pairs):
            blocked.add(cell)
    allowed = {
        (row, column)
        for row in range(n)
        for column in range(n)
        if (row, column) not in original_set
        and (row, column) not in blocked
        and row_demand[row]
        and column_demand[column]
    }

    active_rows = sorted(row_demand)
    active_columns = sorted(column_demand)
    source = 0
    row_offset = 1
    column_offset = row_offset + len(active_rows)
    sink = column_offset + len(active_columns)
    flow = Dinic(sink + 1)
    row_node = {
        row: row_offset + index for index, row in enumerate(active_rows)
    }
    column_node = {
        column: column_offset + index
        for index, column in enumerate(active_columns)
    }
    for row in active_rows:
        flow.add_edge(source, row_node[row], row_demand[row])
    for row, column in allowed:
        flow.add_edge(row_node[row], column_node[column], 1)
    for column in active_columns:
        flow.add_edge(column_node[column], sink, column_demand[column])

    maximum_flow = flow.maximum_flow(source, sink)
    reachable = flow.residual_reachable(source)
    deficient_rows = [
        row for row in active_rows if row_node[row] in reachable
    ]
    cut_columns = [
        column for column in active_columns if column_node[column] in reachable
    ]
    degrees_by_row = collections.Counter(row for row, _ in allowed)
    degrees_by_column = collections.Counter(column for _, column in allowed)

    result = {
        "n": n,
        "q": q,
        "removed_count": len(removed),
        "retained_count": len(retained),
        "protected_secant_shadow_cell_count": len(blocked),
        "active_row_count": len(active_rows),
        "active_column_count": len(active_columns),
        "allowed_active_board_edge_count": len(allowed),
        "allowed_active_board_density": (
            len(allowed) / (len(active_rows) * len(active_columns))
            if active_rows and active_columns
            else 0
        ),
        "minimum_allowed_degree_on_active_rows": min(
            (degrees_by_row[row] for row in active_rows), default=0
        ),
        "minimum_allowed_degree_on_active_columns": min(
            (degrees_by_column[column] for column in active_columns), default=0
        ),
        "total_demand": len(removed),
        "maximum_b_matching_flow": maximum_flow,
        "hall_feasible": maximum_flow == len(removed),
        "residual_min_cut_reachable_rows": deficient_rows,
        "residual_min_cut_reachable_columns": cut_columns,
        "row_demand": dict(sorted(row_demand.items())),
        "column_demand": dict(sorted(column_demand.items())),
    }
    if added is not None:
        added_set = set(added)
        result["provided_added_count"] = len(added)
        result["provided_additions_all_allowed"] = added_set <= allowed
        result["provided_additions_realize_demands"] = (
            collections.Counter(row for row, _ in added) == row_demand
            and collections.Counter(column for _, column in added)
            == column_demand
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--switch-json", type=Path, nargs="+", required=True)
    parser.add_argument("--q", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    results = []
    for path in args.switch_json:
        payload = json.loads(path.read_text())
        n = int(payload["n"])
        original = decode_solution(locate(args.cache, n), n)
        q = args.q if args.q is not None else int(payload.get("q", n))
        result = analyze(
            original=original,
            removed=[tuple(point) for point in payload["removed"]],
            added=[tuple(point) for point in payload.get("added", [])],
            n=n,
            q=q,
        )
        result["source_switch_json"] = str(path)
        results.append(result)
    encoded = json.dumps({"results": results}, indent=2)
    print(encoded)
    if args.output:
        args.output.write_text(encoded)


if __name__ == "__main__":
    main()
