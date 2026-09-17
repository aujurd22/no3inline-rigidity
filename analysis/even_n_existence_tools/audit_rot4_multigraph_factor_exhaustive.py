"""Feed a V40 basin into the exhaustive corrected q=0 factor enumerator."""

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
    parser.add_argument(
        "--exe", default="rot4_multigraph_factor_multicycle_exhaustive_v4.exe"
    )
    parser.add_argument(
        "--runs",
        default="3,2,2,2,2,1",
        help="comma-separated deletion run lengths",
    )
    parser.add_argument("--size", type=int, default=12)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    started = time.time()

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
    defects = [owner_mask(value) for value in hitting["defect_owner_sets"]]
    blockers = candidate_blockers(base)
    run_lengths = sorted(
        (int(value) for value in args.runs.split(",")),
        reverse=True,
    )
    if not 1 <= args.size <= 12:
        parser.error("--size must lie in 1..12")
    if sum(run_lengths) != args.size:
        parser.error(f"--runs must contain positive lengths summing to {args.size}")
    if min(run_lengths) < 1 or max(run_lengths) > 12:
        parser.error("run lengths must lie in 1..12")
    run_profile = [
        sum(length == value for length in run_lengths)
        for value in range(1, 13)
    ]

    tokens = [str(len(components))]
    for order in components:
        tokens.extend([str(len(order)), *(str(value) for value in order)])
    tokens.append("0")
    tokens.extend(str(value) for value in run_profile)
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
        "deletion_run_lengths": run_lengths,
        "k": args.size,
        "normalization": "all exact old-orientation reselections forbidden",
        "multigraph": "both (u,v) and (v,u) allowed simultaneously",
        "geometry": "candidate cells filtered by exact retained-base blocker masks",
        "factor": (
            "exact deficit-0/1/2 f-factor DFS; loops consume 2 and opposite "
            "orientations may form a digon"
        ),
        "line_capacities": "none (q=0 shadow factor)",
    }
    audit["stderr_progress_tail"] = completed.stderr.splitlines()[-20:]
    audit["elapsed_s"] = round(time.time() - started, 3)
    output = HERE / args.out
    output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    print(output)


if __name__ == "__main__":
    main()
