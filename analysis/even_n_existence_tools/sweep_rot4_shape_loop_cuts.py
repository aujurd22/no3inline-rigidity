"""Split hard deletion run shapes by the number of replacement loops."""

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
    parser.add_argument("--base", default="v40_01")
    parser.add_argument("--size", type=int, default=11)
    parser.add_argument("--cases", required=True, help="comma-separated adjacency:triples:loops")
    parser.add_argument("--passes", type=int, default=1)
    parser.add_argument("--short-direction-q", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=50)
    parser.add_argument("--per-round-time", type=float, default=75.0)
    parser.add_argument("--total-time", type=float, default=180.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--seed-json",
        default="",
        help="optional prior result JSON; every stored line_keys entry is reused",
    )
    parser.add_argument("--out", default="rot4_shape_loop_cut_sweep.json")
    args = parser.parse_args()

    cases = [
        tuple(int(value) for value in item.split(":"))
        for item in args.cases.split(",")
    ]
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    hitting = json.loads(
        (SOURCE_OUTPUTS / f"defect_hitting_{args.base}.json").read_text(
            encoding="utf-8"
        )
    )
    print(f"{args.base}: precomputing blockers", flush=True)
    blockers = candidate_blockers(base)
    output = HERE / args.out
    payload = {"parameters": vars(args), "attempts": [], "final_status": {}}
    shared_lines: set[tuple[int, int, int]] = set()
    if args.seed_json:
        seed = json.loads(Path(args.seed_json).read_text(encoding="utf-8"))

        def collect(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "line_keys":
                        shared_lines.update(
                            canonical_line_orbit(tuple(line)) for line in item
                        )
                    else:
                        collect(item)
            elif isinstance(value, list):
                for item in value:
                    collect(item)

        collect(seed)
        print(f"loaded seed lines={len(shared_lines)}", flush=True)
    statuses = {}
    started = time.time()

    for pass_no in range(1, args.passes + 1):
        unresolved = [
            case
            for case in cases
            if statuses.get(case) not in ("INFEASIBLE", "EXACT_SOLUTION")
        ]
        if not unresolved:
            break
        print(
            f"pass={pass_no} unresolved={unresolved} shared={len(shared_lines)}",
            flush=True,
        )
        for adjacency, triples, loops in unresolved:
            print(
                f"  case={adjacency}:{triples}:{loops} "
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
                loops,
                None,
                None,
                sorted(shared_lines),
            )
            result["pass"] = pass_no
            payload["attempts"].append(result)
            statuses[(adjacency, triples, loops)] = result["status"]
            shared_lines.update(
                canonical_line_orbit(tuple(key)) for key in result["line_keys"]
            )
            payload["final_status"] = {
                f"{a}:{t}:{loop}": status
                for (a, t, loop), status in sorted(statuses.items())
            }
            payload["shared_line_count"] = len(shared_lines)
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(
                f"    status={result['status']} rounds={result['round_count']} "
                f"dynamic={result['dynamic_line_cut_count']} "
                f"shared_now={len(shared_lines)} "
                f"best_bad={result['best_bad_line_count']}",
                flush=True,
            )
            if result["status"] == "EXACT_SOLUTION":
                break
        if any(value == "EXACT_SOLUTION" for value in statuses.values()):
            break
    payload["elapsed_s"] = round(time.time() - started, 3)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
