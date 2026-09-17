"""Exact SAT experiments for a two-lift construction on a 2p x 2p grid.

For a prime p and permutations f,g of F_p, construct two permutations of
Z_{2p}:

    F(x + p*e) = f(x) + p*(e xor a[x])
    G(x + p*e) = g(x) + p*(e xor b[x])

where a[x], b[x] are Boolean variables.  Their graphs have 4p points total,
with exactly two points in every row and column.  We enumerate all triples of
point templates and forbid precisely the Boolean assignments that make a
triple collinear over the integers.

The model is exact: SAT gives a verified 2n-point NTIL set for n=2p; UNSAT
rules out the selected pair (f,g) for every choice of lift bits.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class Template:
    layer: int  # 0 = F, 1 = G
    x: int
    eps: int
    row: int
    residue_y: int


def is_prime(p: int) -> bool:
    if p < 2:
        return False
    for d in range(2, math.isqrt(p) + 1):
        if p % d == 0:
            return False
    return True


def inverse_permutation(p: int) -> list[int]:
    return [0] + [pow(x, -1, p) for x in range(1, p)]


def power_permutation(p: int, exponent: int) -> list[int]:
    if math.gcd(exponent, p - 1) != 1:
        raise ValueError(f"x^{exponent} is not a permutation of F_{p}")
    return [pow(x, exponent, p) for x in range(p)]


def affine_transform(values: list[int], mul: int, add: int, p: int) -> list[int]:
    if math.gcd(mul, p) != 1:
        raise ValueError("mul must be nonzero modulo p")
    return [(mul * y + add) % p for y in values]


def point_for(template: Template, bit: int, p: int) -> tuple[int, int]:
    return (
        template.row,
        template.residue_y + p * (template.eps ^ bit),
    )


def collinear(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> bool:
    return (b[0] - a[0]) * (c[1] - a[1]) == (b[1] - a[1]) * (c[0] - a[0])


def verify(points: list[tuple[int, int]], n: int) -> dict:
    unique = len(set(points))
    row_counts = [0] * n
    col_counts = [0] * n
    for x, y in points:
        row_counts[x] += 1
        col_counts[y] += 1
    bad = []
    for a, b, c in itertools.combinations(points, 3):
        if collinear(a, b, c):
            bad.append((a, b, c))
            if len(bad) >= 10:
                break
    return {
        "point_count": len(points),
        "unique_count": unique,
        "rows_exactly_two": all(v == 2 for v in row_counts),
        "cols_exactly_two": all(v == 2 for v in col_counts),
        "collinear_triples_sample": bad,
        "valid": (
            len(points) == 2 * n
            and unique == 2 * n
            and all(v == 2 for v in row_counts)
            and all(v == 2 for v in col_counts)
            and not bad
        ),
    }


def solve_lift(
    p: int,
    f: list[int],
    g: list[int],
    time_limit: float,
    workers: int,
) -> dict:
    if sorted(f) != list(range(p)) or sorted(g) != list(range(p)):
        raise ValueError("f and g must be permutations")
    if any(f[x] == g[x] for x in range(p)):
        return {
            "status": "REJECTED",
            "reason": "the two permutation graphs overlap modulo p",
        }

    templates = []
    for layer, values in enumerate((f, g)):
        for x in range(p):
            for eps in (0, 1):
                templates.append(
                    Template(
                        layer=layer,
                        x=x,
                        eps=eps,
                        row=x + p * eps,
                        residue_y=values[x],
                    )
                )

    model = cp_model.CpModel()
    bits = [
        [model.new_bool_var(f"bit_{layer}_{x}") for x in range(p)]
        for layer in range(2)
    ]

    forbidden = 0
    candidate_triples = 0
    modular_triples = 0

    for triple in itertools.combinations(templates, 3):
        # Rows are fixed. Three templates sharing a row can be skipped because
        # there are only two layers and overlapping points were rejected.
        if len({t.row for t in triple}) < 3:
            continue

        candidate_triples += 1
        # Integer collinearity implies modular collinearity.  This exact cheap
        # filter removes nearly all template triples.
        a0 = (triple[0].x, triple[0].residue_y)
        b0 = (triple[1].x, triple[1].residue_y)
        c0 = (triple[2].x, triple[2].residue_y)
        det_mod = (
            (b0[0] - a0[0]) * (c0[1] - a0[1])
            - (b0[1] - a0[1]) * (c0[0] - a0[0])
        ) % p
        if det_mod != 0:
            continue
        modular_triples += 1

        keys = sorted({(t.layer, t.x) for t in triple})
        for assignment in itertools.product((0, 1), repeat=len(keys)):
            value = dict(zip(keys, assignment))
            pts = [
                point_for(t, value[(t.layer, t.x)], p)
                for t in triple
            ]
            if not collinear(*pts):
                continue
            literals = []
            for key, val in zip(keys, assignment):
                var = bits[key[0]][key[1]]
                literals.append(var.Not() if val else var)
            model.add_bool_or(literals)
            forbidden += 1

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.log_search_progress = False
    started = time.perf_counter()
    status = solver.solve(model)
    elapsed = time.perf_counter() - started
    status_name = solver.status_name(status)

    result = {
        "p": p,
        "n": 2 * p,
        "status": status_name,
        "elapsed_seconds": elapsed,
        "candidate_template_triples": candidate_triples,
        "modular_template_triples": modular_triples,
        "forbidden_boolean_patterns": forbidden,
        "branches": solver.num_branches,
        "conflicts": solver.num_conflicts,
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        a_bits = [solver.value(v) for v in bits[0]]
        b_bits = [solver.value(v) for v in bits[1]]
        points = []
        for t in templates:
            bit = a_bits[t.x] if t.layer == 0 else b_bits[t.x]
            points.append(point_for(t, bit, p))
        result["a_bits"] = a_bits
        result["b_bits"] = b_bits
        result["points"] = points
        result["verification"] = verify(points, 2 * p)
    return result


def family_values(p: int, family: str, exponent: int) -> list[int]:
    if family == "inverse":
        return inverse_permutation(p)
    if family == "power":
        return power_permutation(p, exponent)
    raise ValueError(f"unknown family: {family}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p", type=int, required=True)
    parser.add_argument("--family", choices=("inverse", "power"), default="inverse")
    parser.add_argument("--exponent", type=int, default=1)
    parser.add_argument("--g-mul", type=int, default=1)
    parser.add_argument("--g-add", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not is_prime(args.p):
        raise SystemExit("p must be prime")
    f = family_values(args.p, args.family, args.exponent)
    g = affine_transform(f, args.g_mul % args.p, args.g_add % args.p, args.p)
    result = solve_lift(args.p, f, g, args.time_limit, args.workers)
    result["family"] = args.family
    result["exponent"] = args.exponent
    result["g_mul"] = args.g_mul
    result["g_add"] = args.g_add
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
