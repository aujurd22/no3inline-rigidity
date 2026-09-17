"""Exhaust unions of two modular hyperbola permutation layers."""

from __future__ import annotations

import argparse
import itertools
import json
import math

from sweep_two_punctured_modular_lines import (
    bad_line_count,
    first_bad_line,
    is_prime,
)


def layer(p: int, multiplier: int) -> list[tuple[int, int]]:
    return [
        (x - 1, multiplier * pow(x, -1, p) % p - 1)
        for x in range(1, p)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maximum-p", type=int, default=101)
    parser.add_argument("--output")
    args = parser.parse_args()
    records = []
    for p in range(3, args.maximum_p + 1):
        if not is_prime(p):
            continue
        layers = {a: layer(p, a) for a in range(1, p)}
        best = None
        solutions = []
        for first, second in itertools.combinations(range(1, p), 2):
            points = layers[first] + layers[second]
            witness = first_bad_line(points)
            if witness is None:
                solutions.append((first, second))
                score = (0, 2)
            else:
                score = bad_line_count(points)
            candidate = {
                "multipliers": [first, second],
                "bad_lines": score[0],
                "maximum_line_size": score[1],
                "first_bad_line": witness,
            }
            if best is None or (
                candidate["bad_lines"],
                candidate["maximum_line_size"],
            ) < (
                best["bad_lines"],
                best["maximum_line_size"],
            ):
                best = candidate
        record = {
            "p": p,
            "n": p - 1,
            "pairs": math.comb(p - 1, 2),
            "solutions": solutions,
            "best": best,
        }
        records.append(record)
        print(json.dumps(record), flush=True)
    if args.output:
        with open(args.output, "w") as stream:
            json.dump(records, stream, indent=2)


if __name__ == "__main__":
    main()
