"""Exhaust a fixed adjacency layer over every feasible (B,C) window profile."""

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
    parser.add_argument("--profile-file", required=True)
    parser.add_argument("--direction-q", type=int, required=True)
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    profile = json.loads((HERE / args.profile_file).read_text(encoding="utf-8"))
    shapes = sorted(
        {
            (item["triple"], item["quadruple"])
            for item in profile["profiles"]
            if item["deleted"] == args.size
            and item["adjacent"] == args.adjacency_count
        }
    )
    summary = {
        "parameters": vars(args),
        "expected_profiles": [list(shape) for shape in shapes],
        "layers": [],
    }
    output = HERE / args.out
    for triple, quadruple in shapes:
        tag = (
            f"{args.base}_k{args.size}_a{args.adjacency_count}"
            f"_b{triple}_c{quadruple}_norm_q{args.direction_q}hard"
        )
        evidence = HERE / f"rot4_short_{tag}.json"
        stdout = HERE / f"short_{tag}.log"
        stderr = HERE / f"short_{tag}.err"
        if not evidence.exists():
            command = [
                sys.executable,
                "-u",
                str(HERE / "solve_rot4_short_factor.py"),
                "--base",
                args.base,
                "--size",
                str(args.size),
                "--adjacency-count",
                str(args.adjacency_count),
                "--triple-count",
                str(triple),
                "--quadruple-count",
                str(quadruple),
                "--direction-q",
                str(args.direction_q),
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
                f"CLOSED_Q{args.direction_q}"
                if status == "INFEASIBLE"
                else f"SURVIVES_Q{args.direction_q}"
                if status in ("OPTIMAL", "FEASIBLE")
                else "UNRESOLVED"
            )
            record = {
                "triple": triple,
                "quadruple": quadruple,
                "classification": classification,
                "status": status,
                "wall_s": payload["wall_s"],
                "evidence": evidence.name,
            }
        else:
            record = {
                "triple": triple,
                "quadruple": quadruple,
                "classification": "NO_OUTPUT",
            }
        summary["layers"].append(record)
        covered = {
            (item["triple"], item["quadruple"])
            for item in summary["layers"]
            if item["classification"].startswith("CLOSED")
        }
        summary["closed_profile_count"] = len(covered)
        summary["complete_closure"] = covered == set(shapes)
        output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
