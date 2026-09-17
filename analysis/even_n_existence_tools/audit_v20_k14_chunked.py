"""Chunked q=0..q=3 exact audit over CUDA root-option survivors (k=14).

Memory-bounded: the GPU survivor list and every intermediate feasible list are
processed in fixed-size chunks. Each chunk is handed to the C++ exact
deficit-0/1/2 f-factor DFS (mode 3) with the requested short-direction line
capacities (q). The feasible subset returned for a chunk is collected and
becomes the input for the next q level, so q=0 -> q=1 -> q=2 -> q=3 is a
pipeline that never materialises one giant stdin string.
"""

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


def build_tokens(base, k, masks, q, defects, blockers, components) -> str:
    edges = [tuple(value) for value in base["edges"]]
    tokens = [str(len(components))]
    for order in components:
        tokens.extend([str(len(order)), *(str(value) for value in order)])
    tokens.extend(["3", str(k), str(len(masks)), *(str(mask) for mask in masks)])
    for (u, v), bit in zip(edges, base["bits"]):
        tokens.extend([str(u), str(v), str(bit)])
    tokens.extend([str(len(defects)), *(str(value) for value in defects)])
    for u in range(37):
        for v in range(37):
            values = blockers[(u, v)]
            tokens.extend([str(len(values)), *(str(value) for value in values)])
    line_keys = short_direction_lines(q)
    tokens.append(str(len(line_keys)))
    for key in line_keys:
        tokens.extend(str(value) for value in key)
    return " ".join(tokens)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--gpu", required=True)
    parser.add_argument(
        "--exe", default="rot4_multigraph_factor_multicycle_exhaustive_v9.exe"
    )
    parser.add_argument("--chunk", type=int, default=2_000_000)
    parser.add_argument("--max-q", type=int, default=3)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--save-final",
        default=None,
        help="Optional path; if set, the final q-level feasible masks are "
        "written here (one decimal mask per line) so survivors can be "
        "geometrically verified after the audit.",
    )
    args = parser.parse_args()

    archive = json.loads((HERE / "v20_basin_archive.json").read_text())
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    edges = [tuple(value) for value in base["edges"]]
    components = ordered_components(edges)
    blockers = candidate_blockers(base)
    hitting = json.loads(
        (HERE / f"v20_defect_hitting_{args.base}.json").read_text()
    )
    defects = [owner_mask(value) for value in hitting["defect_owner_sets"]]

    gpu = json.loads((HERE / args.gpu).read_text())
    if not gpu["survivor_masks_complete"]:
        raise RuntimeError("GPU survivor buffer overflowed")
    current = [int(value) for value in gpu["survivor_masks"]]
    started = time.time()
    per_q = {}
    print(
        f"{args.base} k={args.size}: {len(current):,} input survivors",
        flush=True,
    )
    for q in range(0, args.max_q + 1):
        feasible = []
        count = 0
        max_nodes = 0
        for start in range(0, len(current), args.chunk):
            chunk = current[start : start + args.chunk]
            if not chunk:
                continue
            tokens = build_tokens(base, args.size, chunk, q, defects, blockers, components)
            completed = subprocess.run(
                [str((HERE / args.exe).resolve())],
                input=tokens,
                text=True,
                capture_output=True,
                check=True,
            )
            res = json.loads(completed.stdout)
            count += res["factor_feasible_masks"]
            max_nodes = max(max_nodes, res.get("maximum_factor_search_nodes", 0))
            feasible.extend(res.get("feasible_masks", []))
        per_q[q] = {
            "factor_feasible_masks": count,
            "collected_feasible": len(feasible),
            "max_factor_search_nodes": max_nodes,
        }
        print(
            f"  {args.base} k={args.size} q={q}: feasible={count:,} "
            f"collected={len(feasible):,}",
            flush=True,
        )
        current = feasible
        if count == 0:
            for qq in range(q + 1, args.max_q + 1):
                per_q[qq] = {
                    "factor_feasible_masks": 0,
                    "collected_feasible": 0,
                    "max_factor_search_nodes": 0,
                }
            break

    payload = {
        "base": args.base,
        "k": args.size,
        "gpu": args.gpu,
        "method": (
            "chunked exact deficit-0/1/2 f-factor DFS (mode 3) over CUDA "
            "root-option survivors; q=0..q=max_q short-direction line capacities"
        ),
        "per_q": per_q,
        "elapsed_s": round(time.time() - started, 2),
    }
    if args.save_final and current:
        final_path = HERE / args.save_final
        final_path.write_text(
            "\n".join(str(mask) for mask in current) + "\n", encoding="utf-8"
        )
        payload["final_survivors_file"] = str(final_path)
        payload["final_survivors_count"] = len(current)
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(per_q, indent=2))
    print(output)


if __name__ == "__main__":
    main()
