"""Sweep four parallel affine permutations in the exact 2p lift model."""

from __future__ import annotations

import argparse
import itertools
import json
import time

from four_permutation_lift_sat import is_prime, solve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--stop-after-sat", action="store_true")
    args = parser.parse_args()
    if not is_prime(args.p):
        raise SystemExit("p must be prime")

    started = time.perf_counter()
    counts: dict[str, int] = {}
    tested = 0
    for slope in range(1, args.p):
        for shifts in itertools.combinations(range(args.p), 4):
            permutations = [
                [(slope * x + shift) % args.p for x in range(args.p)]
                for shift in shifts
            ]
            result = solve(
                args.p,
                permutations,
                time_limit=args.time_limit,
                workers=args.workers,
            )
            tested += 1
            status = result["status"]
            counts[status] = counts.get(status, 0) + 1
            print(
                json.dumps(
                    {
                        "tested": tested,
                        "slope": slope,
                        "shifts": shifts,
                        "status": status,
                        "elapsed_seconds": result["elapsed_seconds"],
                    }
                ),
                flush=True,
            )
            if status in ("OPTIMAL", "FEASIBLE"):
                print(json.dumps(result, indent=2), flush=True)
                if args.stop_after_sat:
                    break
        else:
            continue
        break
    print(
        json.dumps(
            {
                "summary": True,
                "p": args.p,
                "tested": tested,
                "status_counts": counts,
                "wall_seconds": time.perf_counter() - started,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
