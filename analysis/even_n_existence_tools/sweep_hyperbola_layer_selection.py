"""Sweep K-subsets of modular hyperbola multipliers."""

from __future__ import annotations

import argparse
import itertools
import json

from hyperbola_layer_selection_sat import solve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--layers", type=int, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--stop-after-hits", type=int, default=1)
    args = parser.parse_args()

    tested = 0
    hits = 0
    statuses: dict[str, int] = {}
    for multipliers in itertools.combinations(range(1, args.p), args.layers):
        result = solve(
            args.p,
            multipliers,
            args.workers,
            args.time_limit,
            seed=args.p * 1000003 + tested,
            symmetry="none",
        )
        tested += 1
        status = result["status"]
        statuses[status] = statuses.get(status, 0) + 1
        if result.get("verification", {}).get("valid"):
            hits += 1
            print(
                json.dumps(
                    {
                        "event": "hit",
                        "p": args.p,
                        "layers": args.layers,
                        "tested": tested,
                        "multipliers": multipliers,
                        "selected_layer_histogram": result[
                            "selected_layer_histogram"
                        ],
                        "selected_points": result["selected_points"],
                    }
                ),
                flush=True,
            )
            if args.stop_after_hits and hits >= args.stop_after_hits:
                break
        elif tested % 100 == 0:
            print(
                json.dumps(
                    {
                        "event": "progress",
                        "p": args.p,
                        "layers": args.layers,
                        "tested": tested,
                        "hits": hits,
                        "statuses": statuses,
                    }
                ),
                flush=True,
            )
    print(
        json.dumps(
            {
                "event": "summary",
                "p": args.p,
                "layers": args.layers,
                "tested": tested,
                "hits": hits,
                "statuses": statuses,
            }
        )
    )


if __name__ == "__main__":
    main()
