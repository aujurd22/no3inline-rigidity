"""Sweep and revisit k=11 deletion-adjacency layers with shared line cuts."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from analyze_rot4_shadow_factor import SOURCE_OUTPUTS
from search_rot4_shadow_escape_radius import candidate_blockers
from solve_joint_rot4_general_factor import (
    canonical_line_orbit,
    solve_general_with_cuts,
)


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bases", default="all")
    parser.add_argument("--size", type=int, default=11)
    parser.add_argument("--adjacencies", default="0,1,2,3,4,5,6,7,8,9,10")
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--short-direction-q", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=50)
    parser.add_argument("--per-round-time", type=float, default=90.0)
    parser.add_argument("--total-time", type=float, default=240.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", default="rot4_adjacency_cut_sweep.json")
    args = parser.parse_args()

    wanted = (
        {f"v40_{i:02d}" for i in range(1, 5)}
        if args.bases == "all"
        else set(args.bases.split(","))
    )
    adjacencies = [int(item) for item in args.adjacencies.split(",")]
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = [item for item in archive["archive"] if item["id"] in wanted]
    output = HERE / args.out
    payload = {"parameters": vars(args), "bases": []}
    globally_shared_lines: set[tuple[int, int, int]] = set()
    started = time.time()

    for base in sorted(bases, key=lambda item: item["id"]):
        hitting = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base['id']}.json").read_text(
                encoding="utf-8"
            )
        )
        print(f"{base['id']}: precomputing blockers", flush=True)
        blockers = candidate_blockers(base)
        base_result = {"base": base["id"], "attempts": [], "final_status": {}}
        payload["bases"].append(base_result)
        statuses = {}
        shared_lines = set(globally_shared_lines)

        for pass_no in range(1, args.passes + 1):
            unresolved = [
                adjacency
                for adjacency in adjacencies
                if statuses.get(adjacency) not in ("INFEASIBLE", "EXACT_SOLUTION")
            ]
            if not unresolved:
                break
            print(
                f"  pass={pass_no} unresolved={unresolved} "
                f"shared_lines={len(shared_lines)}",
                flush=True,
            )
            for adjacency in unresolved:
                print(
                    f"    adjacency={adjacency} starting with "
                    f"{len(shared_lines)} shared lines",
                    flush=True,
                )
                result = solve_general_with_cuts(
                    base,
                    hitting["defect_owner_sets"],
                    blockers,
                    args.size,
                    args.max_rounds,
                    args.per_round_time,
                    args.total_time,
                    args.workers,
                    args.short_direction_q,
                    adjacency,
                    None,
                    None,
                    None,
                    None,
                    sorted(shared_lines),
                )
                result["pass"] = pass_no
                base_result["attempts"].append(result)
                statuses[adjacency] = result["status"]
                shared_lines.update(
                    canonical_line_orbit(tuple(key))
                    for key in result["line_keys"]
                )
                globally_shared_lines.update(shared_lines)
                base_result["final_status"] = {
                    str(key): value for key, value in sorted(statuses.items())
                }
                payload["global_shared_line_count"] = len(globally_shared_lines)
                output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                print(
                    f"      status={result['status']} "
                    f"rounds={result['round_count']} "
                    f"new_dynamic={result['dynamic_line_cut_count']} "
                    f"shared_now={len(shared_lines)} "
                    f"best_bad={result['best_bad_line_count']}",
                    flush=True,
                )
                if result["status"] == "EXACT_SOLUTION":
                    break
            if any(value == "EXACT_SOLUTION" for value in statuses.values()):
                break
        base_result["shared_line_count"] = len(shared_lines)
        base_result["final_status"] = {
            str(key): value for key, value in sorted(statuses.items())
        }
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if any(value == "EXACT_SOLUTION" for value in statuses.values()):
            break

    payload["elapsed_s"] = round(time.time() - started, 3)
    payload["global_shared_line_count"] = len(globally_shared_lines)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
