"""Search structured four-permutation bases for a satisfiable exact lift.

The goal is not to solve a new board by brute force.  Small-prime searches are
used to identify algebraic base families whose two-bit lifts remain feasible.
"""

from __future__ import annotations

import argparse
import json
import random
import time

from four_permutation_lift_sat import inverse_permutation, is_prime, solve


def affine_permutations(p: int) -> list[tuple[tuple, list[int]]]:
    return [
        (("affine", slope, intercept), [(slope * x + intercept) % p for x in range(p)])
        for slope in range(1, p)
        for intercept in range(p)
    ]


def transformed_inverse_permutations(p: int) -> list[tuple[tuple, list[int]]]:
    inverse = inverse_permutation(p)
    unique: dict[tuple[int, ...], tuple] = {}
    for input_slope in range(1, p):
        for input_intercept in range(p):
            transformed_input = [
                inverse[(input_slope * x + input_intercept) % p]
                for x in range(p)
            ]
            for output_slope in range(1, p):
                for output_intercept in range(p):
                    permutation = tuple(
                        (output_slope * value + output_intercept) % p
                        for value in transformed_input
                    )
                    unique.setdefault(
                        permutation,
                        (
                            "inverse",
                            input_slope,
                            input_intercept,
                            output_slope,
                            output_intercept,
                        ),
                    )
    return [(parameters, list(permutation)) for permutation, parameters in unique.items()]


def candidate_pool(mode: str, p: int) -> list[tuple[tuple, list[int]]]:
    if mode == "affine":
        return affine_permutations(p)
    if mode == "inverse":
        return transformed_inverse_permutations(p)
    if mode == "mixed":
        merged = affine_permutations(p) + transformed_inverse_permutations(p)
        unique: dict[tuple[int, ...], tuple] = {}
        for parameters, permutation in merged:
            unique.setdefault(tuple(permutation), parameters)
        return [(parameters, list(permutation)) for permutation, parameters in unique.items()]
    raise ValueError(mode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--mode", choices=("affine", "inverse", "mixed", "random"), required=True)
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=5.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--continue-after-sat", action="store_true")
    args = parser.parse_args()
    if not is_prime(args.p):
        raise SystemExit("p must be prime")

    rng = random.Random(args.seed)
    pool = None if args.mode == "random" else candidate_pool(args.mode, args.p)
    tested_keys: set[tuple[tuple[int, ...], ...]] = set()
    counts: dict[str, int] = {}
    satisfiable = []
    started = time.perf_counter()
    while len(tested_keys) < args.trials:
        if args.mode == "random":
            selected = []
            for layer in range(4):
                permutation = list(range(args.p))
                rng.shuffle(permutation)
                selected.append((("random", layer), permutation))
        else:
            selected = rng.sample(pool, 4)
        key = tuple(sorted(tuple(permutation) for _, permutation in selected))
        if key in tested_keys:
            continue
        tested_keys.add(key)
        parameters = [item[0] for item in selected]
        permutations = [item[1] for item in selected]
        result = solve(
            args.p,
            permutations,
            time_limit=args.time_limit,
            workers=args.workers,
        )
        status = result["status"]
        counts[status] = counts.get(status, 0) + 1
        if status in ("OPTIMAL", "FEASIBLE"):
            witness = {
                "trial": len(tested_keys),
                "parameters": parameters,
                "permutations": permutations,
                "result": result,
            }
            satisfiable.append(witness)
            print(json.dumps(witness, indent=2), flush=True)
            if not args.continue_after_sat:
                break
        elif len(tested_keys) % 25 == 0:
            print(
                json.dumps(
                    {
                        "progress": len(tested_keys),
                        "counts": counts,
                        "wall_seconds": time.perf_counter() - started,
                    }
                ),
                flush=True,
            )
    print(
        json.dumps(
            {
                "summary": True,
                "p": args.p,
                "mode": args.mode,
                "tested": len(tested_keys),
                "counts": counts,
                "satisfiable_found": len(satisfiable),
                "wall_seconds": time.perf_counter() - started,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
