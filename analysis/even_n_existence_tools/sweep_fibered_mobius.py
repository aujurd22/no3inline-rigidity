"""Sweep completed modular-hyperbola fibres for fixed K and p."""

from __future__ import annotations

import argparse
import json
import time

from fibered_mobius_sat import is_prime, solve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--maximum-tests", type=int, default=0)
    parser.add_argument("--fix-u", type=int)
    parser.add_argument("--fix-v", type=int)
    parser.add_argument("--continue-after-sat", action="store_true")
    args = parser.parse_args()
    if not is_prime(args.p):
        raise SystemExit("p must be prime")

    us = [args.fix_u % args.p] if args.fix_u is not None else range(args.p)
    vs = [args.fix_v % args.p] if args.fix_v is not None else range(args.p)
    tested = 0
    counts: dict[str, int] = {}
    started = time.perf_counter()
    for u in us:
        for v in vs:
            for multiplier in range(1, args.p):
                if args.maximum_tests and tested >= args.maximum_tests:
                    break
                result = solve(
                    args.k,
                    args.p,
                    u,
                    v,
                    multiplier,
                    args.time_limit,
                    args.workers,
                )
                tested += 1
                counts[result["status"]] = counts.get(result["status"], 0) + 1
                print(
                    json.dumps(
                        {
                            "tested": tested,
                            "u": u,
                            "v": v,
                            "multiplier": multiplier,
                            "status": result["status"],
                            "constraints": result["relevant_line_constraints"],
                            "solve_seconds": result["solve_seconds"],
                        }
                    ),
                    flush=True,
                )
                if result["status"] in ("OPTIMAL", "FEASIBLE"):
                    print(json.dumps({"hit": True, "result": result}, indent=2), flush=True)
                    if not args.continue_after_sat:
                        print(
                            json.dumps(
                                {
                                    "summary": True,
                                    "tested": tested,
                                    "counts": counts,
                                    "elapsed_seconds": time.perf_counter() - started,
                                },
                                indent=2,
                            ),
                            flush=True,
                        )
                        return
            if args.maximum_tests and tested >= args.maximum_tests:
                break
        if args.maximum_tests and tested >= args.maximum_tests:
            break
    print(
        json.dumps(
            {
                "summary": True,
                "tested": tested,
                "counts": counts,
                "elapsed_seconds": time.perf_counter() - started,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
