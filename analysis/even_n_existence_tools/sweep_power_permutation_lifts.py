"""Test finite-field power permutations in the exact 2p lift normal form.

Affine and inverse permutations were already tested.  For primes p whose
multiplicative group has other units e, x -> x**e is a genuinely new
permutation-polynomial family.  We test two tightly specified four-layer
bases:

* vertical:       x**e + b for four distinct output shifts b;
* horizontal:     (x+a)**e for four distinct input shifts a.

All arithmetic in the base graph is modulo p.  The existing exact lift solver
then chooses the two high bits of every occurrence and either returns a fully
verified 4p-point NTIL set in the 2p grid or proves this fixed base infeasible.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import time

from four_permutation_lift_sat import is_prime, solve


def exponents(p: int) -> list[int]:
    """Return non-affine, non-inverse power-permutation exponents."""

    return [
        exponent
        for exponent in range(2, p - 2)
        if math.gcd(exponent, p - 1) == 1
    ]


def make_layers(
    p: int,
    exponent: int,
    shifts: tuple[int, int, int, int],
    mode: str,
) -> list[list[int]]:
    if mode == "vertical":
        return [
            [(pow(x, exponent, p) + shift) % p for x in range(p)]
            for shift in shifts
        ]
    if mode == "horizontal":
        return [
            [pow((x + shift) % p, exponent, p) for x in range(p)]
            for shift in shifts
        ]
    raise ValueError(mode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument(
        "--mode",
        choices=("vertical", "horizontal", "both"),
        default="both",
    )
    parser.add_argument("--time-limit", type=float, default=5.0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--maximum-tests", type=int, default=0)
    parser.add_argument("--continue-after-sat", action="store_true")
    args = parser.parse_args()
    if not is_prime(args.p):
        raise SystemExit("p must be prime")

    powers = exponents(args.p)
    modes = ("vertical", "horizontal") if args.mode == "both" else (args.mode,)
    started = time.perf_counter()
    tested = 0
    status_counts: dict[str, int] = {}
    hits = []
    for exponent in powers:
        for mode in modes:
            for shifts in itertools.combinations(range(args.p), 4):
                if args.maximum_tests and tested >= args.maximum_tests:
                    break
                layers = make_layers(args.p, exponent, shifts, mode)
                result = solve(
                    args.p,
                    layers,
                    time_limit=args.time_limit,
                    workers=args.workers,
                )
                tested += 1
                status = result["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
                if status in ("OPTIMAL", "FEASIBLE"):
                    witness = {
                        "hit": True,
                        "p": args.p,
                        "exponent": exponent,
                        "mode": mode,
                        "shifts": shifts,
                        "layers": layers,
                        "result": result,
                    }
                    hits.append(witness)
                    print(json.dumps(witness, indent=2), flush=True)
                    if not args.continue_after_sat:
                        print(
                            json.dumps(
                                {
                                    "summary": True,
                                    "p": args.p,
                                    "tested": tested,
                                    "status_counts": status_counts,
                                    "hits": len(hits),
                                    "elapsed_seconds": time.perf_counter() - started,
                                },
                                indent=2,
                            ),
                            flush=True,
                        )
                        return
                elif tested % 25 == 0:
                    print(
                        json.dumps(
                            {
                                "progress": tested,
                                "p": args.p,
                                "exponent": exponent,
                                "mode": mode,
                                "status_counts": status_counts,
                                "elapsed_seconds": time.perf_counter() - started,
                            }
                        ),
                        flush=True,
                    )
            if args.maximum_tests and tested >= args.maximum_tests:
                break
        if args.maximum_tests and tested >= args.maximum_tests:
            break

    print(
        json.dumps(
            {
                "summary": True,
                "p": args.p,
                "tested": tested,
                "exponents": powers,
                "status_counts": status_counts,
                "hits": len(hits),
                "elapsed_seconds": time.perf_counter() - started,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
