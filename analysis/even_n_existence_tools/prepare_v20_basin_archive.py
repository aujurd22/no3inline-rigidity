"""Extract, independently verify, and archive every known m=37 V=20 basin."""

from __future__ import annotations

import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


M = 37
N = 2 * M
HERE = Path(__file__).resolve().parent
ISING_OUT = HERE.parent / "ising_m37" / "outputs"


def c4_lifts(cell: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    x, y = cell
    result = []
    for _ in range(4):
        result.append((x, y))
        x, y = N - 1 - y, x
    return tuple(result)


def rotate(point: tuple[int, int]) -> tuple[int, int]:
    return N - 1 - point[1], point[0]


def canonical_triple(
    triple: tuple[tuple[int, int], tuple[int, int], tuple[int, int]]
) -> tuple[tuple[int, int], ...]:
    values = []
    current = tuple(sorted(triple))
    for _ in range(4):
        values.append(current)
        current = tuple(sorted(rotate(point) for point in current))
    return min(values)


def line_key(
    p: tuple[int, int], q: tuple[int, int]
) -> tuple[int, int, int]:
    dx, dy = q[0] - p[0], q[1] - p[1]
    if dx == 0 and dy == 0:
        raise ValueError("duplicate point")
    divisor = math.gcd(abs(dx), abs(dy))
    a, b = dy // divisor, -dx // divisor
    if a < 0 or (a == 0 and b < 0):
        a, b = -a, -b
    return a, b, a * p[0] + b * p[1]


def normalize_edges(values) -> list[tuple[int, int]]:
    result = []
    for value in values:
        if isinstance(value, str):
            u, v = map(int, value.split())
        else:
            u, v = map(int, value)
        result.append((u, v))
    return result


def directed_cells(
    edges: list[tuple[int, int]], bits: list[int]
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (v, u) if int(bit) else (u, v)
        for (u, v), bit in zip(edges, bits)
    )


def factor_components(edges: list[tuple[int, int]]) -> list[list[int]]:
    loops = [[index] for index, (u, v) in enumerate(edges) if u == v]
    incident: dict[int, list[int]] = defaultdict(list)
    unseen = set()
    for index, (u, v) in enumerate(edges):
        if u == v:
            continue
        incident[u].append(index)
        incident[v].append(index)
        unseen.add(index)
    if any(len(values) not in (0, 2) for values in incident.values()):
        raise AssertionError("non-loop factor degree is not 0 or 2")
    cycles = []
    while unseen:
        first = min(unseen)
        start, current = edges[first]
        previous = first
        order = [first]
        while True:
            candidates = [
                edge for edge in incident[current] if edge != previous
            ]
            if len(candidates) != 1:
                raise AssertionError("factor traversal is not unique")
            following = candidates[0]
            if following == first:
                if current != start:
                    raise AssertionError("factor cycle closed at wrong vertex")
                break
            order.append(following)
            u, v = edges[following]
            current = v if u == current else u
            previous = following
        unseen.difference_update(order)
        cycles.append(order)
    return sorted(cycles + loops, key=lambda value: (-len(value), value))


def validate_factor(edges: list[tuple[int, int]]) -> dict:
    if len(edges) != M:
        raise AssertionError("factor does not have 37 edges")
    degree = Counter()
    unordered = set()
    for u, v in edges:
        if not 0 <= u < M or not 0 <= v < M:
            raise AssertionError("factor endpoint outside 0..36")
        key = (min(u, v), max(u, v))
        if key in unordered:
            raise AssertionError("duplicate unordered factor edge")
        unordered.add(key)
        if u == v:
            degree[u] += 2
        else:
            degree[u] += 1
            degree[v] += 1
    if any(degree[vertex] != 2 for vertex in range(M)):
        raise AssertionError("factor is not degree two")
    components = factor_components(edges)
    return {
        "edge_count": len(edges),
        "loop_count": sum(u == v for u, v in edges),
        "cycle_lengths": [len(component) for component in components],
        "components": components,
    }


def geometry_and_defects(
    edges: list[tuple[int, int]], bits: list[int]
) -> tuple[dict, list[list[int]]]:
    points = []
    owners = []
    for owner, cell in enumerate(directed_cells(edges, bits)):
        orbit = c4_lifts(cell)
        points.extend(orbit)
        owners.extend([owner] * 4)
    if len(points) != 148 or len(set(points)) != 148:
        raise AssertionError("V20 point set is not 148 distinct points")

    line_members: dict[tuple[int, int, int], set[int]] = defaultdict(set)
    for i, j in itertools.combinations(range(len(points)), 2):
        key = line_key(points[i], points[j])
        line_members[key].update((i, j))
    bad_lines = {
        key: tuple(sorted(members))
        for key, members in line_members.items()
        if len(members) >= 3
    }
    bad_triples = []
    orbit_owners: dict[tuple[tuple[int, int], ...], tuple[int, ...]] = {}
    for members in bad_lines.values():
        for i, j, k in itertools.combinations(members, 3):
            triple = (points[i], points[j], points[k])
            bad_triples.append(triple)
            canonical = canonical_triple(triple)
            owner_set = tuple(sorted({owners[i], owners[j], owners[k]}))
            previous = orbit_owners.setdefault(canonical, owner_set)
            if previous != owner_set:
                raise AssertionError("rotated defect changed owner set")
    geometry = {
        "point_count": len(points),
        "distinct_point_count": len(set(points)),
        "bad_triples": len(bad_triples),
        "bad_line_count": len(bad_lines),
        "max_points_on_line": max(map(len, bad_lines.values()), default=2),
        "defect_orbit_count": len(orbit_owners),
    }
    return geometry, [list(value) for value in orbit_owners.values()]


def minimum_hitting_set(
    edges: list[tuple[int, int]],
    defects: list[list[int]],
    independent: bool,
) -> dict:
    for size in range(M + 1):
        for chosen in itertools.combinations(range(M), size):
            if independent:
                used = set()
                valid = True
                for index in chosen:
                    u, v = edges[index]
                    endpoints = {u, v}
                    if used & endpoints:
                        valid = False
                        break
                    used.update(endpoints)
                if not valid:
                    continue
            if all(set(chosen) & set(defect) for defect in defects):
                return {
                    "status": "OPTIMAL_BY_EXHAUSTIVE_SIZE_ORDER",
                    "independent": independent,
                    "size": size,
                    "indices": list(chosen),
                    "edges": [list(edges[index]) for index in chosen],
                }
    raise AssertionError("defects have no hitting set")


def candidate_items():
    paths = sorted(ISING_OUT.glob("*factor_optima*.json"))
    paths.append(ISING_OUT / "m37_gpu_v20_factor_optimum.json")
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload.get("results", [payload])
        for item in items:
            solve = item.get("solve", {})
            if solve.get("violations") != 20:
                continue
            edges = normalize_edges(item.get("edges", []))
            bits = solve.get("bits") or item.get("hint_bits")
            if len(edges) != M or bits is None or len(bits) != M:
                continue
            yield path.name, item, edges, [int(value) for value in bits]


def main() -> None:
    by_cells = {}
    for source, item, edges, bits in candidate_items():
        cells = tuple(sorted(directed_cells(edges, bits)))
        record = by_cells.setdefault(
            cells,
            {
                "sources": [],
                "edges": edges,
                "bits": bits,
                "hint_defects": [],
            },
        )
        record["sources"].append({
            "file": source,
            "rank": item.get("rank"),
        })
        if item.get("hint_defect") is not None:
            record["hint_defects"].append(int(item["hint_defect"]))

    archive = []
    hitting_payloads = {}
    for number, (cells, record) in enumerate(sorted(by_cells.items()), 1):
        base_id = f"v20_{number:02d}"
        edges = record["edges"]
        bits = record["bits"]
        factor = validate_factor(edges)
        geometry, defects = geometry_and_defects(edges, bits)
        if geometry != {
            "point_count": 148,
            "distinct_point_count": 148,
            "bad_triples": 20,
            "bad_line_count": 20,
            "max_points_on_line": 3,
            "defect_orbit_count": 5,
        }:
            raise AssertionError((base_id, geometry))
        hotness = Counter(index for defect in defects for index in defect)
        hitting = {
            "base": base_id,
            "edges": [list(edge) for edge in edges],
            "bits": bits,
            "defect_owner_sets": defects,
            "hotness_by_defect_orbit": dict(hotness),
            "minimum_hitting_set": minimum_hitting_set(
                edges, defects, False
            ),
            "minimum_independent_hitting_set": minimum_hitting_set(
                edges, defects, True
            ),
        }
        hitting_payloads[base_id] = hitting
        archive.append({
            "id": base_id,
            "value": 20,
            "edges": [list(edge) for edge in edges],
            "bits": bits,
            "directed_cells": [list(cell) for cell in cells],
            "factor": factor,
            "geometry": geometry,
            "sources": record["sources"],
            "hint_defects": sorted(set(record["hint_defects"])),
        })

    if len(archive) != 6:
        raise AssertionError(f"expected six V20 basins, found {len(archive)}")
    output = {
        "statement": (
            "All distinct verified V=20 directed rot4 configurations found "
            "in the ising_m37 exact-orientation outputs."
        ),
        "source_directory": str(ISING_OUT),
        "archive_size": len(archive),
        "all_geometry_rechecked": True,
        "all_factors_rechecked": True,
        "cycle_type_histogram": dict(Counter(
            "+".join(map(str, item["factor"]["cycle_lengths"]))
            for item in archive
        )),
        "archive": archive,
    }
    archive_path = HERE / "v20_basin_archive.json"
    archive_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    for base_id, hitting in hitting_payloads.items():
        (HERE / f"v20_defect_hitting_{base_id}.json").write_text(
            json.dumps(hitting, indent=2), encoding="utf-8"
        )
    print(json.dumps({
        "archive_size": len(archive),
        "cycle_type_histogram": output["cycle_type_histogram"],
        "bases": [
            {
                "id": item["id"],
                "cycles": item["factor"]["cycle_lengths"],
                "minimum_hitting_size": hitting_payloads[item["id"]][
                    "minimum_hitting_set"
                ]["size"],
                "minimum_independent_hitting_size": hitting_payloads[
                    item["id"]
                ]["minimum_independent_hitting_set"]["size"],
            }
            for item in archive
        ],
    }, indent=2))
    print(archive_path)


if __name__ == "__main__":
    main()
