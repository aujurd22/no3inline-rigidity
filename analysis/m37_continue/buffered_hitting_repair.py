"""Add one independent buffer edge to every minimum defect hitting set."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
from pathlib import Path

from exhaustive_hitting_repair import perfect_matchings
from joint_plateau_lns import local_descent
from signed_nae_core import geometry_bad_count, validate_factor
from weighted_factor_search import build_state, exact_weighted, is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def independent(edges, indices):
    vertices = [vertex for index in indices for vertex in edges[index]]
    return len(vertices) == len(set(vertices))


def evaluate(payload):
    index, item, restarts = payload
    edges = [tuple(edge) for edge in item["edges"]]
    _, _, _, constant, jmat = build_state(edges)
    rng = random.Random(202607177000 + index)
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
    parser.add_argument("--evaluate-top", type=int, default=120)
    parser.add_argument("--restarts", type=int, default=4)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=3)
    parser.add_argument("--exact-time", type=float, default=45.0)
    parser.add_argument("--out", default="buffered_hitting_repair.json")
    args = parser.parse_args()

    records = json.loads(
        (OUT / "weighted_breakthrough_verified.json").read_text(encoding="utf-8")
    )
    base = next(item for item in records if item["name"] == "m37_weighted_48")
    prior = json.loads((OUT / "all_hitting_repair.json").read_text(encoding="utf-8"))
    edges = [tuple(edge) for edge in base["edges"]]
    bits = base["weighted_repeat_exact"]["bits"]
    minimum_sets = [tuple(item["indices"]) for item in prior["per_hitting_set"]]

    buffered_sets = set()
    for hitting in minimum_sets:
        for buffer_index in range(37):
            selected = tuple(sorted((*hitting, buffer_index)))
            if len(set(selected)) == 6 and independent(edges, selected):
                buffered_sets.add(selected)
    print(f"buffered independent sets={len(buffered_sets)}", flush=True)

    candidates = {}
    total_matchings = 0
    safe_matchings = 0
    per_set = []
    for set_no, selected in enumerate(sorted(buffered_sets), 1):
        untouched = set(edges[index] for index in range(37) if index not in selected)
        endpoints = [vertex for index in selected for vertex in edges[index]]
        local_safe = 0
        for matching in perfect_matchings(endpoints):
            total_matchings += 1
            new_edges = sorted(tuple(sorted(edge)) for edge in matching)
            if len(set(new_edges)) != 6 or any(edge in untouched for edge in new_edges):
                continue
            candidate = edges[:]
            for index, edge in zip(selected, new_edges):
                candidate[index] = edge
            key = tuple(sorted(candidate))
            if key == tuple(sorted(edges)) or not is_diagonal_safe(candidate):
                continue
            assert validate_factor(37, candidate)["is_2factor"]
            safe_matchings += 1
            local_safe += 1
            if key not in candidates:
                warm = geometry_bad_count(37, candidate, bits)["bad_triples"]
                candidates[key] = {
                    "selected_indices": list(selected),
                    "new_edges": [list(edge) for edge in new_edges],
                    "edges": [list(edge) for edge in candidate],
                    "bits": bits,
                    "warm_bad_triples": warm,
                }
        per_set.append({"indices": list(selected), "safe_matchings": local_safe})
        if set_no % 10 == 0:
            print(
                f"  sets {set_no}/{len(buffered_sets)} unique_safe={len(candidates)}",
                flush=True,
            )

    ranked = sorted(candidates.values(), key=lambda item: item["warm_bad_triples"])
    evaluate_pool = ranked[: args.evaluate_top]
    print(
        f"matchings={total_matchings} safe={safe_matchings} "
        f"unique_safe={len(ranked)} evaluating={len(evaluate_pool)}",
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
    payload = {
        "parameters": vars(args),
        "buffered_independent_set_count": len(buffered_sets),
        "total_matchings": total_matchings,
        "safe_matchings": safe_matchings,
        "unique_safe_factors": len(ranked),
        "per_set": per_set,
        "all_safe_candidates": ranked,
        "warm_top50": ranked[:50],
        "evaluated": len(results),
        "weighted_top50": results[:50],
        "best_feasible": results[0]["bad_triples"] if results else None,
        "exact": [],
    }
    (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    exact = []
    for rank, item in enumerate(exact_pool, 1):
        solved = exact_weighted(item, args.exact_time)
        exact.append({"rank": rank, "candidate": item, "solve": solved})
        payload["exact"] = exact
        (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            f"exact {rank}: feasible={item['bad_triples']} "
            f"status={solved.get('status')} value={solved.get('violations')}",
            flush=True,
        )
    print(OUT / args.out)


if __name__ == "__main__":
    main()
