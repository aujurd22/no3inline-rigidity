"""Sweep all four-shift inverse base graphs in the general four-edge lift."""

from __future__ import annotations

import argparse
import itertools
import json
import time

from four_permutation_lift_sat import inverse_permutation, is_prime, solve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--stop-on-sat", action="store_true")
    args = parser.parse_args()
    if not is_prime(args.p) or args.p < 5:
        raise SystemExit("p must be a prime at least 5")

    p = args.p
    inv = inverse_permutation(p)
    counts: dict[str, int] = {}
    witnesses = []
    started = time.perf_counter()
    for index, shifts in enumerate(itertools.combinations(range(p), 4), start=1):
        permutations = [
            [(value + shift) % p for value in inv]
            for shift in shifts
        ]
        result = solve(
            p=p,
            permutations=permutations,
            time_limit=args.time_limit,
            workers=args.workers,
        )
        status = result["status"]
        counts[status] = counts.get(status, 0) + 1
        if status in ("OPTIMAL", "FEASIBLE") and result.get("verification", {}).get("valid"):
            result["shifts"] = shifts
            witnesses.append(result)
            print("SAT_WITNESS")
            print(json.dumps(result, indent=2), flush=True)
            if args.stop_on_sat:
                break
        if index % 25 == 0:
            print(
                json.dumps(
                    {
                        "progress": index,
                        "status_counts": counts,
                        "elapsed_seconds": time.perf_counter() - started,
                    }
                ),
                flush=True,
            )

    summary = {
        "p": p,
        "n": 2 * p,
        "status_counts": counts,
        "sat_count": len(witnesses),
        "sat_shifts": [result["shifts"] for result in witnesses],
        "elapsed_seconds": time.perf_counter() - started,
    }
    print("SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
