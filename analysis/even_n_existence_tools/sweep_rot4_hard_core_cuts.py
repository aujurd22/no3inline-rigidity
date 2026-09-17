"""Sweep fully specified (adjacency, triples, loops, reselections) hard cores."""

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
    parser.add_argument(
        "--cases",
        required=True,
        help="comma-separated adjacency:triples:loops:reselected[:deficit2_edges]",
    )
    parser.add_argument("--short-direction-q", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=50)
    parser.add_argument("--per-round-time", type=float, default=60.0)
    parser.add_argument("--total-time", type=float, default=150.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed-json", default="")
    parser.add_argument("--out", default="rot4_hard_core_cut_sweep.json")
    args = parser.parse_args()

    cases = []
    for item in args.cases.split(","):
        values = tuple(
            None if value == "*" else int(value)
            for value in item.split(":")
        )
        if len(values) == 4:
            values += (None,)
        if len(values) != 5:
            parser.error("every case needs four or five colon-separated integers")
        cases.append(values)
    archive = json.loads(
        (SOURCE_OUTPUTS / "exact_factor_archive.json").read_text(encoding="utf-8")
    )
    base = next(item for item in archive["archive"] if item["id"] == args.base)
    hitting = json.loads(
        (SOURCE_OUTPUTS / f"defect_hitting_{args.base}.json").read_text(
            encoding="utf-8"
        )
    )
    blockers = candidate_blockers(base)
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
    print(
        f"{args.base}: cases={len(cases)} seed_lines={len(shared_lines)}",
        flush=True,
    )
    payload = {
        "parameters": vars(args),
        "attempts": [],
        "final_status": {},
        "seed_line_count": len(shared_lines),
    }
    output = HERE / args.out
    started = time.time()
    for adjacency, triples, loops, reselected, deficit_two_edges in cases:
        label = ":".join(
            "*" if value is None else str(value)
            for value in (
                adjacency,
                triples,
                loops,
                reselected,
                deficit_two_edges,
            )
        )
        print(
            f"  core={label} "
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
            reselected,
            deficit_two_edges,
            sorted(shared_lines),
        )
        payload["attempts"].append(result)
        payload["final_status"][label] = result["status"]
        shared_lines.update(
            canonical_line_orbit(tuple(key)) for key in result["line_keys"]
        )
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
    payload["elapsed_s"] = round(time.time() - started, 3)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
