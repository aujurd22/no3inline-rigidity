"""Feed one 37-cycle basin into the exhaustive C++ flip audit."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from analyze_rot4_shadow_factor import SOURCE_OUTPUTS, directed_cell
from search_rot4_shadow_escape_radius import candidate_blockers


HERE = Path(__file__).resolve().parent


def owner_mask(owners) -> int:
    return sum(1 << int(owner) for owner in owners)


def cycle_edge_order(edges: list[tuple[int, int]]) -> list[int]:
    incident = defaultdict(list)
    for index, (u, v) in enumerate(edges):
        incident[u].append(index)
        incident[v].append(index)
    assert all(len(value) == 2 for value in incident.values())
    order = [0]
    previous_edge = 0
    previous_vertex, current_vertex = edges[0]
    while len(order) < len(edges):
        candidates = [
            index for index in incident[current_vertex] if index != previous_edge
        ]
        assert len(candidates) == 1
        next_edge = candidates[0]
        order.append(next_edge)
        u, v = edges[next_edge]
        next_vertex = v if u == current_vertex else u
        previous_edge, previous_vertex, current_vertex = (
            next_edge,
            current_vertex,
            next_vertex,
        )
    assert current_vertex == edges[0][0]
    assert len(set(order)) == len(edges)
    return order


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument(
        "--exe", default="rot4_flip_eligibility_exhaustive.exe"
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    edges = [tuple(edge) for edge in base["edges"]]
    order = cycle_edge_order(edges)
    hitting = json.loads(
        (SOURCE_OUTPUTS / f"defect_hitting_{args.base}.json").read_text(
            encoding="utf-8"
        )
    )
    defects = [owner_mask(value) for value in hitting["defect_owner_sets"]]
    blockers = candidate_blockers(base)
    flip_blockers = []
    for edge, bit in zip(edges, base["bits"]):
        old = directed_cell(edge, bit)
        reverse = (old[1], old[0])
        flip_blockers.append(list(blockers[reverse]))

    tokens = [str(len(edges)), *(str(value) for value in order)]
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
    audit["cycle_edge_order"] = order
    audit["witness_removed_indices"] = [
        index
        for index in range(37)
        if (audit["witness_mask"] >> index) & 1
    ]
    cp_path = HERE / f"rot4_flip_eligibility_{args.base}_k12_a6_b1_c0.json"
    if cp_path.exists():
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
