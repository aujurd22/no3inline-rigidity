"""Sweep projectively natural base permutations for the two-lift construction."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import time

from lifted_permutation_sat import inverse_permutation, is_prime, solve_lift


def transformed_inverse(
    p: int,
    in_mul: int,
    in_add: int,
    out_mul: int,
    out_add: int,
) -> list[int]:
    inv = inverse_permutation(p)
    return [
        (out_mul * inv[(in_mul * x + in_add) % p] + out_add) % p
        for x in range(p)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-candidates", type=int, default=0)
    parser.add_argument("--stop-on-sat", action="store_true")
    args = parser.parse_args()

    p = args.p
    if not is_prime(p) or p == 2:
        raise SystemExit("p must be an odd prime")

    f = inverse_permutation(p)
    tested = 0
    derangements = 0
    status_counts: dict[str, int] = {}
    sat_results = []
    started = time.perf_counter()

    parameters = itertools.product(
        range(1, p),
        range(p),
        range(1, p),
        range(p),
    )
    for in_mul, in_add, out_mul, out_add in parameters:
        g = transformed_inverse(p, in_mul, in_add, out_mul, out_add)
        if any(f[x] == g[x] for x in range(p)):
            continue
        derangements += 1
        result = solve_lift(
            p=p,
            f=f,
            g=g,
            time_limit=args.time_limit,
            workers=args.workers,
        )
        tested += 1
        status = result["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        if status in ("OPTIMAL", "FEASIBLE") and result.get("verification", {}).get("valid"):
            result["parameters"] = {
                "in_mul": in_mul,
                "in_add": in_add,
                "out_mul": out_mul,
                "out_add": out_add,
            }
            sat_results.append(result)
            print("SAT_WITNESS")
            print(json.dumps(result, indent=2))
            if args.stop_on_sat:
                break
        if tested % 100 == 0:
            print(
                json.dumps(
                    {
                        "progress": tested,
                        "derangements_seen": derangements,
                        "status_counts": status_counts,
                        "elapsed_seconds": time.perf_counter() - started,
                    }
                ),
                flush=True,
            )
        if args.max_candidates and tested >= args.max_candidates:
            break

    summary = {
        "p": p,
        "n": 2 * p,
        "tested": tested,
        "derangements_seen": derangements,
        "status_counts": status_counts,
        "sat_count": len(sat_results),
        "sat_parameters": [result["parameters"] for result in sat_results],
        "elapsed_seconds": time.perf_counter() - started,
    }
    print("SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
