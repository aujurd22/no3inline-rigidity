"""Recombine pairs of exact low-defect factors inside their edge-set unions."""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import random
from collections import Counter
from pathlib import Path

from joint_plateau_lns import local_descent
from signed_nae_core import geometry_bad_count
from weighted_factor_search import build_state, exact_weighted, is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def factor_key(edges):
    return tuple(sorted(tuple(sorted(edge)) for edge in edges))


def factor_distance(left, right):
    return 37 - len(set(left) & set(right))


def valid_factor(edges):
    if len(edges) != 37 or len(set(edges)) != 37:
        return False
    degree = Counter(vertex for edge in edges for vertex in edge)
    return set(degree) == set(range(37)) and set(degree.values()) == {2}


def projected_hint(primary, secondary, edges):
    first = {tuple(edge): bit for edge, bit in zip(primary["edges"], primary["bits"])}
    second = {tuple(edge): bit for edge, bit in zip(secondary["edges"], secondary["bits"])}
    return [first[edge] if edge in first else second[edge] for edge in edges]


def evaluate(payload):
    index, item, restarts = payload
    edges = [tuple(edge) for edge in item["edges"]]
    _, _, _, constant, jmat = build_state(edges)
    rng = random.Random(202607172000 + index)
    best = 10**9
    best_bits = None
    for hint in item["hints"]:
        value, bits = local_descent(constant, jmat, hint, rng, 5)
        if value < best:
            best, best_bits = value, bits
    for _ in range(restarts):
        start = [rng.getrandbits(1) for _ in edges]
        start[0] = 0
        value, bits = local_descent(constant, jmat, start, rng, 4)
        if value < best:
            best, best_bits = value, bits
    geometry = geometry_bad_count(37, edges, best_bits)
    assert geometry["bad_triples"] == best
    result = {key: value for key, value in item.items() if key != "hints"}
    result.update({"bits": best_bits, "bad_triples": best, "geometry": geometry})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--value-max", type=int, default=48)
    parser.add_argument("--distance-max", type=int, default=8)
    parser.add_argument("--candidate-cap", type=int, default=10000)
    parser.add_argument("--restarts", type=int, default=5)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=20)
    parser.add_argument("--exact-time", type=float, default=60.0)
    parser.add_argument("--out", default="factor_crossover.json")
    args = parser.parse_args()

    archive_payload = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    archive = [
        item
        for item in archive_payload["archive"]
        if item["value"] <= args.value_max and item["diagonal_safe"]
    ]
    archive_keys = {factor_key(item["edges"]) for item in archive}
    candidates = {}
    pair_stats = []
    total_combinations = 0

    for left, right in itertools.combinations(archive, 2):
        lkey, rkey = factor_key(left["edges"]), factor_key(right["edges"])
        d = factor_distance(lkey, rkey)
        if d < 2 or d > args.distance_max:
            continue
        common = set(lkey) & set(rkey)
        difference = sorted((set(lkey) | set(rkey)) - common)
        local_factors = 0
        local_safe = 0
        for chosen in itertools.combinations(difference, d):
            total_combinations += 1
            edges = tuple(sorted((*common, *chosen)))
            if not valid_factor(edges):
                continue
            local_factors += 1
            if edges in archive_keys or not is_diagonal_safe(edges):
                continue
            local_safe += 1
            if edges not in candidates:
                candidates[edges] = {
                    "parents": [[left["id"], right["id"]]],
                    "parent_values": [left["value"], right["value"]],
                    "parent_distance": d,
                    "edges": [list(edge) for edge in edges],
                    "hints": [
                        projected_hint(left, right, edges),
                        projected_hint(right, left, edges),
                    ],
                }
            else:
                candidates[edges]["parents"].append([left["id"], right["id"]])
        pair_stats.append(
            {
                "left": left["id"],
                "right": right["id"],
                "distance": d,
                "union_2factors": local_factors,
                "new_safe_factors": local_safe,
            }
        )
        if len(candidates) >= args.candidate_cap:
            break

    pool = list(candidates.values())[: args.candidate_cap]
    print(
        f"archive={len(archive)} pairs={len(pair_stats)} combinations={total_combinations} "
        f"unique_safe_crossovers={len(pool)}",
        flush=True,
    )
    results = []
    jobs = [(index, item, args.restarts) for index, item in enumerate(pool)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(evaluate, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            if len(results) % 20 == 0:
                print(
                    f"  evaluated={len(results)}/{len(jobs)} "
                    f"best={min(item['bad_triples'] for item in results)}",
                    flush=True,
                )
    results.sort(key=lambda item: (item["bad_triples"], item["parent_distance"]))
    exact_pool = [item for item in results if item["bad_triples"] <= 40]
    if not exact_pool:
        exact_pool = results[: args.exact_top]
    else:
        exact_pool = exact_pool[: args.exact_top]
    exact = []
    for rank, item in enumerate(exact_pool, 1):
        solve = exact_weighted(item, args.exact_time)
        exact.append({"rank": rank, "candidate": item, "solve": solve})
        print(
            f"exact {rank}: warm={item['bad_triples']} "
            f"{solve.get('status')} {solve.get('violations')}",
            flush=True,
        )
    payload = {
        "parameters": vars(args),
        "archive_count": len(archive),
        "pair_count": len(pair_stats),
        "total_combinations": total_combinations,
        "unique_safe_crossovers": len(pool),
        "pair_stats": pair_stats,
        "value_histogram": dict(sorted(Counter(item["bad_triples"] for item in results).items())),
        "top100": results[:100],
        "exact": exact,
    }
    path = OUT / args.out
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(path, flush=True)


if __name__ == "__main__":
    main()
