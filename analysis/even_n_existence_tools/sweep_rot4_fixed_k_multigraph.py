"""Run corrected direct fixed-(k,A) q=0 audits with bounded parallelism."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent


def run_one(size: int, base: str, adjacency: int) -> dict:
    output_name = (
        f"rot4_multigraph_factor_direct_{base}_k{size}_a{adjacency}_q0.json"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(HERE / "audit_rot4_multigraph_factor_fixed_A_exhaustive.py"),
            "--base",
            base,
            "--size",
            str(size),
            "--A",
            str(adjacency),
            "--out",
            output_name,
        ],
        cwd=HERE,
        text=True,
        capture_output=True,
        check=True,
    )
    item = json.loads((HERE / output_name).read_text(encoding="utf-8"))
    return {
        "base": base,
        "A": adjacency,
        "distinct_shape_masks": item["distinct_shape_masks"],
        "defect_hitting_masks": item["defect_hitting_masks"],
        "q0_factor_feasible_masks": item["factor_feasible_masks"],
        "feasible_masks": item["feasible_masks"],
        "maximum_factor_search_nodes": item["maximum_factor_search_nodes"],
        "elapsed_s": item["elapsed_s"],
        "certificate": output_name,
        "stdout_tail": completed.stdout.splitlines()[-2:],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--A", default="")
    parser.add_argument("--bases", default="v40_01,v40_02,v40_03,v40_04")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not 1 <= args.size <= 12:
        parser.error("--size must lie in 1..12")
    adjacency_values = (
        [int(value) for value in args.A.split(",") if value]
        if args.A
        else list(range(args.size))
    )
    if any(not 0 <= value < args.size for value in adjacency_values):
        parser.error("every A must lie in 0..size-1")
    bases = [value for value in args.bases.split(",") if value]
    tasks = [
        (args.size, base, adjacency)
        for adjacency in adjacency_values
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
            records.append(record)
            print(
                f"{record['base']} k={args.size} A={record['A']}: "
                f"shapes={record['distinct_shape_masks']} "
                f"hit={record['defect_hitting_masks']} "
                f"q0={record['q0_factor_feasible_masks']} "
                f"t={record['elapsed_s']}s",
                flush=True,
            )
    records.sort(key=lambda item: (item["A"], item["base"]))
    payload = {
        "method": "corrected direct fixed-(k,A) multigraph q=0 enumeration",
        "k": args.size,
        "A_values": adjacency_values,
        "bases": bases,
        "workers": args.workers,
        "records": records,
        "totals": {
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
