"""Verify the closed-form q=1 diagonal resource model for rot4 cells.

For N=74 and a fundamental cell (u,v), the C4 lift meets canonical diagonal
line orbits indexed by t=-c in

    t = |u-v|              (difference resource),
    t = 73-u-v             (sum resource).

The sum resource is omitted for t >= 72 because the corresponding grid line
has fewer than three points.  A loop contributes twice to resource 0; all
other listed contributions have coefficient one.  This script exhaustively
cross-checks the formula against geometric C4 lifts for all 37^2 cells.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from analyze_rot4_shadow_factor import M, N, SOURCE_OUTPUTS, c4_lifts, directed_cell
from solve_joint_rot4_general_factor import short_direction_lines


HERE = Path(__file__).resolve().parent


def formula_resources(cell: tuple[int, int]) -> Counter[int]:
    u, v = cell
    resources = Counter()
    resources[abs(u - v)] += 2 if u == v else 1
    sum_resource = N - 1 - u - v
    if sum_resource <= N - 3:
        resources[sum_resource] += 1
    return resources


def geometric_resources(cell: tuple[int, int]) -> Counter[int]:
    resources = Counter()
    for a, b, c in short_direction_lines(1):
        assert (a, b) == (1, -1)
        coefficient = sum(a * x + b * y == c for x, y in c4_lifts(cell))
        if coefficient:
            resources[-c] += coefficient
    return resources


def resource_components(cells: list[tuple[int, int]]):
    """Return path/cycle components of an ordinary non-loop resource graph."""
    edges = []
    for cell in cells:
        units = []
        for resource, count in formula_resources(cell).items():
            units.extend([resource] * count)
        if len(units) != 2 or units[0] == units[1]:
            return None
        edges.append(tuple(units))
    adjacency = defaultdict(list)
    for edge_no, (u, v) in enumerate(edges):
        adjacency[u].append((v, edge_no))
        adjacency[v].append((u, edge_no))
    seen_edges = set()
    components = []
    for edge_no, edge in enumerate(edges):
        if edge_no in seen_edges:
            continue
        stack = [edge[0]]
        vertices = set()
        component_edges = set()
        while stack:
            vertex = stack.pop()
            if vertex in vertices:
                continue
            vertices.add(vertex)
            for neighbour, index in adjacency[vertex]:
                component_edges.add(index)
                stack.append(neighbour)
        seen_edges.update(component_edges)
        kind = (
            "cycle"
            if all(len(adjacency[vertex]) == 2 for vertex in vertices)
            else "path"
        )
        components.append(
            {
                "kind": kind,
                "edge_count": len(component_edges),
                "endpoints": sorted(
                    vertex
                    for vertex in vertices
                    if len(adjacency[vertex]) == 1
                ),
            }
        )
    return sorted(
        components,
        key=lambda item: (item["kind"], item["edge_count"], item["endpoints"]),
    )


def main() -> None:
    mismatches = []
    signature_histogram = Counter()
    for u in range(M):
        for v in range(M):
            cell = (u, v)
            formula = formula_resources(cell)
            geometric = geometric_resources(cell)
            signature_histogram[
                (
                    len(formula),
                    sum(formula.values()),
                    max(formula.values()),
                )
            ] += 1
            if formula != geometric:
                mismatches.append(
                    {
                        "cell": list(cell),
                        "formula": dict(formula),
                        "geometric": dict(geometric),
                    }
                )

    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    base_profiles = []
    for base in archive["archive"]:
        if not base["id"].startswith("v40_"):
            continue
        occupancy = Counter()
        cells = [
            directed_cell(tuple(edge), bit)
            for edge, bit in zip(base["edges"], base["bits"])
        ]
        for cell in cells:
            occupancy.update(formula_resources(cell))
        components = resource_components(cells)
        base_profiles.append(
            {
                "base": base["id"],
                "max_occupancy": max(occupancy.values()),
                "occupied_resource_count": len(occupancy),
                "full_resource_count": sum(
                    value == 2 for value in occupancy.values()
                ),
                "resource_occupancy": {
                    str(key): occupancy[key] for key in sorted(occupancy)
                },
                "resource_components": components,
                "resource_component_type": (
                    "linear_forest"
                    if components is not None
                    and all(item["kind"] == "path" for item in components)
                    else "contains_cycle_or_special_edge"
                ),
            }
        )
    payload = {
        "grid_size": N,
        "fundamental_size": M,
        "canonical_q1_line_count": len(short_direction_lines(1)),
        "cell_count": M * M,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "cell_signature_histogram": {
            str(key): value for key, value in sorted(signature_histogram.items())
        },
        "base_profiles": base_profiles,
    }
    output = HERE / "rot4_q1_resource_model_audit.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "cell_count": payload["cell_count"],
                "mismatch_count": payload["mismatch_count"],
                "base_profiles": [
                    {
                        "base": item["base"],
                        "full_resource_count": item["full_resource_count"],
                    }
                    for item in base_profiles
                ],
            },
            indent=2,
        )
    )
    print(output)


if __name__ == "__main__":
    main()
