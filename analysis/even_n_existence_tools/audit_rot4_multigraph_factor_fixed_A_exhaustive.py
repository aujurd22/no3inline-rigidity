"""Direct exact fixed-k, fixed-A audit, including fully deleted factor cycles."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from analyze_rot4_shadow_factor import SOURCE_OUTPUTS
from audit_rot4_flip_eligibility_multicycle import ordered_components
from search_rot4_shadow_escape_radius import candidate_blockers


HERE = Path(__file__).resolve().parent


def owner_mask(owners) -> int:
    return sum(1 << int(owner) for owner in owners)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, default=12)
    parser.add_argument("--A", type=int, required=True)
    parser.add_argument(
        "--require-full-cycle-length",
        type=int,
        default=0,
        help="restrict to masks fully deleting the unique cycle of this length",
    )
    parser.add_argument(
        "--exe", default="rot4_multigraph_factor_multicycle_exhaustive_v5.exe"
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=None,
        help="factor archive JSON (defaults to the historical V40 archive)",
    )
    parser.add_argument(
        "--hitting",
        type=Path,
        default=None,
        help="defect-owner JSON for this base (defaults to the V40 file)",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not 1 <= args.size <= 14:
        parser.error("--size must lie in 1..14")
    if not 0 <= args.A <= args.size:
        parser.error("--A must lie in 0..size")
    started = time.time()

    archive_path = args.archive or (SOURCE_OUTPUTS / "exact_factor_archive.json")
    hitting_path = args.hitting or (
        SOURCE_OUTPUTS / f"defect_hitting_{args.base}.json"
    )
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    edges = [tuple(value) for value in base["edges"]]
    components = ordered_components(edges)
    hitting = json.loads(hitting_path.read_text(encoding="utf-8"))
    defects = [owner_mask(value) for value in hitting["defect_owner_sets"]]
    blockers = candidate_blockers(base)

    tokens = [str(len(components))]
    for order in components:
        tokens.extend([str(len(order)), *(str(value) for value in order)])
    if args.require_full_cycle_length:
        tokens.extend(
            [
                "2",
                str(args.size),
                str(args.A),
                str(args.require_full_cycle_length),
            ]
        )
    else:
        tokens.extend(["1", str(args.size), str(args.A)])
    for (u, v), bit in zip(edges, base["bits"]):
        tokens.extend([str(u), str(v), str(bit)])
    tokens.extend([str(len(defects)), *(str(value) for value in defects)])
    for u in range(37):
        for v in range(37):
            values = blockers[(u, v)]
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
    audit["first_feasible_removed_indices"] = [
        index
        for index in range(37)
        if (audit["first_feasible_mask"] >> index) & 1
    ]
    audit["method"] = {
        "k": args.size,
        "A": args.A,
        "required_full_cycle_length": (
            args.require_full_cycle_length or None
        ),
        "cycle_handling": (
            "direct local (selected-edge-count, adjacency-count) generation; "
            "empty, partially selected, and fully selected cycles are distinct"
        ),
        "normalization": "all exact old-orientation reselections forbidden",
        "multigraph": "both (u,v) and (v,u) allowed simultaneously",
        "geometry": "candidate cells filtered by exact retained-base blocker masks",
        "factor": (
            "exact deficit-0/1/2 f-factor DFS; loops consume 2 and opposite "
            "orientations may form a digon"
        ),
        "line_capacities": "none (q=0 shadow factor)",
        "archive": str(archive_path.resolve()),
        "hitting": str(hitting_path.resolve()),
    }
    audit["stderr_progress_tail"] = completed.stderr.splitlines()[-20:]
    audit["elapsed_s"] = round(time.time() - started, 3)
    output = HERE / args.out
    output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({
        "base": args.base,
        "A": args.A,
        "shapes": audit["distinct_shape_masks"],
        "hit": audit["defect_hitting_masks"],
        "q0": audit["factor_feasible_masks"],
        "max_nodes": audit["maximum_factor_search_nodes"],
        "elapsed_s": audit["elapsed_s"],
    }, indent=2))
    print(output)


if __name__ == "__main__":
    main()
