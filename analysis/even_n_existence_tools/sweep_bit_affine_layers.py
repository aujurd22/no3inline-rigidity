"""Search unions of two affine bit-permutation graphs on 2^k coordinates.

A layer has the form

    y = permute_bits(x, pi) XOR mask.

It is a permutation graph, so a disjoint pair automatically has two points
in each row and column.  The search first discards layers containing an
internal collinear triple and then tests every (or a bounded number of)
pairs of surviving layers.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random


def permute_bits(value: int, permutation: tuple[int, ...]) -> int:
    result = 0
    for target, source in enumerate(permutation):
        result |= ((value >> source) & 1) << target
    return result


def independent_column_tuples(k: int):
    """Yield ordered bases of F_2^k, encoded as integer column vectors."""

    def rank(vectors: tuple[int, ...]) -> int:
        basis = [0] * k
        result = 0
        for value in vectors:
            current = value
            while current:
                pivot = current.bit_length() - 1
                if basis[pivot]:
                    current ^= basis[pivot]
                else:
                    basis[pivot] = current
                    result += 1
                    break
        return result

    def extend(prefix: tuple[int, ...]):
        if len(prefix) == k:
            yield prefix
            return
        current_rank = len(prefix)
        for vector in range(1, 1 << k):
            candidate = prefix + (vector,)
            if rank(candidate) == current_rank + 1:
                yield from extend(candidate)

    yield from extend(())


def linear_image(value: int, columns: tuple[int, ...]) -> int:
    result = 0
    bit = 0
    current = value
    while current:
        if current & 1:
            result ^= columns[bit]
        current >>= 1
        bit += 1
    return result


def normal_direction(dx: int, dy: int) -> tuple[int, int]:
    divisor = math.gcd(abs(dx), abs(dy))
    dx //= divisor
    dy //= divisor
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return dx, dy


def no_three(points: list[tuple[int, int]]) -> bool:
    for first_index, first in enumerate(points):
        seen: set[tuple[int, int]] = set()
        for second_index, second in enumerate(points):
            if first_index == second_index:
                continue
            direction = normal_direction(
                second[0] - first[0], second[1] - first[1]
            )
            if direction in seen:
                return False
            seen.add(direction)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bits", type=int, required=True)
    parser.add_argument("--pair-limit", type=int, default=0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--general-linear",
        action="store_true",
        help="use every invertible F2-linear map, not only bit-coordinate permutations",
    )
    args = parser.parse_args()
    k = args.bits
    n = 1 << k

    layers = []
    tested_layers = 0
    transformations = (
        independent_column_tuples(k)
        if args.general_linear
        else itertools.permutations(range(k))
    )
    for transformation in transformations:
        if args.general_linear:
            base = [linear_image(x, transformation) for x in range(n)]
        else:
            base = [permute_bits(x, transformation) for x in range(n)]
        for mask in range(n):
            tested_layers += 1
            values = tuple(value ^ mask for value in base)
            points = [(x, values[x]) for x in range(n)]
            if no_three(points):
                layers.append((transformation, mask, values))

    total_pairs = len(layers) * (len(layers) - 1) // 2
    if args.pair_limit and total_pairs > args.pair_limit:
        generator = random.Random(args.seed)
        sampled: set[tuple[int, int]] = set()
        while len(sampled) < args.pair_limit:
            first_index = generator.randrange(len(layers))
            second_index = generator.randrange(len(layers) - 1)
            if second_index >= first_index:
                second_index += 1
            if first_index > second_index:
                first_index, second_index = second_index, first_index
            sampled.add((first_index, second_index))
        pairs = list(sampled)
    else:
        pairs = list(itertools.combinations(range(len(layers)), 2))
    hits = []
    disjoint_pairs = 0
    for first_index, second_index in pairs:
        first = layers[first_index]
        second = layers[second_index]
        if any(a == b for a, b in zip(first[2], second[2])):
            continue
        disjoint_pairs += 1
        points = [(x, first[2][x]) for x in range(n)]
        points.extend((x, second[2][x]) for x in range(n))
        if no_three(points):
            hits.append(
                {
                    "first_permutation": first[0],
                    "first_mask": first[1],
                    "second_permutation": second[0],
                    "second_mask": second[1],
                    "points": points,
                }
            )
            break

    print(
        json.dumps(
            {
                "bits": k,
                "n": n,
                "tested_layers": tested_layers,
                "internally_valid_layers": len(layers),
                "pairs_tested": len(pairs),
                "disjoint_pairs": disjoint_pairs,
                "hits": hits,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
