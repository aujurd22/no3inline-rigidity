"""Split one normalized (k,A,B) q=1 layer by quadruple-window count."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--adjacency-count", type=int, required=True)
    parser.add_argument("--triple-count", type=int, required=True)
    parser.add_argument("--quadruple-counts", required=True)
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    summary = {"parameters": vars(args), "layers": []}
    output = HERE / args.out
    for quadruple in [
        int(value) for value in args.quadruple_counts.split(",")
    ]:
        tag = (
            f"{args.base}_k{args.size}_a{args.adjacency_count}"
            f"_b{args.triple_count}_c{quadruple}_norm_q1resource"
        )
        evidence = HERE / f"rot4_{tag}.json"
        stdout = HERE / f"{tag}.log"
        stderr = HERE / f"{tag}.err"
        if not evidence.exists():
            command = [
                sys.executable,
                "-u",
                str(HERE / "solve_rot4_q1_resource_factor.py"),
                "--base",
                args.base,
                "--size",
                str(args.size),
                "--adjacency-count",
                str(args.adjacency_count),
                "--triple-count",
                str(args.triple_count),
                "--quadruple-count",
                str(quadruple),
                "--time-limit",
                str(args.time_limit),
                "--workers",
                str(args.workers),
                "--out",
                evidence.name,
            ]
            with stdout.open("w", encoding="utf-8") as stdout_file, (
                stderr.open("w", encoding="utf-8")
            ) as stderr_file:
                subprocess.run(
                    command,
                    cwd=HERE,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    check=False,
                )
        if evidence.exists():
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            status = payload["status"]
            classification = (
                "CLOSED_Q1"
                if status == "INFEASIBLE"
                else "SURVIVES_Q1"
                if status in ("OPTIMAL", "FEASIBLE")
                else "UNRESOLVED"
            )
            record = {
                "quadruple_count": quadruple,
                "classification": classification,
                "status": status,
                "wall_s": payload["wall_s"],
                "evidence": evidence.name,
            }
        else:
            record = {
                "quadruple_count": quadruple,
                "classification": "NO_OUTPUT",
            }
        summary["layers"].append(record)
        output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
