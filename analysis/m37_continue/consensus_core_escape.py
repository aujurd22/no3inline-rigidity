"""Beam search that explicitly escapes the 25-edge consensus core of V=40 basins."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from collections import Counter, defaultdict
from pathlib import Path

from weighted_factor_search import exact_weighted, expand_base


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def factor_key(edges):
    return tuple(sorted(tuple(sorted(edge)) for edge in edges))


def choose(candidates, beam_size, per_overlap):
    candidates.sort(key=lambda x: (x["geometric_bad_triples"], x["core_overlap"]))
    chosen = []
    chosen_keys = set()
    # Preserve a low-energy spine.
    for item in candidates[: max(8, beam_size // 3)]:
        key = factor_key(item["edges"])
        chosen.append(item)
        chosen_keys.add(key)
    # Preserve representatives at every achieved distance from the old core.
    groups = defaultdict(list)
    for item in candidates:
        groups[item["core_overlap"]].append(item)
    for overlap in sorted(groups):
        for item in groups[overlap][:per_overlap]:
            if len(chosen) >= beam_size:
                break
            key = factor_key(item["edges"])
            if key not in chosen_keys:
                chosen.append(item)
                chosen_keys.add(key)
        if len(chosen) >= beam_size:
            break
    # Fill remaining capacity by energy plus a strong novelty credit.
    remaining = sorted(
        candidates,
        key=lambda x: (x["geometric_bad_triples"] + 3 * x["core_overlap"], x["core_overlap"]),
    )
    for item in remaining:
        if len(chosen) >= beam_size:
            break
        key = factor_key(item["edges"])
        if key not in chosen_keys:
            chosen.append(item)
            chosen_keys.add(key)
    return chosen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--beam-size", type=int, default=36)
    parser.add_argument("--per-overlap", type=int, default=4)
    parser.add_argument("--restarts", type=int, default=4)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=20)
    parser.add_argument("--exact-time", type=float, default=60.0)
    parser.add_argument("--out", default="consensus_core_escape.json")
    args = parser.parse_args()

    archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    seeds = [item for item in archive["archive"] if item["value"] == 40]
    core = set.intersection(*[{tuple(edge) for edge in item["edges"]} for item in seeds])
    assert len(core) == 25
    beam = [
        {
            "node_id": item["id"],
            "edges": item["edges"],
            "bits": item["bits"],
            "geometric_bad_triples": 40,
            "core_overlap": 25,
            "depth": 0,
        }
        for item in seeds
    ]
    visited = {factor_key(item["edges"]) for item in beam}
    all_new = {}
    layers = []
    serial = 0

    for depth in range(1, args.depth + 1):
        jobs = [
            (
                item["node_id"],
                item["edges"],
                item["bits"],
                5000,
                args.restarts,
                202607174000 + depth * 1000 + index,
                True,
            )
            for index, item in enumerate(beam)
        ]
        raw = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(expand_base, job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                raw.extend(result["results"])
                print(
                    f"depth={depth} parent={result['parent']} safe={len(result['results'])}",
                    flush=True,
                )
        unique = {}
        for item in raw:
            key = factor_key(item["edges"])
            if key in visited:
                continue
            old = unique.get(key)
            if old is None or item["geometric_bad_triples"] < old["geometric_bad_triples"]:
                serial += 1
                item["node_id"] = f"c{depth}_{serial:06d}"
                item["depth"] = depth
                item["core_overlap"] = len(set(key) & core)
                unique[key] = item
        visited.update(unique)
        all_new.update(unique)
        candidates = list(unique.values())
        beam = choose(candidates, args.beam_size, args.per_overlap)
        histogram = Counter(item["geometric_bad_triples"] for item in candidates)
        overlap_best = {}
        for item in candidates:
            value = item["geometric_bad_triples"]
            overlap_best[item["core_overlap"]] = min(overlap_best.get(item["core_overlap"], value), value)
        layer = {
            "depth": depth,
            "parents": len(jobs),
            "raw_safe_neighbors": len(raw),
            "new_unique_factors": len(candidates),
            "best_value": min(histogram) if histogram else None,
            "minimum_core_overlap": min(overlap_best) if overlap_best else None,
            "best_value_by_core_overlap": dict(sorted(overlap_best.items())),
            "value_histogram": dict(sorted(histogram.items())),
            "beam": beam,
        }
        layers.append(layer)
        print(
            f"layer={depth} new={len(candidates)} best={layer['best_value']} "
            f"min_core={layer['minimum_core_overlap']} beam={len(beam)}",
            flush=True,
        )
        checkpoint = {
            "parameters": vars(args),
            "consensus_core": [list(edge) for edge in sorted(core)],
            "layers": layers,
            "exact": [],
        }
        (OUT / args.out).write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
        if not beam or layer["best_value"] is not None and layer["best_value"] <= 36:
            break

    ranked = sorted(
        all_new.values(),
        key=lambda x: (x["geometric_bad_triples"], x["core_overlap"], x["depth"]),
    )
    exact_pool = ranked[: args.exact_top]
    exact = []
    for rank, item in enumerate(exact_pool, 1):
        solve = exact_weighted(item, args.exact_time)
        exact.append({"rank": rank, "candidate": item, "solve": solve})
        print(
            f"exact {rank}: warm={item['geometric_bad_triples']} core={item['core_overlap']} "
            f"{solve.get('status')} {solve.get('violations')}",
            flush=True,
        )
    payload = {
        "parameters": vars(args),
        "consensus_core": [list(edge) for edge in sorted(core)],
        "layers": layers,
        "visited_factors": len(visited),
        "top100": ranked[:100],
        "exact": exact,
    }
    path = OUT / args.out
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(path, flush=True)


if __name__ == "__main__":
    main()
