"""Measure the determinant product and its p-adic spectrum in known NTIL sets.

For a no-three-in-line set S, every unordered triple has a nonzero integer
determinant.  Therefore

    Delta(S) = product_{A,B,C in S} |det(B-A,C-A)|

is a positive integer.  Factoring all determinants gives the exact identity

    log Delta = sum_p v_p(Delta) log p
              = sum_p sum_{a >= 1} T_{p^a} log p,

where T_q is the number of triples whose determinant is divisible by q.

This script decodes one compact C4 record for every available even order and
computes that spectrum.  The largest determinant is only (n-1)^2, so a small
smallest-prime-factor table makes the calculation inexpensive even for n=72.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
from collections import Counter
from pathlib import Path


ALPHABET = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "#$%&@?!()[]<>{}=*+|-/~^_:;,.|"
)
VALUE = {character: index for index, character in enumerate(ALPHABET)}
SYMMETRY_MARKERS = set(".:/-ocx+*")


def decode_record(text: str, n: int, coordinate_format: bool) -> list[tuple[int, int]]:
    text = text.strip()
    if coordinate_format:
        values = [int(value) for value in text.split()]
        if len(values) != 4 * n:
            raise ValueError(
                f"n={n}: coordinate record has {len(values)}, expected {4*n}"
            )
        return list(zip(values[::2], values[1::2]))
    body = text[1:] if text[0] in SYMMETRY_MARKERS else text
    if len(body) < 2 * n:
        raise ValueError(f"n={n}: compact record has only {len(body)} symbols")
    return [
        (row, VALUE[body[2 * row + offset]])
        for row in range(n)
        for offset in (0, 1)
    ]


def first_record(path: Path, n: int) -> list[tuple[int, int]]:
    coordinate_format = path.suffix == ".mvr" or path.name.endswith("_coords.txt")
    text = next(line for line in path.read_text().splitlines() if line.strip())
    return decode_record(text, n, coordinate_format)


def smallest_prime_factors(limit: int) -> list[int]:
    spf = list(range(limit + 1))
    if limit >= 1:
        spf[1] = 1
    for p in range(2, math.isqrt(limit) + 1):
        if spf[p] != p:
            continue
        for value in range(p * p, limit + 1, p):
            if spf[value] == value:
                spf[value] = p
    return spf


def factor(value: int, spf: list[int]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    while value > 1:
        p = spf[value]
        exponent = 0
        while value % p == 0:
            value //= p
            exponent += 1
        result.append((p, exponent))
    return result


def determinant_spectrum(points: list[tuple[int, int]], n: int) -> dict:
    if len(points) != 2 * n or len(set(points)) != 2 * n:
        raise ValueError(f"n={n}: record does not contain 2n distinct points")
    row_counts = Counter(x for x, _ in points)
    column_counts = Counter(y for _, y in points)
    if any(row_counts[i] != 2 for i in range(n)):
        raise ValueError(f"n={n}: row saturation failed")
    if any(column_counts[i] != 2 for i in range(n)):
        raise ValueError(f"n={n}: column saturation failed")

    maximum = (n - 1) ** 2
    spf = smallest_prime_factors(maximum)
    determinant_histogram: Counter[int] = Counter()
    valuation: Counter[int] = Counter()
    divisible: Counter[int] = Counter()
    prime_power_divisible: Counter[int] = Counter()
    log_product = 0.0
    minimum_seen = maximum
    maximum_seen = 0

    for (x1, y1), (x2, y2), (x3, y3) in itertools.combinations(points, 3):
        determinant = abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
        if determinant == 0:
            raise ValueError(f"n={n}: collinear triple found")
        determinant_histogram[determinant] += 1
        log_product += math.log(determinant)
        minimum_seen = min(minimum_seen, determinant)
        maximum_seen = max(maximum_seen, determinant)
        for p, exponent in factor(determinant, spf):
            divisible[p] += 1
            valuation[p] += exponent
            power = p
            for _ in range(exponent):
                prime_power_divisible[power] += 1
                power *= p

    triples = math.comb(2 * n, 3)
    reconstructed_log = sum(exponent * math.log(p) for p, exponent in valuation.items())
    if abs(reconstructed_log - log_product) > 1e-7 * max(1.0, log_product):
        raise AssertionError("prime factorisation did not reconstruct log product")

    weighted_by_prime = {
        p: valuation[p] * math.log(p) for p in sorted(valuation)
    }
    geometric_mean = math.exp(log_product / triples)
    return {
        "n": n,
        "points": len(points),
        "triples": triples,
        "minimum_determinant": minimum_seen,
        "maximum_determinant_seen": maximum_seen,
        "maximum_possible_determinant": maximum,
        "log_determinant_product": log_product,
        "log_product_upper_bound": triples * math.log(maximum),
        "upper_bound_fill_ratio": log_product / (triples * math.log(maximum)),
        "geometric_mean_determinant": geometric_mean,
        "geometric_mean_over_maximum": geometric_mean / maximum,
        "valuation_by_prime": dict(sorted(valuation.items())),
        "triples_divisible_by_prime": dict(sorted(divisible.items())),
        "prime_power_divisibility": dict(sorted(prime_power_divisible.items())),
        "log_weight_by_prime": weighted_by_prime,
        "top_determinants": determinant_histogram.most_common(20),
    }


def choose_sources(cache: Path, minimum_n: int, maximum_n: int) -> dict[int, Path]:
    pattern = re.compile(r"^n(\d+)_rot4(?:\.(?:few|mvr))?$")
    candidates: dict[int, list[Path]] = {}
    for path in cache.iterdir():
        match = pattern.match(path.name)
        if not match:
            continue
        n = int(match.group(1))
        if n % 2 or not (minimum_n <= n <= maximum_n):
            continue
        candidates.setdefault(n, []).append(path)

    chosen: dict[int, Path] = {}
    for n, paths in candidates.items():
        # Prefer the full compact file, then .few, then coordinate .mvr.
        chosen[n] = min(
            paths,
            key=lambda path: (
                path.suffix == ".mvr",
                path.suffix == ".few",
                len(path.name),
            ),
        )
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--minimum-n", type=int, default=6)
    parser.add_argument("--maximum-n", type=int, default=72)
    parser.add_argument(
        "--orders",
        type=int,
        nargs="*",
        help="optional explicit list of orders; otherwise use every available even order",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write the complete JSON record here and keep stdout compact",
    )
    args = parser.parse_args()

    sources = choose_sources(args.cache, args.minimum_n, args.maximum_n)
    if args.orders:
        missing = [n for n in args.orders if n not in sources]
        if missing:
            raise FileNotFoundError(f"no rot4 source for orders {missing}")
        orders = args.orders
    else:
        orders = sorted(sources)

    records = []
    for n in orders:
        path = sources[n]
        points = first_record(path, n)
        record = determinant_spectrum(points, n)
        record["source"] = str(path)
        records.append(record)
        print(
            f"n={n:2d} triples={record['triples']:7d} "
            f"fill={record['upper_bound_fill_ratio']:.6f} "
            f"gm/max={record['geometric_mean_over_maximum']:.6f}",
            flush=True,
        )

    summary = {
        "description": "Exact determinant-product spectra of known C4 NTIL records",
        "records": records,
    }
    encoded = json.dumps(summary, indent=2)
    if args.output:
        args.output.write_text(encoded)
        print(f"wrote {args.output}")
    else:
        print("JSON_BEGIN")
        print(encoded)


if __name__ == "__main__":
    main()
