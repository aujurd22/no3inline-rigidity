"""Exhaust every legal 2-switch around all independently verified V=14 factors."""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import random
import time
from pathlib import Path

from joint_plateau_lns import local_descent
from signed_nae_core import (
    build_ising,
    c4_lifts,
    enumerate_clauses,
    geometry_bad_count,
    has_collinear_triple,
    solve_clause_cp_sat,
)
from spectral_neighbor_search import add_mask, generate_switches, masks_from_clauses


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
G = {}


def triple_mask(lifts, triple):
    a, b, c = triple
    mask = 0
    for bits in range(8):
        points = (
            lifts[a][(bits >> 0) & 1]
            + lifts[b][(bits >> 1) & 1]
            + lifts[c][(bits >> 2) & 1]
        )
        if has_collinear_triple(points):
            mask |= 1 << bits
    return mask


def init_worker(m, edges, warm_bits, masks, jmat, pairs, clause_count, restarts):
    G.update(
        m=m,
        edges=[tuple(e) for e in edges],
        warm_bits=warm_bits,
        masks={tuple(map(int, key.split(","))): value for key, value in masks.items()},
        jmat=jmat,
        pairs=pairs,
        clause_count=clause_count,
        restarts=restarts,
    )


def evaluate(spec):
    move_no, i, j, e1, e2 = spec
    edges = G["edges"][:]
    edges[i], edges[j] = tuple(e1), tuple(e2)
    lifts = [
        (c4_lifts(G["m"], (u, v)), c4_lifts(G["m"], (v, u))) for u, v in edges
    ]
    jmat = [row[:] for row in G["jmat"]]
    pairs = G["pairs"]
    clause_count = G["clause_count"]
    changed = {i, j}
    for triple in itertools.combinations(range(len(edges)), 3):
        if changed.isdisjoint(triple):
            continue
        old = G["masks"].get(triple, 0)
        new = triple_mask(lifts, triple)
        if old == new:
            continue
        pairs += add_mask(jmat, triple, old, -1)
        pairs += add_mask(jmat, triple, new, +1)
        clause_count += new.bit_count() - old.bit_count()

    rng = random.Random(202607170000 + move_no)
    value, bits = local_descent(pairs, jmat, G["warm_bits"], rng, 4)
    for _ in range(G["restarts"]):
        random_bits = [rng.getrandbits(1) for _ in edges]
        random_bits[0] = 0
        candidate_v, candidate_bits = local_descent(pairs, jmat, random_bits, rng, 3)
        if candidate_v < value:
            value, bits = candidate_v, candidate_bits
    return {
        "switch_indices": [i, j],
        "new_edges": [list(e1), list(e2)],
        "edges": [list(e) for e in edges],
        "clauses": clause_count,
        "violations": value,
        "bits": bits,
    }


def exact_check(item, time_limit):
    edges = [tuple(e) for e in item["edges"]]
    clauses = enumerate_clauses(37, edges)
    solved = solve_clause_cp_sat(clauses, 37, time_limit)
    if solved.get("bits") is not None:
        solved["geometry"] = geometry_bad_count(37, edges, solved["bits"])
    return solved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--restarts", type=int, default=2)
    parser.add_argument("--exact-top", type=int, default=6)
    parser.add_argument("--exact-time", type=float, default=60.0)
    parser.add_argument("--out", default="exhaustive_v14_neighbors.json")
    args = parser.parse_args()

    bases = json.loads(
        (OUT / "joint_breakthrough_verified.json").read_text(encoding="utf-8")
    )
    payload = {"parameters": vars(args), "bases": []}
    total_start = time.time()
    for base_index, base in enumerate(bases, 1):
        print(f"base {base_index}/{len(bases)}: {base['name']}", flush=True)
        edges = [tuple(e) for e in base["edges"]]
        clauses = enumerate_clauses(37, edges)
        masks = masks_from_clauses(clauses)
        pair_list, jmat, missing = build_ising(37, clauses)
        assert not missing
        switches = generate_switches(edges)
        packed = {",".join(map(str, key)): value for key, value in masks.items()}
        specs = [(k, *move) for k, move in enumerate(switches)]
        results = []
        start = time.time()
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=args.workers,
            initializer=init_worker,
            initargs=(
                37,
                edges,
                base["bits"],
                packed,
                jmat,
                len(pair_list),
                len(clauses),
                args.restarts,
            ),
        ) as pool:
            for index, result in enumerate(pool.map(evaluate, specs, chunksize=1), 1):
                results.append(result)
                if index % 200 == 0:
                    print(
                        f"  {index}/{len(specs)} bestV={min(x['violations'] for x in results)}",
                        flush=True,
                    )
        results.sort(key=lambda x: (x["violations"], x["clauses"]))
        exact_pool = [x for x in results if x["violations"] < 14]
        if not exact_pool:
            exact_pool = results[: args.exact_top]
        exact = []
        for rank, item in enumerate(exact_pool, 1):
            solved = exact_check(item, args.exact_time)
            exact.append({"rank": rank, "candidate": item, "solve": solved})
            print(
                f"  exact {rank}: feasible={item['violations']} clauses={item['clauses']} "
                f"-> {solved.get('status')} {solved.get('violations')}",
                flush=True,
            )
        payload["bases"].append(
            {
                "name": base["name"],
                "base_clauses": base["clauses"],
                "legal_switches": len(specs),
                "elapsed_s": round(time.time() - start, 3),
                "best_feasible_violations": results[0]["violations"],
                "top50": results[:50],
                "exact": exact,
            }
        )
        payload["elapsed_s"] = round(time.time() - total_start, 3)
        (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(OUT / args.out)


if __name__ == "__main__":
    main()
