"""Sweep (adjacent-pair count, triple-window count) deletion run shapes."""

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
    parser.add_argument("--bases", default="v40_01")
    parser.add_argument("--size", type=int, default=11)
    parser.add_argument(
        "--shapes",
        default="5:0,5:1,5:2,5:3,5:4,6:0,6:1,6:2,6:3,6:4,6:5",
    )
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--short-direction-q", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=50)
    parser.add_argument("--per-round-time", type=float, default=90.0)
    parser.add_argument("--total-time", type=float, default=240.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", default="rot4_runshape_cut_sweep.json")
    args = parser.parse_args()

    wanted = set(args.bases.split(","))
    shapes = [
        tuple(int(value) for value in item.split(":"))
        for item in args.shapes.split(",")
    ]
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    bases = [item for item in archive["archive"] if item["id"] in wanted]
    output = HERE / args.out
    payload = {"parameters": vars(args), "bases": []}
    global_lines: set[tuple[int, int, int]] = set()
    started = time.time()

    for base in sorted(bases, key=lambda item: item["id"]):
        hitting = json.loads(
            (SOURCE_OUTPUTS / f"defect_hitting_{base['id']}.json").read_text(
                encoding="utf-8"
            )
        )
        print(f"{base['id']}: precomputing blockers", flush=True)
        blockers = candidate_blockers(base)
        statuses = {}
        shared_lines = set(global_lines)
        base_result = {"base": base["id"], "attempts": [], "final_status": {}}
        payload["bases"].append(base_result)
        for pass_no in range(1, args.passes + 1):
            unresolved = [
                shape
                for shape in shapes
                if statuses.get(shape) not in ("INFEASIBLE", "EXACT_SOLUTION")
            ]
            if not unresolved:
                break
            print(
                f"  pass={pass_no} unresolved={unresolved} "
                f"shared={len(shared_lines)}",
                flush=True,
            )
            for adjacency, triples in unresolved:
                print(
                    f"    shape={adjacency}:{triples} "
                    f"shared={len(shared_lines)}",
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
                    triples,
                    None,
                    None,
                    None,
                    sorted(shared_lines),
                )
                result["pass"] = pass_no
                base_result["attempts"].append(result)
                statuses[(adjacency, triples)] = result["status"]
                shared_lines.update(
                    canonical_line_orbit(tuple(key))
                    for key in result["line_keys"]
                )
                global_lines.update(shared_lines)
                base_result["final_status"] = {
                    f"{a}:{t}": status
                    for (a, t), status in sorted(statuses.items())
                }
                output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                print(
                    f"      status={result['status']} "
                    f"rounds={result['round_count']} "
                    f"dynamic={result['dynamic_line_cut_count']} "
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
            f"{a}:{t}": status
            for (a, t), status in sorted(statuses.items())
        }
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if any(value == "EXACT_SOLUTION" for value in statuses.values()):
            break

    payload["elapsed_s"] = round(time.time() - started, 3)
    payload["global_shared_line_count"] = len(global_lines)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
