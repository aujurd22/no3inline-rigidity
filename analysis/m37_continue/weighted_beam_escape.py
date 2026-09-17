"""Diverse multi-start beam search on the diagonal-safe 2-factor graph."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from weighted_factor_search import exact_weighted, expand_base


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def factor_key(edges):
    return tuple(sorted(tuple(sorted(edge)) for edge in edges))


def factor_distance(left, right):
    return 37 - len(set(left) & set(right))


def choose_diverse(candidates, beam_size, low_keys, per_parent):
    candidates.sort(
        key=lambda x: (
            x["geometric_bad_triples"],
            -min(factor_distance(factor_key(x["edges"]), key) for key in low_keys),
            x["node_id"],
        )
    )
    chosen = []
    counts = defaultdict(int)

    # Guarantee that more than one basin can survive a layer when competitive.
    for item in candidates:
        if len(chosen) >= beam_size:
            break
        if counts[item["parent"]] >= per_parent:
            continue
        key = factor_key(item["edges"])
        if chosen and min(factor_distance(key, factor_key(x["edges"])) for x in chosen) < 2:
            continue
        chosen.append(item)
        counts[item["parent"]] += 1

    for item in candidates:
        if len(chosen) >= beam_size:
            break
        if item in chosen:
            continue
        key = factor_key(item["edges"])
        if chosen and min(factor_distance(key, factor_key(x["edges"])) for x in chosen) < 2:
            continue
        chosen.append(item)

    for item in candidates:
        if len(chosen) >= beam_size:
            break
        if item not in chosen:
            chosen.append(item)
    return chosen


def checkpoint(args, seeds, layers, elite, exact=None, elapsed=None):
    payload = {
        "parameters": vars(args),
        "seed_count": len(seeds),
        "seed_histogram": dict(sorted(Counter(x["geometric_bad_triples"] for x in seeds).items())),
        "layers": layers,
        "global_elite": elite[:100],
        "exact": exact or [],
        "elapsed_s": elapsed,
    }
    (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--beam-size", type=int, default=24)
    parser.add_argument("--per-parent", type=int, default=2)
    parser.add_argument("--restarts", type=int, default=3)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=20)
    parser.add_argument("--exact-time", type=float, default=60.0)
    parser.add_argument("--seed-max", type=int, default=48)
    parser.add_argument("--out", default="weighted_beam_escape.json")
    args = parser.parse_args()

    archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    seeds = []
    for item in archive["archive"]:
        if item["value"] <= args.seed_max and item["diagonal_safe"]:
            seeds.append(
                {
                    "node_id": item["id"],
                    "parent": None,
                    "depth": 0,
                    "edges": item["edges"],
                    "bits": item["bits"],
                    "geometric_bad_triples": item["value"],
                }
            )
    assert seeds
    low_keys = [factor_key(x["edges"]) for x in seeds]
    visited = set(low_keys)
    beam = seeds
    elite_by_key = {factor_key(x["edges"]): x for x in seeds}
    layers = []
    next_id = 1
    started = time.time()

    print(
        f"seeds={len(seeds)} values={Counter(x['geometric_bad_triples'] for x in seeds)}",
        flush=True,
    )
    for depth in range(1, args.depth + 1):
        jobs = []
        for index, parent in enumerate(beam):
            jobs.append(
                (
                    parent["node_id"],
                    parent["edges"],
                    parent["bits"],
                    5000,
                    args.restarts,
                    202607171000 + depth * 1000 + index,
                    True,
                )
            )
        raw = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(expand_base, job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                raw.extend(result["results"])
                print(
                    f"  depth={depth} parent={result['parent']} "
                    f"safe_neighbors={len(result['results'])}",
                    flush=True,
                )

        unique = {}
        for item in raw:
            key = factor_key(item["edges"])
            if key in visited:
                continue
            previous = unique.get(key)
            if previous is None or item["geometric_bad_triples"] < previous["geometric_bad_triples"]:
                item["depth"] = depth
                item["node_id"] = f"b{depth}_{next_id:05d}"
                unique[key] = item
                next_id += 1
        candidates = list(unique.values())
        visited.update(unique)
        for key, item in unique.items():
            old = elite_by_key.get(key)
            if old is None or item["geometric_bad_triples"] < old["geometric_bad_triples"]:
                elite_by_key[key] = item

        histogram = Counter(x["geometric_bad_triples"] for x in candidates)
        beam = choose_diverse(candidates, args.beam_size, low_keys, args.per_parent)
        layer = {
            "depth": depth,
            "parents": len(jobs),
            "raw_safe_neighbors": len(raw),
            "new_unique_factors": len(candidates),
            "value_histogram": dict(sorted(histogram.items())),
            "best_value": min(histogram) if histogram else None,
            "beam": beam,
        }
        layers.append(layer)
        elite = sorted(
            elite_by_key.values(),
            key=lambda x: (x["geometric_bad_triples"], x.get("depth", 0), x["node_id"]),
        )
        checkpoint(args, seeds, layers, elite, elapsed=round(time.time() - started, 3))
        print(
            f"depth={depth} raw={len(raw)} new={len(candidates)} "
            f"best={layer['best_value']} beam={len(beam)} visited={len(visited)}",
            flush=True,
        )
        if not beam or layer["best_value"] is not None and layer["best_value"] <= 36:
            break

    elite = sorted(
        elite_by_key.values(),
        key=lambda x: (x["geometric_bad_triples"], x.get("depth", 0), x["node_id"]),
    )
    exact_pool = []
    seen = set()
    for item in elite:
        key = factor_key(item["edges"])
        if key in low_keys or key in seen:
            continue
        seen.add(key)
        exact_pool.append(item)
        if len(exact_pool) >= args.exact_top:
            break

    exact = []
    for rank, item in enumerate(exact_pool, 1):
        solve = exact_weighted(item, args.exact_time)
        exact.append({"rank": rank, "candidate": item, "solve": solve})
        print(
            f"exact {rank}: warm={item['geometric_bad_triples']} "
            f"{solve.get('status')} {solve.get('violations')}",
            flush=True,
        )
    checkpoint(
        args,
        seeds,
        layers,
        elite,
        exact=exact,
        elapsed=round(time.time() - started, 3),
    )
    print(OUT / args.out, flush=True)


if __name__ == "__main__":
    main()
