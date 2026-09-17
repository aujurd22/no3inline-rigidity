"""Inspect the cycle structure of known quarter-turn NTIL solutions.

For an even grid N=2m, a C4-symmetric saturated configuration has exactly
m points in the north-west m by m fundamental square.  Regard a cell (u,v)
as a directed edge u -> v on m vertices.  The row/column saturation identity

    out_degree(i) + in_degree(i) = 2

makes the underlying multigraph 2-regular, hence a disjoint union of cycles
(a loop is a one-cycle and two parallel edges form a two-cycle).

This script decodes Flammenkamp's compact files and records those cycles.  It
is intentionally read-only: it is a pattern finder, not a solver.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path


ALPHABET = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "#$%&@?!()[]<>{}=*+|-/~^_:;,.|"
)
VALUE = {character: index for index, character in enumerate(ALPHABET)}
SYMMETRY_MARKERS = set(".:/-ocx+*")


def decode_first(path: Path, n: int) -> list[tuple[int, int]]:
    line = next(text.strip() for text in path.read_text().splitlines() if text.strip())
    body = line[1:] if line[0] in SYMMETRY_MARKERS else line
    if len(body) < 2 * n:
        raise ValueError(f"{path}: compact record has only {len(body)} symbols")
    return [
        (row, VALUE[body[2 * row + offset]])
        for row in range(n)
        for offset in (0, 1)
    ]


def decode_record(text: str, n: int, coordinate_format: bool) -> list[tuple[int, int]]:
    text = text.strip()
    if coordinate_format:
        values = [int(value) for value in text.split()]
        if len(values) != 4 * n:
            raise ValueError(
                f"n={n}: coordinate record has {len(values)} rather than {4*n} integers"
            )
        return list(zip(values[::2], values[1::2]))
    body = text[1:] if text[0] in SYMMETRY_MARKERS else text
    if len(body) < 2 * n:
        raise ValueError(f"n={n}: compact record has only {len(body)} symbols")
    return [
        (row, VALUE[body[2 * row + offset]])
        for row in range(n)
        for offset in (0, 1)
    ]


def rotate(point: tuple[int, int], n: int) -> tuple[int, int]:
    x, y = point
    return n - 1 - y, x


def validate_c4(points: list[tuple[int, int]], n: int) -> None:
    point_set = set(points)
    if len(point_set) != 2 * n:
        raise ValueError(f"n={n}: expected {2*n} distinct points")
    if {rotate(point, n) for point in point_set} != point_set:
        raise ValueError(f"n={n}: record is not invariant under quarter turn")
    rows = collections.Counter(x for x, _ in point_set)
    columns = collections.Counter(y for _, y in point_set)
    if any(rows[i] != 2 or columns[i] != 2 for i in range(n)):
        raise ValueError(f"n={n}: record does not saturate every row and column")


def fundamental_cycles(
    points: list[tuple[int, int]], n: int
) -> tuple[list[tuple[int, int]], list[dict]]:
    m = n // 2
    edges = sorted((x, y) for x, y in points if x < m and y < m)
    if len(edges) != m:
        raise ValueError(f"n={n}: fundamental square has {len(edges)} rather than {m} cells")

    incidence: list[list[int]] = [[] for _ in range(m)]
    for edge_id, (u, v) in enumerate(edges):
        # A loop has two incidences at its vertex.
        incidence[u].append(edge_id)
        incidence[v].append(edge_id)
    if any(len(bucket) != 2 for bucket in incidence):
        raise ValueError(
            f"n={n}: total-degree identity failed: {[len(x) for x in incidence]}"
        )

    unseen = set(range(len(edges)))
    cycles: list[dict] = []
    while unseen:
        first_edge = min(unseen)
        u0, v0 = edges[first_edge]
        if u0 == v0:
            unseen.remove(first_edge)
            cycles.append(
                {
                    "length": 1,
                    "vertices": [u0],
                    "edge_ids": [first_edge],
                    "orientation_word": "L",
                }
            )
            continue

        vertices = [u0]
        edge_ids: list[int] = []
        orientation: list[str] = []
        current_vertex = u0
        current_edge = first_edge
        while True:
            unseen.remove(current_edge)
            edge_ids.append(current_edge)
            a, b = edges[current_edge]
            if a == current_vertex:
                next_vertex = b
                orientation.append("+")
            elif b == current_vertex:
                next_vertex = a
                orientation.append("-")
            else:
                raise AssertionError("walk lost incidence")
            if next_vertex == vertices[0]:
                break
            vertices.append(next_vertex)
            candidates = [edge for edge in incidence[next_vertex] if edge != current_edge]
            if len(candidates) != 1:
                raise AssertionError("2-regular walk did not have a unique continuation")
            current_vertex = next_vertex
            current_edge = candidates[0]

        cycles.append(
            {
                "length": len(edge_ids),
                "vertices": vertices,
                "edge_ids": edge_ids,
                "orientation_word": "".join(orientation),
            }
        )
    cycles.sort(key=lambda item: (-item["length"], item["vertices"]))
    return edges, cycles


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--minimum-n", type=int, default=2)
    parser.add_argument("--maximum-n", type=int, default=10_000)
    parser.add_argument("--include-edges", action="store_true")
    parser.add_argument(
        "--scan-all",
        action="store_true",
        help="summarise every record in every rot4/.few/.mvr file",
    )
    args = parser.parse_args()

    records = []
    pattern = re.compile(r"^n(\d+)_rot4(?:\.(?:few|mvr))?$")
    if args.scan_all:
        summaries: dict[int, dict] = {}
        for path in sorted(args.cache.iterdir()):
            match = pattern.match(path.name)
            if not match:
                continue
            n = int(match.group(1))
            if n % 2 or not (args.minimum_n <= n <= args.maximum_n):
                continue
            m = n // 2
            summary = summaries.setdefault(
                n,
                {
                    "n": n,
                    "m": m,
                    "records": 0,
                    "sources": [],
                    "minimum_cycle_count": m,
                    "maximum_cycle_length": 0,
                    "hamiltonian_records": 0,
                    "hamiltonian_plus_loops_records": 0,
                    "cycle_partition_histogram": collections.Counter(),
                    "first_hamiltonian": None,
                },
            )
            summary["sources"].append(str(path))
            coordinate_format = path.suffix == ".mvr"
            for line_number, text in enumerate(path.read_text().splitlines(), 1):
                if not text.strip():
                    continue
                points = decode_record(text, n, coordinate_format)
                validate_c4(points, n)
                edges, cycles = fundamental_cycles(points, n)
                lengths = tuple(cycle["length"] for cycle in cycles)
                summary["records"] += 1
                summary["minimum_cycle_count"] = min(
                    summary["minimum_cycle_count"], len(cycles)
                )
                summary["maximum_cycle_length"] = max(
                    summary["maximum_cycle_length"], lengths[0]
                )
                summary["cycle_partition_histogram"]["+".join(map(str, lengths))] += 1
                if lengths == (m,):
                    summary["hamiltonian_records"] += 1
                    if summary["first_hamiltonian"] is None:
                        summary["first_hamiltonian"] = {
                            "source": str(path),
                            "line": line_number,
                            "edges": edges,
                            "cycle": cycles[0],
                        }
                if lengths and lengths[0] + sum(
                    length for length in lengths[1:] if length == 1
                ) == m and all(length == 1 for length in lengths[1:]):
                    summary["hamiltonian_plus_loops_records"] += 1

        serialisable = []
        for _, summary in sorted(summaries.items()):
            summary["cycle_partition_histogram"] = dict(
                summary["cycle_partition_histogram"].most_common()
            )
            serialisable.append(summary)
        print(json.dumps(serialisable, indent=2))
        return

    chosen: dict[int, Path] = {}
    # Prefer a full file to a .few file if both exist.
    for path in sorted(args.cache.iterdir(), key=lambda p: (p.name.endswith(".few"), p.name)):
        match = pattern.match(path.name)
        if not match:
            continue
        n = int(match.group(1))
        if n % 2 or not (args.minimum_n <= n <= args.maximum_n):
            continue
        chosen.setdefault(n, path)

    for n, path in sorted(chosen.items()):
        points = decode_first(path, n)
        validate_c4(points, n)
        edges, cycles = fundamental_cycles(points, n)
        record = {
            "n": n,
            "m": n // 2,
            "source": str(path),
            "cycle_lengths": [cycle["length"] for cycle in cycles],
            "cycle_count": len(cycles),
            "loop_count": sum(cycle["length"] == 1 for cycle in cycles),
            "two_cycle_count": sum(cycle["length"] == 2 for cycle in cycles),
            "orientation_words": [cycle["orientation_word"] for cycle in cycles],
            "cycles": cycles,
        }
        if args.include_edges:
            record["fundamental_edges"] = edges
        records.append(record)

    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
