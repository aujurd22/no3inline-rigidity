"""Count triples whose determinant has a prime divisor at least sqrt(n).

For N=2n points, the universal direction-box lower bound is

    T_p >= ceil(N F_p(N-1) / 3),

where F_p(M) is the minimum number of same-box pairs after distributing M
objects among p+1 directions.  A nonzero determinant of magnitude < n^2 has
at most three distinct prime divisors >= sqrt(n).  Dividing the summed T_p
lower bounds by three therefore gives a finite union lower bound.
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
from pathlib import Path

from analyze_large_prime_carries import (
    decode_solution,
    determinant,
    locate,
    primes_below,
)


def direction_box_pair_minimum(m: int, p: int) -> int:
    quotient, remainder = divmod(m, p + 1)
    return (p + 1) * math.comb(quotient, 2) + quotient * remainder


def analyze(points: list[tuple[int, int]], n: int) -> dict:
    threshold = math.sqrt(n)
    primes = [
        p for p in primes_below((n - 1) ** 2 + 1) if p >= threshold
    ]
    relevant_for_lower_bound = [p for p in primes if p <= 2 * n - 2]
    n_points = 2 * n

    exact_lower_bounds = {}
    lower_bound_sum = 0
    log_weighted_lower_bound_sum = 0.0
    for p in relevant_for_lower_bound:
        numerator = n_points * direction_box_pair_minimum(n_points - 1, p)
        lower_bound = math.ceil(numerator / 3)
        exact_lower_bounds[p] = lower_bound
        lower_bound_sum += lower_bound
        log_weighted_lower_bound_sum += (
            lower_bound * math.log(p) / (2 * math.log(n - 1))
        )

    multiplicity_histogram: collections.Counter[int] = collections.Counter()
    union_count = 0
    summed_actual_modular_counts = 0
    ordinary = 0
    multiplicity_by_absolute_determinant = [
        0
    ] * ((n - 1) ** 2 + 1)
    for value in range(1, len(multiplicity_by_absolute_determinant)):
        multiplicity_by_absolute_determinant[value] = sum(
            value % p == 0 for p in primes
        )
    for triple in itertools.combinations(points, 3):
        value = determinant(*triple)
        if value == 0:
            ordinary += 1
            continue
        multiplicity = multiplicity_by_absolute_determinant[abs(value)]
        multiplicity_histogram[multiplicity] += 1
        if multiplicity:
            union_count += 1
            summed_actual_modular_counts += multiplicity

    total_triples = math.comb(2 * n, 3)
    finite_union_lower_bound = math.ceil(lower_bound_sum / 3)
    finite_log_weight_union_lower_bound = math.ceil(
        log_weighted_lower_bound_sum
    )
    return {
        "n": n,
        "point_count": len(points),
        "threshold_sqrt_n": threshold,
        "ordinary_collinear_triples": ordinary,
        "total_triples": total_triples,
        "relevant_prime_count": len(relevant_for_lower_bound),
        "minimum_relevant_prime": min(relevant_for_lower_bound, default=None),
        "maximum_relevant_prime": max(relevant_for_lower_bound, default=None),
        "summed_exact_direction_box_lower_bounds": lower_bound_sum,
        "finite_union_lower_bound_after_dividing_by_three": (
            finite_union_lower_bound
        ),
        "finite_lower_bound_fraction_of_all_triples": (
            finite_union_lower_bound / total_triples
        ),
        "finite_log_weight_union_lower_bound": (
            finite_log_weight_union_lower_bound
        ),
        "finite_log_weight_lower_bound_fraction_of_all_triples": (
            finite_log_weight_union_lower_bound / total_triples
        ),
        "actual_union_count": union_count,
        "actual_union_fraction_of_all_triples": union_count / total_triples,
        "summed_actual_modular_counts": summed_actual_modular_counts,
        "actual_mean_multiplicity_conditioned_on_union": (
            summed_actual_modular_counts / union_count if union_count else None
        ),
        "maximum_observed_multiplicity": max(multiplicity_histogram, default=0),
        "multiplicity_histogram": dict(sorted(multiplicity_histogram.items())),
        "exact_lower_bound_by_prime": exact_lower_bounds,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--n", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = {
        "results": [
            analyze(decode_solution(locate(args.cache, n), n), n) for n in args.n
        ]
    }
    text = json.dumps(payload, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
