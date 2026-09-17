"""Exhaust all endpoint pairings of the minimum independent defect hitting set."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
from pathlib import Path

from joint_plateau_lns import local_descent
from signed_nae_core import geometry_bad_count, validate_factor
from weighted_factor_search import build_state, exact_weighted, is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def perfect_matchings(vertices):
    if not vertices:
        yield []
        return
    first = vertices[0]
    for index in range(1, len(vertices)):
        second = vertices[index]
        rest = vertices[1:index] + vertices[index + 1 :]
        for matching in perfect_matchings(rest):
            yield [(first, second), *matching]


def evaluate(payload):
    index, item, restarts = payload
    edges = [tuple(edge) for edge in item["edges"]]
    _, _, _, constant, jmat = build_state(edges)
    rng = random.Random(202607175000 + index)
    best, bits = local_descent(constant, jmat, item["bits"], rng, 5)
    for _ in range(restarts):
        start = [rng.getrandbits(1) for _ in edges]
        start[0] = 0
        value, candidate_bits = local_descent(constant, jmat, start, rng, 4)
        if value < best:
            best, bits = value, candidate_bits
    geometry = geometry_bad_count(37, edges, bits)
    assert best == geometry["bad_triples"]
    return {**item, "bad_triples": best, "bits": bits, "geometry": geometry}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluate-top", type=int, default=160)
    parser.add_argument("--restarts", type=int, default=5)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=4)
    parser.add_argument("--exact-time", type=float, default=120.0)
    parser.add_argument("--out", default="exhaustive_hitting_repair.json")
    args = parser.parse_args()

    best_records = json.loads(
        (OUT / "weighted_breakthrough_verified.json").read_text(encoding="utf-8")
    )
    base = next(item for item in best_records if item["name"] == "m37_weighted_48")
    hitting = json.loads(
        (OUT / "defect_hitting_results.json").read_text(encoding="utf-8")
    )["minimum_independent_hitting_set"]
    selected = hitting["indices"]
    edges = [tuple(edge) for edge in base["edges"]]
    bits = base["weighted_repeat_exact"]["bits"]
    untouched = set(edges[index] for index in range(len(edges)) if index not in selected)
    endpoints = [vertex for index in selected for vertex in edges[index]]
    assert len(endpoints) == len(set(endpoints)) == 10

    candidates = []
    seen = set()
    total_matchings = 0
    for raw_matching in perfect_matchings(endpoints):
        total_matchings += 1
        new_edges = sorted(tuple(sorted(edge)) for edge in raw_matching)
        if len(set(new_edges)) != len(new_edges):
            continue
        if any(edge in untouched for edge in new_edges):
            continue
        candidate = edges[:]
        for index, edge in zip(sorted(selected), new_edges):
            candidate[index] = edge
        key = tuple(sorted(candidate))
        if key in seen or key == tuple(sorted(edges)):
            continue
        seen.add(key)
        if not validate_factor(37, candidate)["is_2factor"]:
            continue
        if not is_diagonal_safe(candidate):
            continue
        warm_geometry = geometry_bad_count(37, candidate, bits)
        candidates.append(
            {
                "selected_indices": selected,
                "new_edges": [list(edge) for edge in new_edges],
                "edges": [list(edge) for edge in candidate],
                "bits": bits,
                "warm_bad_triples": warm_geometry["bad_triples"],
            }
        )
    candidates.sort(key=lambda item: item["warm_bad_triples"])
    evaluate_pool = candidates[: args.evaluate_top]
    print(
        f"matchings={total_matchings} safe={len(candidates)} "
        f"evaluating={len(evaluate_pool)} warm_best="
        f"{candidates[0]['warm_bad_triples'] if candidates else None}",
        flush=True,
    )
    results = []
    jobs = [(index, item, args.restarts) for index, item in enumerate(evaluate_pool)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(evaluate, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            if len(results) % 20 == 0:
                print(
                    f"  evaluated {len(results)}/{len(jobs)} "
                    f"best={min(x['bad_triples'] for x in results)}",
                    flush=True,
                )
    results.sort(key=lambda item: item["bad_triples"])
    improvements = [item for item in results if item["bad_triples"] < 48]
    exact_pool = (improvements or results)[: args.exact_top]
    exact = []
    for rank, item in enumerate(exact_pool, 1):
        solved = exact_weighted(item, args.exact_time)
        exact.append({"rank": rank, "candidate": item, "solve": solved})
        print(
            f"exact {rank}: feasible={item['bad_triples']} "
            f"status={solved.get('status')} value={solved.get('violations')}",
            flush=True,
        )
    payload = {
        "parameters": vars(args),
        "selected_indices": selected,
        "selected_original_edges": [list(edges[index]) for index in selected],
        "total_matchings": total_matchings,
        "diagonal_safe_matchings": len(candidates),
        "evaluated": len(results),
        "warm_top50": candidates[:50],
        "weighted_top50": results[:50],
        "best_feasible": results[0]["bad_triples"] if results else None,
        "exact": exact,
    }
    (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(OUT / args.out)


if __name__ == "__main__":
    main()
