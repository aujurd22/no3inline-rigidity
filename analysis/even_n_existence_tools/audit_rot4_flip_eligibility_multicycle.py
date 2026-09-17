"""Run the exhaustive deletion/flip audit for an arbitrary factor cycle type."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from analyze_rot4_shadow_factor import SOURCE_OUTPUTS, directed_cell
from search_rot4_shadow_escape_radius import candidate_blockers


HERE = Path(__file__).resolve().parent


def ordered_components(edges: list[tuple[int, int]]) -> list[list[int]]:
    incident = defaultdict(list)
    loops = []
    for index, (u, v) in enumerate(edges):
        if u == v:
            loops.append([index])
            continue
        incident[u].append(index)
        incident[v].append(index)
    unseen = {
        index
        for index, (u, v) in enumerate(edges)
        if u != v
    }
    result = []
    while unseen:
        first = min(unseen)
        start_vertex, current_vertex = edges[first]
        previous_edge = first
        order = [first]
        while True:
            next_edges = [
                value
                for value in incident[current_vertex]
                if value != previous_edge
            ]
            assert len(next_edges) == 1
            next_edge = next_edges[0]
            if next_edge == first:
                assert current_vertex == start_vertex
                break
            order.append(next_edge)
            u, v = edges[next_edge]
            current_vertex = v if u == current_vertex else u
            previous_edge = next_edge
        unseen.difference_update(order)
        result.append(order)
    return sorted(result + loops, key=lambda value: (-len(value), value))


def mask(owners) -> int:
    return sum(1 << int(owner) for owner in owners)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument(
        "--exe", default="rot4_flip_eligibility_multicycle_exhaustive.exe"
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    edges = [tuple(value) for value in base["edges"]]
    components = ordered_components(edges)
    hitting = json.loads(
        (SOURCE_OUTPUTS / f"defect_hitting_{args.base}.json").read_text(
            encoding="utf-8"
        )
    )
    defects = [mask(value) for value in hitting["defect_owner_sets"]]
    blockers = candidate_blockers(base)
    flip_blockers = []
    for edge, bit in zip(edges, base["bits"]):
        old = directed_cell(edge, bit)
        flip_blockers.append(list(blockers[(old[1], old[0])]))

    tokens = [str(len(components))]
    for order in components:
        tokens.extend([str(len(order)), *(str(value) for value in order)])
    tokens.extend([str(len(defects)), *(str(value) for value in defects)])
    for values in flip_blockers:
        tokens.extend([str(len(values)), *(str(value) for value in values)])
    completed = subprocess.run(
        [str((HERE / args.exe).resolve())],
        input=" ".join(tokens),
        text=True,
        capture_output=True,
        check=True,
    )
    audit = json.loads(completed.stdout)
    audit["base"] = args.base
    audit["cycle_edge_orders"] = components
    audit["witness_removed_indices"] = [
        index
        for index in range(37)
        if (audit["witness_mask"] >> index) & 1
    ]
    cp_path = HERE / f"rot4_flip_eligibility_{args.base}_k12_a6_b1_c0.json"
    cp = json.loads(cp_path.read_text(encoding="utf-8"))
    audit["cp_sat_cross_check"] = {
        "status": cp["status"],
        "objective": cp["objective"],
        "agrees": cp["objective"] == audit["maximum_eligible_flips"],
    }
    assert audit["cp_sat_cross_check"]["agrees"]
    output = HERE / args.out
    output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    print(output)


if __name__ == "__main__":
    main()
