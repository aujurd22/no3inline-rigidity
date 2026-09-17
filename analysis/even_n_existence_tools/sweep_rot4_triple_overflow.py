"""Split a hard (k,A) layer by its cyclic triple-deletion count B."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def classify(payload: dict) -> str:
    if payload["status"] == "INFEASIBLE":
        hard_q = payload["parameters"].get("hard_direction_q", 0)
        return "CLOSED_F0" if hard_q == 0 else f"CLOSED_HARD_Q{hard_q}"
    if payload["status"] == "OPTIMAL" and payload["objective"] > 0:
        return "CLOSED_OVERFLOW"
    if payload["status"] == "OPTIMAL" and payload["objective"] == 0:
        return "SURVIVES"
    return "UNRESOLVED"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--adjacency-count", type=int, required=True)
    parser.add_argument("--triple-counts", required=True)
    parser.add_argument("--direction-q", type=int, default=1)
    parser.add_argument("--hard-direction-q", type=int, default=0)
    parser.add_argument("--forbid-exact-reselection", action="store_true")
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = HERE / args.out
    summary = {"parameters": vars(args), "layers": []}
    for triple_count in [int(value) for value in args.triple_counts.split(",")]:
        normalization_tag = "_norm" if args.forbid_exact_reselection else ""
        tag = (
            f"{args.base}_k{args.size}_a{args.adjacency_count}"
            f"_b{triple_count}{normalization_tag}"
            f"_hq{args.hard_direction_q}_q{args.direction_q}"
        )
        evidence = HERE / f"rot4_line_overflow_{tag}.json"
        stdout_path = HERE / f"lineopt_{tag}.log"
        stderr_path = HERE / f"lineopt_{tag}.err"
        if not evidence.exists():
            command = [
                sys.executable,
                "-u",
                str(HERE / "minimize_rot4_diagonal_overflow.py"),
                "--base",
                args.base,
                "--size",
                str(args.size),
                "--adjacency-count",
                str(args.adjacency_count),
                "--triple-count",
                str(triple_count),
                "--direction-q",
                str(args.direction_q),
                "--hard-direction-q",
                str(args.hard_direction_q),
                "--time-limit",
                str(args.time_limit),
                "--workers",
                str(args.workers),
                "--out",
                evidence.name,
            ]
            if args.forbid_exact_reselection:
                command.append("--forbid-exact-reselection")
            with stdout_path.open("w", encoding="utf-8") as stdout, (
                stderr_path.open("w", encoding="utf-8")
            ) as stderr:
                subprocess.run(
                    command,
                    cwd=HERE,
                    stdout=stdout,
                    stderr=stderr,
                    check=False,
                )
        if evidence.exists():
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            record = {
                "triple_count": triple_count,
                "classification": classify(payload),
                "status": payload["status"],
                "objective": payload["objective"],
                "best_bound": payload["best_bound"],
                "wall_s": payload["wall_s"],
                "evidence": evidence.name,
            }
        else:
            record = {
                "triple_count": triple_count,
                "classification": "NO_OUTPUT",
            }
        summary["layers"].append(record)
        output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
