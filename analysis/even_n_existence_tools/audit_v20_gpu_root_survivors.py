"""Run the exact CPU q=0 factor DFS only on CUDA root-option survivors."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from audit_rot4_flip_eligibility_multicycle import ordered_components
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import short_direction_lines


HERE = Path(__file__).resolve().parent


def owner_mask(owners) -> int:
    return sum(1 << int(owner) for owner in owners)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--gpu", required=True)
    parser.add_argument(
        "--source-field",
        choices=("survivor_masks", "feasible_masks"),
        default="survivor_masks",
    )
    parser.add_argument("--short-direction-q", type=int, default=0)
    parser.add_argument(
        "--exe", default="rot4_multigraph_factor_multicycle_exhaustive_v9.exe"
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    started = time.time()

    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    hitting = json.loads(
        (HERE / f"v20_defect_hitting_{args.base}.json").read_text()
    )
    gpu = json.loads((HERE / args.gpu).read_text())
    masks = [int(value) for value in gpu[args.source_field]]
    if args.source_field == "survivor_masks":
        if not gpu["survivor_masks_complete"]:
            raise RuntimeError("GPU survivor buffer overflowed")
        if gpu["root_nonzero_count"] != len(masks):
            raise RuntimeError(
                "GPU survivor count does not match the stored masks"
            )
    elif gpu["factor_feasible_masks"] != len(masks):
        raise RuntimeError("q=0 source does not contain every feasible mask")

    edges = [tuple(value) for value in base["edges"]]
    components = ordered_components(edges)
    defects = [owner_mask(value) for value in hitting["defect_owner_sets"]]
    blockers = candidate_blockers(base)
    tokens = [str(len(components))]
    for order in components:
        tokens.extend([str(len(order)), *(str(value) for value in order)])
    tokens.extend(
        ["3", str(args.size), str(len(masks)), *(str(mask) for mask in masks)]
    )
    for (u, v), bit in zip(edges, base["bits"]):
        tokens.extend([str(u), str(v), str(bit)])
    tokens.extend([str(len(defects)), *(str(value) for value in defects)])
    for u in range(37):
        for v in range(37):
            values = blockers[(u, v)]
            tokens.extend([str(len(values)), *(str(value) for value in values)])
    line_keys = short_direction_lines(args.short_direction_q)
    tokens.extend([str(len(line_keys))])
    for key in line_keys:
        tokens.extend(str(value) for value in key)

    completed = subprocess.run(
        [str((HERE / args.exe).resolve())],
        input=" ".join(tokens),
        text=True,
        capture_output=True,
        check=True,
    )
    audit = json.loads(completed.stdout)
    audit.update(
        {
            "base": args.base,
            "source_certificate": args.gpu,
            "source_field": args.source_field,
            "source_root_nonzero_by_adjacency": gpu.get(
                "root_nonzero_by_adjacency"
            ),
            "method": {
                "name": (
                    "CUDA exhaustive fixed-weight mask scan and exact "
                    "root-option filter, followed by C++ exact deficit "
                    "f-factor DFS"
                ),
                "k": args.size,
                "normalization": "all exact old-orientation reselections forbidden",
                "line_capacities": (
                    f"all primitive non-axis directions with q<="
                    f"{args.short_direction_q}"
                ),
            },
            "elapsed_s": round(time.time() - started, 4),
        }
    )
    output = HERE / args.out
    output.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    summary = {
        "base": args.base,
        "source_masks": len(masks),
        "factor_feasible": audit["factor_feasible_masks"],
        "short_direction_q": args.short_direction_q,
        "elapsed_s": audit["elapsed_s"],
    }
    if not args.quiet:
        summary["feasible_masks"] = audit["feasible_masks"]
    print(json.dumps(summary, indent=2))
    print(output)


if __name__ == "__main__":
    main()
