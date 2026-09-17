"""Run corrected fixed-(k,A) q=0 audits over all six verified V20 basins."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "v20_basin_archive.json"
BASES = [f"v20_{index:02d}" for index in range(1, 7)]


def run_one(size: int, base: str, adjacency: int, exe: str) -> dict:
    output_name = f"v20_multigraph_factor_{base}_k{size}_a{adjacency}_q0.json"
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
            "--archive",
            str(ARCHIVE),
            "--hitting",
            str(HERE / f"v20_defect_hitting_{base}.json"),
            "--exe",
            exe,
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
        "stderr_tail": completed.stderr.splitlines()[-5:],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--A", default="")
    parser.add_argument("--bases", default=",".join(BASES))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--exe", default="rot4_multigraph_factor_multicycle_exhaustive_v5.exe"
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not 1 <= args.size <= 14:
        parser.error("--size must lie in 1..14")
    adjacency_values = (
        [int(value) for value in args.A.split(",") if value]
        if args.A
        else list(range(args.size + 1))
    )
    if any(not 0 <= value <= args.size for value in adjacency_values):
        parser.error("every A must lie in 0..size")
    bases = [value for value in args.bases.split(",") if value]
    unknown = sorted(set(bases) - set(BASES))
    if unknown:
        parser.error(f"unknown V20 bases: {unknown}")

    tasks = [
        (args.size, base, adjacency, args.exe)
        for adjacency in adjacency_values
        for base in bases
    ]
    started = time.time()
    records = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, args.workers)
    ) as executor:
        futures = {executor.submit(run_one, *task): task for task in tasks}
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
    records.sort(key=lambda item: (item["base"], item["A"]))

    per_base = {}
    expected = math.comb(37, args.size)
    for base in bases:
        selected = [item for item in records if item["base"] == base]
        shape_total = sum(item["distinct_shape_masks"] for item in selected)
        per_base[base] = {
            "distinct_shape_masks": shape_total,
            "expected_masks": expected,
            "partition_complete": shape_total == expected,
            "defect_hitting_masks": sum(
                item["defect_hitting_masks"] for item in selected
            ),
            "q0_factor_feasible_masks": sum(
                item["q0_factor_feasible_masks"] for item in selected
            ),
        }
    payload = {
        "method": (
            "corrected direct fixed-(k,A) multigraph q=0 enumeration; "
            "cycle length one is the base loop and contributes A=1 when removed"
        ),
        "archive": str(ARCHIVE),
        "k": args.size,
        "A_values": adjacency_values,
        "bases": bases,
        "workers": args.workers,
        "records": records,
        "per_base": per_base,
        "all_partitions_complete": all(
            item["partition_complete"] for item in per_base.values()
        ),
        "elapsed_s": round(time.time() - started, 3),
    }
    output = HERE / args.out
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(per_base, indent=2))
    print(output)


if __name__ == "__main__":
    main()
