"""Monte Carlo diagnostics for the K-scale translated-inverse lift family.

Labels are sampled from the exact row/column-balanced distribution:

* in each base row, the 2K occurrences receive every high-row label twice;
* in each base column, the 2K occurrences receive every high-column label
  twice;
* the row-label and column-label assignments are independent.

This always produces 2n distinct points with exactly two in every exact row
and column.  We count Euclidean collinear triples and occupied overfull lines
to measure whether the algebraic support removes the usual n log n random
barrier.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import random
import statistics
import time

from fibered_mobius_sat import is_prime, mobius_permutation


Point = tuple[int, int]
Occurrence = tuple[int, int]  # layer, base row


def normalise(dx: int, dy: int) -> tuple[int, int]:
    divisor = math.gcd(abs(dx), abs(dy))
    dx //= divisor
    dy //= divisor
    if dx < 0 or (dx == 0 and dy < 0):
        dx = -dx
        dy = -dy
    return dx, dy


def bad_statistics(points: list[Point]) -> tuple[int, int, int]:
    """Return triple count, overfull-line count, and maximum occupancy."""

    lines: dict[tuple[int, int, int], set[Point]] = {}
    for first_index, first in enumerate(points):
        for second in points[first_index + 1 :]:
            dx, dy = normalise(second[0] - first[0], second[1] - first[1])
            # A canonical integer line is dy*x - dx*y = intercept.
            intercept = dy * first[0] - dx * first[1]
            key = (dx, dy, intercept)
            bucket = lines.setdefault(key, set())
            bucket.add(first)
            bucket.add(second)
    occupancies = [len(bucket) for bucket in lines.values() if len(bucket) >= 3]
    return (
        sum(math.comb(occupancy, 3) for occupancy in occupancies),
        len(occupancies),
        max(occupancies, default=2),
    )


def sample_points(
    k: int,
    p: int,
    permutations: list[list[int]],
    rng: random.Random,
) -> list[Point]:
    occurrence_count = 2 * k
    high_rows: dict[Occurrence, int] = {}
    for residue in range(p):
        labels = [label for label in range(k) for _ in range(2)]
        rng.shuffle(labels)
        for layer, label in enumerate(labels):
            high_rows[(layer, residue)] = label

    by_column: dict[int, list[Occurrence]] = {
        column: [] for column in range(p)
    }
    for layer, permutation in enumerate(permutations):
        for residue, column in enumerate(permutation):
            by_column[column].append((layer, residue))
    high_columns: dict[Occurrence, int] = {}
    for column, occurrences in by_column.items():
        if len(occurrences) != occurrence_count:
            raise AssertionError("base column did not have 2K occurrences")
        labels = [label for label in range(k) for _ in range(2)]
        rng.shuffle(labels)
        for occurrence, label in zip(occurrences, labels):
            high_columns[occurrence] = label

    return [
        (
            residue + high_rows[(layer, residue)] * p,
            permutations[layer][residue]
            + high_columns[(layer, residue)] * p,
        )
        for layer in range(occurrence_count)
        for residue in range(p)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--shifts", type=int, nargs="*")
    parser.add_argument("--u", type=int, default=0)
    parser.add_argument("--v", type=int, default=0)
    parser.add_argument("--multiplier", type=int, default=1)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=1000)
    args = parser.parse_args()
    if not is_prime(args.p):
        raise SystemExit("p must be prime")
    shifts = args.shifts if args.shifts else list(range(2 * args.k))
    shifts = [shift % args.p for shift in shifts]
    if len(shifts) != 2 * args.k or len(set(shifts)) != 2 * args.k:
        raise SystemExit("need 2K distinct shifts")
    base = mobius_permutation(
        args.p,
        args.u % args.p,
        args.v % args.p,
        args.multiplier % args.p,
    )
    permutations = [
        [(value + shift) % args.p for value in base]
        for shift in shifts
    ]

    rng = random.Random(args.seed)
    triples = []
    lines = []
    maxima = []
    best = None
    zero_count = 0
    started = time.perf_counter()
    for sample in range(1, args.samples + 1):
        points = sample_points(args.k, args.p, permutations, rng)
        triple_count, line_count, maximum = bad_statistics(points)
        triples.append(triple_count)
        lines.append(line_count)
        maxima.append(maximum)
        if best is None or (triple_count, line_count) < (best[0], best[1]):
            best = (triple_count, line_count, points)
        if triple_count == 0:
            zero_count += 1
            print(
                json.dumps(
                    {
                        "hit": True,
                        "sample": sample,
                        "points": points,
                    }
                ),
                flush=True,
            )
        if args.progress_every and sample % args.progress_every == 0:
            print(
                json.dumps(
                    {
                        "progress": sample,
                        "mean_triples": statistics.fmean(triples),
                        "best_triples": best[0],
                        "best_lines": best[1],
                        "zero_count": zero_count,
                        "elapsed_seconds": time.perf_counter() - started,
                    }
                ),
                flush=True,
            )

    result = {
        "summary": True,
        "k": args.k,
        "p": args.p,
        "n": args.k * args.p,
        "shifts": shifts,
        "u": args.u % args.p,
        "v": args.v % args.p,
        "multiplier": args.multiplier % args.p,
        "samples": args.samples,
        "mean_collinear_triples": statistics.fmean(triples),
        "median_collinear_triples": statistics.median(triples),
        "mean_overfull_lines": statistics.fmean(lines),
        "maximum_occupancy_histogram": dict(
            sorted(collections.Counter(maxima).items())
        ),
        "best_collinear_triples": best[0],
        "best_overfull_lines": best[1],
        "best_points": best[2],
        "zero_count": zero_count,
        "elapsed_seconds": time.perf_counter() - started,
    }
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
