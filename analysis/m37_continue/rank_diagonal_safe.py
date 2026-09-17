"""Rank every diagonal-safe one-switch factor by true weighted geometry descent."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
from pathlib import Path

from joint_plateau_lns import local_descent
from signed_nae_core import geometry_bad_count
from weighted_factor_search import build_state, exact_weighted


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def evaluate(payload):
    index, item, restarts = payload
    edges = [tuple(e) for e in item["edges"]]
    _, _, _, constant, jmat = build_state(edges)
    rng = random.Random(202607172000 + index)
    best_v, best_bits = local_descent(constant, jmat, item["bits"], rng, 5)
    for _ in range(restarts):
        bits = [rng.getrandbits(1) for _ in edges]
        bits[0] = 0
        value, candidate = local_descent(constant, jmat, bits, rng, 4)
        if value < best_v:
            best_v, best_bits = value, candidate
    geometry = geometry_bad_count(37, edges, best_bits)
    assert best_v == geometry["bad_triples"]
    return {
        **item,
        "heuristic_bad_triples": best_v,
        "heuristic_bits": best_bits,
        "heuristic_geometry": geometry,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--restarts", type=int, default=12)
    parser.add_argument("--exact-top", type=int, default=4)
    parser.add_argument("--exact-time", type=float, default=60.0)
    parser.add_argument("--out", default="ranked_diagonal_safe.json")
    args = parser.parse_args()

    source = json.loads(
        (OUT / "diagonal_factor_search.json").read_text(encoding="utf-8")
    )
    safe = source["safe_top50"]
    jobs = [(index, item, args.restarts) for index, item in enumerate(safe)]
    ranked = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in concurrent.futures.as_completed(
            [pool.submit(evaluate, job) for job in jobs]
        ):
            ranked.append(result.result())
            print(
                f"ranked {len(ranked)}/{len(jobs)} current_best="
                f"{min(x['heuristic_bad_triples'] for x in ranked)}",
                flush=True,
            )
    ranked.sort(key=lambda x: x["heuristic_bad_triples"])
    exact = []
    for rank, item in enumerate(ranked[: args.exact_top], 1):
        candidate = {**item, "bits": item["heuristic_bits"]}
        solved = exact_weighted(candidate, args.exact_time)
        exact.append({"rank": rank, "candidate": candidate, "solve": solved})
        print(
            f"exact {rank}: heuristic={item['heuristic_bad_triples']} "
            f"status={solved.get('status')} value={solved.get('violations')}",
            flush=True,
        )
    payload = {
        "parameters": vars(args),
        "safe_factor_count": len(ranked),
        "best_heuristic_bad_triples": ranked[0]["heuristic_bad_triples"],
        "ranked": ranked,
        "exact": exact,
    }
    (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(OUT / args.out)


if __name__ == "__main__":
    main()
