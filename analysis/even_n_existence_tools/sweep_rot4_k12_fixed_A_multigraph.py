"""Sweep every deletion-run partition at fixed k and adjacency A."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent


def partitions(total: int, parts: int, maximum: int | None = None):
    if parts == 0:
        if total == 0:
            yield ()
        return
    maximum = min(total, maximum if maximum is not None else total)
    for first in range(maximum, 0, -1):
        for tail in partitions(total - first, parts - 1, first):
            yield (first,) + tail


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=12)
    parser.add_argument("--A", type=int, required=True)
    parser.add_argument("--bases", default="v40_01,v40_02,v40_03,v40_04")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not 1 <= args.size <= 12:
        parser.error("--size must lie in 1..12")
    run_count = args.size - args.A
    if not 1 <= run_count <= args.size:
        parser.error("A must lie in 0..size-1")
    profiles = list(partitions(args.size, run_count))
    bases = args.bases.split(",")
    started = time.time()
    records = []
    for base in bases:
        for profile in profiles:
            b = sum(max(length - 2, 0) for length in profile)
            c = sum(max(length - 3, 0) for length in profile)
            slug = "-".join(map(str, profile))
            output_name = (
                f"rot4_multigraph_factor_exhaustive_{base}_k{args.size}_"
                f"a{args.A}_b{b}_c{c}_r{slug}_q0.json"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(HERE / "audit_rot4_multigraph_factor_exhaustive.py"),
                    "--base",
                    base,
                    "--runs",
                    ",".join(map(str, profile)),
                    "--size",
                    str(args.size),
                    "--out",
                    output_name,
                ],
                cwd=HERE,
                text=True,
                capture_output=True,
                check=True,
            )
            item = json.loads((HERE / output_name).read_text(encoding="utf-8"))
            record = {
                "base": base,
                "profile": list(profile),
                "B": b,
                "C": c,
                "distinct_shape_masks": item["distinct_shape_masks"],
                "defect_hitting_masks": item["defect_hitting_masks"],
                "q0_factor_feasible_masks": item["factor_feasible_masks"],
                "first_feasible_removed_indices": item[
                    "first_feasible_removed_indices"
                ],
                "maximum_factor_search_nodes": item[
                    "maximum_factor_search_nodes"
                ],
                "certificate": output_name,
            }
            records.append(record)
            print(
                f"{base} {profile}: hit={record['defect_hitting_masks']} "
                f"q0={record['q0_factor_feasible_masks']}",
                flush=True,
            )
    payload = {
        "k": args.size,
        "A": args.A,
        "run_count": run_count,
        "profile_count_per_base": len(profiles),
        "bases": bases,
        "records": records,
        "totals": {
            "base_profile_cases": len(records),
            "distinct_shape_masks": sum(
                item["distinct_shape_masks"] for item in records
            ),
            "defect_hitting_masks": sum(
                item["defect_hitting_masks"] for item in records
            ),
            "q0_factor_feasible_masks": sum(
                item["q0_factor_feasible_masks"] for item in records
            ),
        },
        "elapsed_s": round(time.time() - started, 3),
    }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["totals"], indent=2))
    print(output)


if __name__ == "__main__":
    main()
