"""Scan known C4 NTIL solutions for centered modular-circle concentration.

For an even n C4 solution, each four-point orbit has a representative
(x,y) in the top-left n/2 square.  All four points have the same value of

    R_p(x,y) = (2x-(n-1))^2 + (2y-(n-1))^2  (mod p),

so a residue class occupied by t representatives gives 4t solution points
on one centered circle over F_p.

The symmetry-matched null model randomly relabels the vertices of the exact
undirected total-degree-two fundamental graph.  This preserves its loops,
cycle structure, and row/column degree pattern.  For each prime we estimate
the tail probability of the observed maximum radius multiplicity.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import random
from pathlib import Path

from analyze_determinant_product import choose_sources, first_record


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    return all(value % divisor for divisor in range(2, math.isqrt(value) + 1))


def representative_edges(points: list[tuple[int, int]], n: int) -> list[tuple[int, int]]:
    m = n // 2
    edges = [(x, y) for x, y in points if x < m and y < m]
    if len(edges) != m:
        raise ValueError(f"n={n}: found {len(edges)} fundamental points, expected {m}")
    degrees = collections.Counter()
    for x, y in edges:
        degrees[x] += 1
        degrees[y] += 1
    if any(degrees[vertex] != 2 for vertex in range(m)):
        raise ValueError(f"n={n}: fundamental graph is not total-degree two")
    return edges


def maximum_radius_multiplicity(
    edges: list[tuple[int, int]], labels: list[int], n: int, p: int
) -> int:
    center_twice = n - 1
    radii = collections.Counter(
        (
            (2 * labels[x] - center_twice) ** 2
            + (2 * labels[y] - center_twice) ** 2
        )
        % p
        for x, y in edges
    )
    return max(radii.values())


def scan_order(
    n: int,
    path: Path,
    samples: int,
    seed: int,
    lower_factor: float,
    upper_factor: float,
) -> dict:
    points = first_record(path, n)
    edges = representative_edges(points, n)
    m = n // 2
    primes = [
        value
        for value in range(
            max(2, math.ceil(lower_factor * n)),
            math.floor(upper_factor * n) + 1,
        )
        if is_prime(value)
    ]
    identity = list(range(m))
    exact = {
        p: maximum_radius_multiplicity(edges, identity, n, p) for p in primes
    }
    exceed = collections.Counter()
    histograms = {p: collections.Counter() for p in primes}
    rng = random.Random(seed + 1_000_003 * n)
    labels = list(range(m))
    for _ in range(samples):
        rng.shuffle(labels)
        for p in primes:
            observed = maximum_radius_multiplicity(edges, labels, n, p)
            histograms[p][observed] += 1
            exceed[p] += observed >= exact[p]
    records = [
        {
            "p": p,
            "exact_orbits": exact[p],
            "exact_points": 4 * exact[p],
            "tail_probability": exceed[p] / samples,
            "histogram": dict(sorted(histograms[p].items())),
        }
        for p in primes
    ]
    records.sort(key=lambda item: (item["tail_probability"], -item["exact_orbits"]))
    return {
        "n": n,
        "source": str(path),
        "fundamental_edges": edges,
        "samples": samples,
        "prime_interval": [lower_factor, upper_factor],
        "primes_tested": len(primes),
        "best": records[0] if records else None,
        "bonferroni_bound": (
            min(1.0, records[0]["tail_probability"] * len(primes))
            if records
            else None
        ),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--minimum-n", type=int, default=6)
    parser.add_argument("--maximum-n", type=int, default=72)
    parser.add_argument("--samples", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--lower-factor", type=float, default=0.5)
    parser.add_argument("--upper-factor", type=float, default=2.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sources = choose_sources(args.cache, args.minimum_n, args.maximum_n)
    results = []
    for n in sorted(sources):
        result = scan_order(
            n,
            sources[n],
            args.samples,
            args.seed,
            args.lower_factor,
            args.upper_factor,
        )
        results.append(result)
        print(
            json.dumps(
                {
                    "n": n,
                    "best": result["best"],
                    "bonferroni_bound": result["bonferroni_bound"],
                }
            ),
            flush=True,
        )
    args.output.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
