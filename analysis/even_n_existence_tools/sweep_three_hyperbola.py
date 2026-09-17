"""Sweep multiplier triples for the three-hyperbola deletion model."""

from __future__ import annotations

import argparse
import itertools
import json

from three_hyperbola_cover_sat import solve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=10.0)
    parser.add_argument("--stop-after-hits", type=int, default=0)
    args = parser.parse_args()

    hits = 0
    tested = 0
    status_histogram: dict[str, int] = {}
    for multipliers in itertools.combinations(range(1, args.p), 3):
        result = solve(
            args.p,
            multipliers,
            args.workers,
            args.time_limit,
            seed=1000003 * args.p + tested,
        )
        tested += 1
        status = result["status"]
        status_histogram[status] = status_histogram.get(status, 0) + 1
        if result.get("verification", {}).get("valid"):
            hits += 1
            print(
                json.dumps(
                    {
                        "event": "hit",
                        "p": args.p,
                        "tested": tested,
                        "multipliers": multipliers,
                        "removed_layer_histogram": result[
                            "removed_layer_histogram"
                        ],
                        "removed_points": result["removed_points"],
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
                        "tested": tested,
                        "hits": hits,
                        "statuses": status_histogram,
                    }
                ),
                flush=True,
            )

    print(
        json.dumps(
            {
                "event": "summary",
                "p": args.p,
                "tested": tested,
                "hits": hits,
                "statuses": status_histogram,
            }
        )
    )


if __name__ == "__main__":
    main()
