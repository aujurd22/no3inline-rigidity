"""Structural comparison of all exactly solved V=40 basins."""

from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path

from defect_orbit_analysis import canonical_triple, slope_type
from signed_nae_core import c4_lifts


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def cycle_lengths(edges):
    adjacency = {vertex: [] for vertex in range(37)}
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)
    unseen = set(range(37))
    lengths = []
    while unseen:
        start = min(unseen)
        previous = None
        current = start
        length = 0
        while True:
            unseen.discard(current)
            length += 1
            choices = [vertex for vertex in adjacency[current] if vertex != previous]
            nxt = choices[0]
            if nxt == start:
                break
            previous, current = current, nxt
        lengths.append(length)
    return sorted(lengths)


def defects(item):
    points = []
    owners = []
    for owner, (edge, bit) in enumerate(zip(item["edges"], item["bits"])):
        u, v = edge
        orbit = c4_lifts(37, (u, v) if bit == 0 else (v, u))
        points.extend(orbit)
        owners.extend([owner] * 4)
    result = {}
    for i, j, k in itertools.combinations(range(148), 3):
        p, q, r = points[i], points[j], points[k]
        det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        if det:
            continue
        key = canonical_triple((p, q, r))
        result.setdefault(
            key,
            {
                "points": [list(point) for point in key],
                "slope_type": list(slope_type(key)),
                "owner_arity": len({owners[i], owners[j], owners[k]}),
            },
        )
    return result


def oriented_cells(item):
    return {
        (edge[0], edge[1]) if bit == 0 else (edge[1], edge[0])
        for edge, bit in zip(item["edges"], item["bits"])
    }


def main():
    archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    basins = [item for item in archive["archive"] if item["value"] == 40]
    details = []
    defect_maps = {}
    for item in basins:
        dmap = defects(item)
        defect_maps[item["id"]] = dmap
        slope_counts = Counter(tuple(value["slope_type"]) for value in dmap.values())
        arity_counts = Counter(value["owner_arity"] for value in dmap.values())
        details.append(
            {
                "id": item["id"],
                "sources": item["sources"],
                "cycle_lengths": cycle_lengths([tuple(edge) for edge in item["edges"]]),
                "defect_orbits": len(dmap),
                "owner_arity_counts": dict(sorted(arity_counts.items())),
                "slope_type_counts": {
                    f"{a},{b}": count for (a, b), count in sorted(slope_counts.items())
                },
                "defects": list(dmap.values()),
            }
        )

    pairwise = []
    for left, right in itertools.combinations(basins, 2):
        le = {tuple(edge) for edge in left["edges"]}
        re = {tuple(edge) for edge in right["edges"]}
        lc, rc = oriented_cells(left), oriented_cells(right)
        ld, rd = set(defect_maps[left["id"]]), set(defect_maps[right["id"]])
        ls = {tuple(value["slope_type"]) for value in defect_maps[left["id"]].values()}
        rs = {tuple(value["slope_type"]) for value in defect_maps[right["id"]].values()}
        pairwise.append(
            {
                "left": left["id"],
                "right": right["id"],
                "edge_distance": 37 - len(le & re),
                "oriented_cell_distance": 37 - len(lc & rc),
                "shared_exact_defect_orbits": len(ld & rd),
                "shared_slope_types": len(ls & rs),
                "slope_jaccard": len(ls & rs) / len(ls | rs),
            }
        )
    edge_sets = [{tuple(edge) for edge in item["edges"]} for item in basins]
    cell_sets = [oriented_cells(item) for item in basins]
    defect_sets = [set(defect_maps[item["id"]]) for item in basins]
    slope_sets = [
        {tuple(value["slope_type"]) for value in defect_maps[item["id"]].values()}
        for item in basins
    ]
    payload = {
        "basin_count": len(basins),
        "common_undirected_edges": [list(edge) for edge in sorted(set.intersection(*edge_sets))],
        "common_oriented_cells": [list(cell) for cell in sorted(set.intersection(*cell_sets))],
        "common_exact_defect_orbits": len(set.intersection(*defect_sets)),
        "common_slope_types": [list(item) for item in sorted(set.intersection(*slope_sets))],
        "union_slope_type_count": len(set.union(*slope_sets)),
        "pairwise": pairwise,
        "basins": details,
    }
    path = OUT / "v40_basin_comparison.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"basins={len(basins)} common_edges={len(payload['common_undirected_edges'])} "
        f"common_cells={len(payload['common_oriented_cells'])} "
        f"common_defects={payload['common_exact_defect_orbits']} "
        f"common_slopes={payload['common_slope_types']} "
        f"union_slopes={payload['union_slope_type_count']}"
    )
    for item in details:
        print(
            item["id"],
            "cycles=", item["cycle_lengths"],
            "arity=", item["owner_arity_counts"],
            "slopes=", item["slope_type_counts"],
        )
    for item in pairwise:
        print(item)
    print(path)


if __name__ == "__main__":
    main()
