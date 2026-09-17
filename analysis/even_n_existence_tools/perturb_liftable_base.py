"""Measure local robustness of a known liftable four-permutation base."""

from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

from analyze_modp_reductions import analyse, decode_first
from four_permutation_lift_sat import solve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--time-limit", type=float, default=5.0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    known = analyse(decode_first(args.cache, 2 * args.p), args.p)
    base = known["four_permutation_decomposition"]
    started = time.perf_counter()
    counts: dict[str, int] = {}
    satisfiable = []
    tested = 0
    for layer in range(4):
        for first, second in itertools.combinations(range(args.p), 2):
            candidate = [permutation[:] for permutation in base]
            candidate[layer][first], candidate[layer][second] = (
                candidate[layer][second],
                candidate[layer][first],
            )
            result = solve(
                args.p,
                candidate,
                time_limit=args.time_limit,
                workers=args.workers,
            )
            tested += 1
            status = result["status"]
            counts[status] = counts.get(status, 0) + 1
            if status in ("OPTIMAL", "FEASIBLE"):
                record = {
                    "layer": layer,
                    "swap": [first, second],
                    "permutations": candidate,
                    "result": result,
                }
                satisfiable.append(record)
                print(json.dumps(record, indent=2), flush=True)
    print(
        json.dumps(
            {
                "summary": True,
                "p": args.p,
                "tested": tested,
                "counts": counts,
                "satisfiable_neighbours": len(satisfiable),
                "wall_seconds": time.perf_counter() - started,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
