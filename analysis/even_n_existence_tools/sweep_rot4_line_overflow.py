"""Escalate fixed short-direction families until an adjacency layer closes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent


def classify(payload: dict) -> str:
    if payload["status"] == "INFEASIBLE":
        return "CLOSED_F0"
    if payload["status"] == "OPTIMAL":
        return (
            "CLOSED_OVERFLOW"
            if payload["objective"] > 0
            else "SURVIVES"
        )
    return "UNRESOLVED"


def write_summary(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--adjacencies", required=True)
    parser.add_argument("--size", type=int, default=11)
    parser.add_argument("--q-max", type=int, default=4)
    parser.add_argument("--time-limit", type=float, default=1200.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--forbid-exact-reselection", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    adjacencies = [int(value) for value in args.adjacencies.split(",")]
    summary = {
        "parameters": vars(args),
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "layers": [],
    }
    summary_path = HERE / args.out
    for adjacency in adjacencies:
        layer = {
            "adjacency_count": adjacency,
            "attempts": [],
            "classification": "UNRESOLVED",
        }
        summary["layers"].append(layer)
        for q in range(1, args.q_max + 1):
            normalization_tag = (
                "_norm" if args.forbid_exact_reselection else ""
            )
            tag = (
                f"{args.base}_k{args.size}_a{adjacency}"
                f"{normalization_tag}_q{q}"
            )
            output = HERE / f"rot4_line_overflow_{tag}.json"
            stdout_path = HERE / f"lineopt_{tag}.log"
            stderr_path = HERE / f"lineopt_{tag}.err"
            if not output.exists():
                command = [
                    sys.executable,
                    "-u",
                    str(HERE / "minimize_rot4_diagonal_overflow.py"),
                    "--base",
                    args.base,
                    "--size",
                    str(args.size),
                    "--adjacency-count",
                    str(adjacency),
                    "--direction-q",
                    str(q),
                    "--hard-direction-q",
                    str(q - 1),
                    "--time-limit",
                    str(args.time_limit),
                    "--workers",
                    str(args.workers),
                    "--out",
                    output.name,
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
            if not output.exists():
                layer["attempts"].append(
                    {"q": q, "status": "NO_OUTPUT", "classification": "UNRESOLVED"}
                )
                break
            result = json.loads(output.read_text(encoding="utf-8"))
            result_class = classify(result)
            layer["attempts"].append(
                {
                    "q": q,
                    "status": result["status"],
                    "objective": result["objective"],
                    "best_bound": result["best_bound"],
                    "wall_s": result["wall_s"],
                    "classification": result_class,
                    "evidence": output.name,
                }
            )
            layer["classification"] = result_class
            layer["closing_q"] = q if result_class.startswith("CLOSED") else None
            write_summary(summary_path, summary)
            if result_class != "SURVIVES":
                break
        write_summary(summary_path, summary)
    summary["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    write_summary(summary_path, summary)
    print(summary_path)


if __name__ == "__main__":
    main()
