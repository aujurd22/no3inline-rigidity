"""Incrementally score all 706 diagonal-safe six-edge buffered repairs."""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import random
from pathlib import Path

from joint_plateau_lns import local_descent
from signed_nae_core import c4_lifts, geometry_bad_count
from weighted_factor_search import (
    apply_pair,
    apply_triple,
    build_state,
    exact_weighted,
    pair_vector,
    triple_vector,
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
G = {}


def init_worker(base_edges, base_bits, pair_map, triple_map, constant, jmat, restarts):
    G.update(
        base_edges=[tuple(edge) for edge in base_edges],
        base_bits=base_bits,
        pair_map={tuple(map(int, key.split(","))): value for key, value in pair_map.items()},
        triple_map={
            tuple(map(int, key.split(","))): value for key, value in triple_map.items()
        },
        constant=constant,
        jmat=jmat,
        restarts=restarts,
    )


def evaluate(payload):
    index, item = payload
    edges = [tuple(edge) for edge in item["edges"]]
    lifts = [(c4_lifts(37, edge), c4_lifts(37, edge[::-1])) for edge in edges]
    changed = set(item["selected_indices"])
    constant = G["constant"]
    jmat = [row[:] for row in G["jmat"]]
    for i, j in itertools.combinations(range(37), 2):
        if changed.isdisjoint((i, j)):
            continue
        constant = apply_pair(constant, jmat, i, j, G["pair_map"][(i, j)], -1)
        constant = apply_pair(constant, jmat, i, j, pair_vector(lifts, i, j), 1)
    for triple in itertools.combinations(range(37), 3):
        if changed.isdisjoint(triple):
            continue
        constant = apply_triple(
            constant, jmat, triple, G["triple_map"][triple], -1
        )
        constant = apply_triple(
            constant, jmat, triple, triple_vector(lifts, *triple), 1
        )

    rng = random.Random(202607178000 + index)
    best, bits = local_descent(constant, jmat, G["base_bits"], rng, 5)
    for _ in range(G["restarts"]):
        start = [rng.getrandbits(1) for _ in range(37)]
        start[0] = 0
        value, candidate_bits = local_descent(constant, jmat, start, rng, 4)
        if value < best:
            best, bits = value, candidate_bits
    geometry = geometry_bad_count(37, edges, bits)
    assert best == geometry["bad_triples"]
    return {**item, "bad_triples": best, "bits": bits, "geometry": geometry}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--restarts", type=int, default=2)
    parser.add_argument("--exact-top", type=int, default=3)
    parser.add_argument("--exact-time", type=float, default=60.0)
    parser.add_argument("--out", default="buffered_all_weighted.json")
    args = parser.parse_args()

    candidates_source = json.loads(
        (OUT / "buffered_hitting_candidates.json").read_text(encoding="utf-8")
    )
    candidates = candidates_source["all_safe_candidates"]
    records = json.loads(
        (OUT / "weighted_breakthrough_verified.json").read_text(encoding="utf-8")
    )
    base = next(item for item in records if item["name"] == "m37_weighted_48")
    base_edges = [tuple(edge) for edge in base["edges"]]
    base_bits = base["weighted_repeat_exact"]["bits"]
    _, pair_map, triple_map, constant, jmat = build_state(base_edges)
    packed_pairs = {",".join(map(str, key)): value for key, value in pair_map.items()}
    packed_triples = {
        ",".join(map(str, key)): value for key, value in triple_map.items()
    }

    results = []
    jobs = list(enumerate(candidates))
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=args.workers,
        initializer=init_worker,
        initargs=(
            base_edges,
            base_bits,
            packed_pairs,
            packed_triples,
            constant,
            jmat,
            args.restarts,
        ),
    ) as pool:
        for result in pool.map(evaluate, jobs, chunksize=1):
            results.append(result)
            if len(results) % 50 == 0:
                print(
                    f"evaluated {len(results)}/{len(jobs)} "
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
        "evaluated": len(results),
        "best_feasible": results[0]["bad_triples"],
        "value_histogram": {
            str(value): sum(item["bad_triples"] == value for item in results)
            for value in sorted({item["bad_triples"] for item in results})
        },
        "top100": results[:100],
        "exact": exact,
    }
    (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(OUT / args.out)


if __name__ == "__main__":
    main()
