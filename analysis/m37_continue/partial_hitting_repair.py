"""Exhaust maximum-coverage independent repairs with 2, 3, or 4 factor edges."""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import random
from collections import Counter
from pathlib import Path

from defect_hitting_analysis import defect_owner_sets, max_coverage
from exhaustive_hitting_repair import perfect_matchings
from joint_plateau_lns import local_descent
from signed_nae_core import geometry_bad_count, validate_factor
from weighted_factor_search import build_state, exact_weighted, is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def independent(edges, indices):
    vertices = [vertex for index in indices for vertex in edges[index]]
    return len(vertices) == len(set(vertices))


def coverage(defects, indices):
    selected = set(indices)
    return sum(bool(selected & defect) for defect in defects)


def evaluate(payload):
    index, item, restarts = payload
    edges = [tuple(edge) for edge in item["edges"]]
    _, _, _, constant, jmat = build_state(edges)
    rng = random.Random(202607179000 + index)
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
    parser.add_argument("--restarts", type=int, default=4)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=4)
    parser.add_argument("--exact-time", type=float, default=90.0)
    parser.add_argument("--coverage-slack", type=int, default=0)
    parser.add_argument(
        "--base",
        default="48",
        help="48, 40, or an id such as v40_01 from exact_factor_archive.json",
    )
    parser.add_argument("--out", default="partial_hitting_repair.json")
    args = parser.parse_args()

    if args.base == "48":
        records = json.loads(
            (OUT / "weighted_breakthrough_verified.json").read_text(encoding="utf-8")
        )
        base = next(item for item in records if item["name"] == "m37_weighted_48")
        hitting = json.loads(
            (OUT / "defect_hitting_results.json").read_text(encoding="utf-8")
        )
        known_best = 48
    elif args.base == "40":
        base = json.loads((OUT / "weighted_40_verified.json").read_text(encoding="utf-8"))
        hitting = json.loads((OUT / "defect_hitting_40.json").read_text(encoding="utf-8"))
        known_best = 40
    else:
        archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
        chosen = next((item for item in archive["archive"] if item["id"] == args.base), None)
        if chosen is None:
            raise ValueError(f"unknown archive factor id: {args.base}")
        base = {"edges": chosen["edges"], "weighted_repeat_exact": {"bits": chosen["bits"]}}
        known_best = chosen["value"]
        hitting = None
    edges = [tuple(edge) for edge in base["edges"]]
    bits = base["weighted_repeat_exact"]["bits"]
    if hitting is None:
        defects = [set(item) for item in defect_owner_sets(edges, bits)]
    else:
        defects = [set(item) for item in hitting["defect_owner_sets"]]
    if hitting is None:
        maximum = {
            budget: max_coverage(edges, defects, True, budget)["covered"]
            for budget in (2, 3, 4)
        }
    else:
        maximum = {
            item["budget"]: item["covered"]
            for item in hitting["coverage_frontier"]
            if item["independent"] and item["budget"] in (2, 3, 4)
        }

    candidates = {}
    selected_sets = []
    total_matchings = 0
    safe_matchings = 0
    for budget in (2, 3, 4):
        for indices in itertools.combinations(range(37), budget):
            if not independent(edges, indices):
                continue
            covered = coverage(defects, indices)
            if covered < maximum[budget] - args.coverage_slack:
                continue
            selected_sets.append({"indices": list(indices), "covered": covered})
            untouched = set(edges[index] for index in range(37) if index not in indices)
            endpoints = [vertex for index in indices for vertex in edges[index]]
            for matching in perfect_matchings(endpoints):
                total_matchings += 1
                new_edges = sorted(tuple(sorted(edge)) for edge in matching)
                if len(set(new_edges)) != budget or any(
                    edge in untouched for edge in new_edges
                ):
                    continue
                candidate = edges[:]
                for index, edge in zip(indices, new_edges):
                    candidate[index] = edge
                key = tuple(sorted(candidate))
                if key == tuple(sorted(edges)) or not is_diagonal_safe(candidate):
                    continue
                assert validate_factor(37, candidate)["is_2factor"]
                safe_matchings += 1
                if key not in candidates:
                    warm = geometry_bad_count(37, candidate, bits)["bad_triples"]
                    candidates[key] = {
                        "selected_indices": list(indices),
                        "covered_old_defects": covered,
                        "new_edges": [list(edge) for edge in new_edges],
                        "edges": [list(edge) for edge in candidate],
                        "bits": bits,
                        "warm_bad_triples": warm,
                    }

    ranked = sorted(candidates.values(), key=lambda item: item["warm_bad_triples"])
    evaluate_pool = ranked[: args.evaluate_top]
    print(
        f"selected_sets={len(selected_sets)} matchings={total_matchings} "
        f"safe={safe_matchings} unique={len(ranked)} evaluating={len(evaluate_pool)}",
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
    improvements = [item for item in results if item["bad_triples"] < known_best]
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
        "known_best": known_best,
        "defect_owner_sets": [sorted(item) for item in defects],
        "maximum_coverage": maximum,
        "selected_set_histogram": dict(Counter(len(item["indices"]) for item in selected_sets)),
        "selected_sets": selected_sets,
        "total_matchings": total_matchings,
        "safe_matchings": safe_matchings,
        "unique_safe_factors": len(ranked),
        "warm_top100": ranked[:100],
        "evaluated": len(results),
        "value_histogram": dict(Counter(item["bad_triples"] for item in results)),
        "weighted_top100": results[:100],
        "best_feasible": results[0]["bad_triples"] if results else None,
        "exact": exact,
    }
    (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(OUT / args.out)


if __name__ == "__main__":
    main()
