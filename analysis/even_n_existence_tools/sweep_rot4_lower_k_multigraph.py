"""Audit a range of corrected lower normalized-distance shells."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import time
from pathlib import Path

from sweep_rot4_fixed_k_multigraph import run_one


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-size", type=int, default=5)
    parser.add_argument("--max-size", type=int, default=10)
    parser.add_argument("--bases", default="v40_01,v40_02,v40_03,v40_04")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not 1 <= args.min_size <= args.max_size <= 12:
        parser.error("require 1 <= min-size <= max-size <= 12")
    bases = [value for value in args.bases.split(",") if value]
    tasks = [
        (size, base, adjacency)
        for size in range(args.min_size, args.max_size + 1)
        for adjacency in range(size)
        for base in bases
    ]
    started = time.time()
    records = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, args.workers)
    ) as executor:
        futures = {
            executor.submit(run_one, *task): task
            for task in tasks
        }
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            size = futures[future][0]
            record["k"] = size
            records.append(record)
            print(
                f"{record['base']} k={size} A={record['A']}: "
                f"shapes={record['distinct_shape_masks']} "
                f"hit={record['defect_hitting_masks']} "
                f"q0={record['q0_factor_feasible_masks']} "
                f"t={record['elapsed_s']}s",
                flush=True,
            )
    records.sort(key=lambda item: (item["k"], item["A"], item["base"]))
    per_k = []
    for size in range(args.min_size, args.max_size + 1):
        selected = [item for item in records if item["k"] == size]
        expected = len(bases) * math.comb(37, size)
        actual = sum(item["distinct_shape_masks"] for item in selected)
        per_k.append({
            "k": size,
            "expected_all_masks": expected,
            "audited_all_masks": actual,
            "coverage_exact": actual == expected,
            "defect_hitting_masks": sum(
                item["defect_hitting_masks"] for item in selected
            ),
            "q0_factor_feasible_masks": sum(
                item["q0_factor_feasible_masks"] for item in selected
            ),
        })
    if not all(item["coverage_exact"] for item in per_k):
        raise RuntimeError("coverage identity failed")
    payload = {
        "method": "corrected direct fixed-(k,A) multigraph q=0 enumeration",
        "k_range": [args.min_size, args.max_size],
        "bases": bases,
        "workers": args.workers,
        "per_k": per_k,
        "records": records,
        "totals": {
            "all_masks": sum(item["audited_all_masks"] for item in per_k),
            "defect_hitting_masks": sum(
                item["defect_hitting_masks"] for item in per_k
            ),
            "q0_factor_feasible_masks": sum(
                item["q0_factor_feasible_masks"] for item in per_k
            ),
        },
        "elapsed_s": round(time.time() - started, 3),
    }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"per_k": per_k, "totals": payload["totals"]}, indent=2))
    print(output)


if __name__ == "__main__":
    main()
