#!/usr/bin/env python3
"""Scan the complete legal one-2-switch neighbourhood of an m=37 factor."""

from __future__ import annotations

import argparse
import json
import pickle
import random
import time
from pathlib import Path

import numpy as np

from weighted_prefilter_ab_m37 import (
    exact_orientation_sa, pair_tables, quadratic_local_min, summarize,
)


M = 37


def all_one_switches(seed_edges):
    seed = tuple(sorted(seed_edges))
    seen = set()
    for i in range(len(seed)):
        a, b = seed[i]
        for j in range(i + 1, len(seed)):
            c, d = seed[j]
            if len({a, b, c, d}) < 4:
                continue
            rest = set(seed)
            rest.remove(seed[i]); rest.remove(seed[j])
            for e1, e2 in (((a, c), (b, d)), ((a, d), (b, c))):
                e1, e2 = tuple(sorted(e1)), tuple(sorted(e2))
                if e1 == e2 or e1 in rest or e2 in rest:
                    continue
                candidate = tuple(sorted((*rest, e1, e2)))
                if candidate != seed and candidate not in seen:
                    seen.add(candidate)
                    yield candidate, [list(seed[i]), list(seed[j])], [list(e1), list(e2)]


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--evaluate", type=int, default=30)
    ap.add_argument("--score-restarts", type=int, default=4)
    ap.add_argument("--exact-restarts", type=int, default=4)
    ap.add_argument("--exact-moves", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=20260722)
    ap.add_argument(
        "--seed-input", type=Path,
        help="JSON containing an 'edges' field; defaults to the historical best72",
    )
    ap.add_argument("--out", type=Path, default=here / "results" /
                    "pair_codegree_37" / "one_switch_landscape_m37.json")
    args = ap.parse_args()
    began = time.time()
    raw_matrix = np.load(here / "co3_m37.npy", mmap_mode="r")
    weighted_matrix = np.load(here / "weighted_co3_m37.npy", mmap_mode="r")
    direct_bad = np.load(here / "direct_bad_m37.npy", mmap_mode="r")
    with (here / "line_cons_m37.pkl").open("rb") as f:
        constraints, incidence = pickle.load(f)
    seed_path = args.seed_input or (here / "results" /
                                    "swarm_D1_2_best72_clauses.json")
    clause_data = json.loads(seed_path.read_text(encoding="utf-8"))
    seed_edges = tuple(sorted(tuple(e) for e in clause_data["edges"]))

    pool = []
    for number, (edges, removed, added) in enumerate(all_one_switches(seed_edges), 1):
        raw, weighted, bad = pair_tables(edges, raw_matrix, weighted_matrix, direct_bad)
        score_seed = args.seed + sum((i + 1) * (u * M + v + 1)
                                     for i, (u, v) in enumerate(edges))
        raw_score, raw_bits, raw_direct = quadratic_local_min(
            raw, bad, np.random.default_rng(score_seed), args.score_restarts)
        weighted_score, weighted_bits, weighted_direct = quadratic_local_min(
            weighted, bad, np.random.default_rng(score_seed), args.score_restarts)
        pool.append({
            "edges": [list(e) for e in edges], "removed": removed, "added": added,
            "raw_score": raw_score, "weighted_score": weighted_score,
            "raw_direct_bad": raw_direct, "weighted_direct_bad": weighted_direct,
            "raw_bits": raw_bits.tolist(), "weighted_bits": weighted_bits.tolist(),
        })
        if number % 250 == 0:
            print(f"  scored {number} one-switch neighbours", flush=True)

    raw_eligible = [r for r in pool if r["raw_direct_bad"] == 0]
    weighted_eligible = [r for r in pool if r["weighted_direct_bad"] == 0]
    raw_pick = sorted(raw_eligible, key=lambda r: r["raw_score"])[:args.evaluate]
    weighted_pick = sorted(weighted_eligible, key=lambda r: r["weighted_score"])[:args.evaluate]
    rng = random.Random(args.seed)
    random_pick = rng.sample(pool, min(args.evaluate, len(pool)))
    groups = {"random": random_pick, "raw": raw_pick, "weighted": weighted_pick}
    cache = {}
    for group, rows in groups.items():
        print(f"  exact {group} ({len(rows)})", flush=True)
        for row in rows:
            key = tuple(map(tuple, row["edges"]))
            if key not in cache:
                exact_seed = args.seed + sum((i + 1) * (u * M + v + 1)
                                              for i, (u, v) in enumerate(key))
                cache[key] = exact_orientation_sa(
                    key, constraints, incidence, exact_seed,
                    args.exact_restarts, args.exact_moves)
            row["exact"] = cache[key]
    union = list({tuple(map(tuple, r["edges"])): r
                  for rows in groups.values() for r in rows}.values())
    y = np.asarray([r["exact"]["best_geometric_bad"] for r in union], dtype=float)
    correlations = {
        "evaluated_unique": len(union),
        "raw": float(np.corrcoef([r["raw_score"] for r in union], y)[0, 1]),
        "weighted": float(np.corrcoef([r["weighted_score"] for r in union], y)[0, 1]),
    }
    exact_best = min(union, key=lambda r: r["exact"]["best_geometric_bad"])
    payload = {
        "definition": "complete legal one-2-switch neighbourhood of one m=37 factor",
        "seed_input": str(seed_path),
        "seed_edges": [list(e) for e in seed_edges],
        "parameters": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
        "pool_size": len(pool), "raw_direct_free": len(raw_eligible),
        "weighted_direct_free": len(weighted_eligible),
        "summaries": {name: summarize(rows) for name, rows in groups.items()},
        "correlations": correlations,
        "best_evaluated": exact_best,
        "groups": groups,
        "pool_scores": [{k: r[k] for k in
                         ("edges", "removed", "added", "raw_score", "weighted_score",
                          "raw_direct_bad", "weighted_direct_bad")} for r in pool],
        "seconds": time.time() - began,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"pool_size": len(pool), "summaries": payload["summaries"],
                      "correlations": correlations,
                      "best": {"bad": exact_best["exact"]["best_geometric_bad"],
                               "removed": exact_best["removed"],
                               "added": exact_best["added"]},
                      "seconds": payload["seconds"]}, indent=2))


if __name__ == "__main__":
    main()
