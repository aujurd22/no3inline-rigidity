"""Defect-guided multi-edge destroy/repair in diagonal-safe factor space."""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import random
import time
from collections import Counter
from pathlib import Path

from joint_plateau_lns import local_descent
from signed_nae_core import c4_lifts, geometry_bad_count, validate_factor
from spectral_neighbor_search import generate_switches
from weighted_factor_search import build_state, exact_weighted, is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def canonical(edges):
    return tuple(sorted(tuple(sorted(edge)) for edge in edges))


def edge_distance(left, right):
    return len(set(canonical(left)) ^ set(canonical(right)))


def defect_hotness(edges, bits):
    points = []
    owners = []
    for owner, ((u, v), bit) in enumerate(zip(edges, bits)):
        orbit = c4_lifts(37, (u, v) if bit == 0 else (v, u))
        points.extend(orbit)
        owners.extend([owner] * 4)
    hot = Counter()
    bad = 0
    for i, j, k in itertools.combinations(range(len(points)), 3):
        p, q, r = points[i], points[j], points[k]
        det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        if det:
            continue
        bad += 1
        for owner in {owners[i], owners[j], owners[k]}:
            hot[owner] += 1
    return hot, bad


def weighted_pick(rng, eligible, hot):
    weights = [1 + hot.get(index, 0) for index in eligible]
    return rng.choices(eligible, weights=weights, k=1)[0]


def generate_repair(seed, target, min_k, max_k, rng, global_seen):
    edges = [tuple(edge) for edge in seed["edges"]]
    hot, checked_bad = defect_hotness(edges, seed["bits"])
    assert checked_bad == seed["bad_triples"]
    existing = set(edges)
    results = []
    local_seen = set()
    attempts = 0
    while len(results) < target and attempts < target * 3000:
        attempts += 1
        k = rng.randint(min_k, max_k)
        selected = []
        used_vertices = set()
        while len(selected) < k:
            eligible = [
                index
                for index, (u, v) in enumerate(edges)
                if index not in selected and u not in used_vertices and v not in used_vertices
            ]
            if not eligible:
                break
            index = weighted_pick(rng, eligible, hot)
            selected.append(index)
            used_vertices.update(edges[index])
        if len(selected) != k:
            continue
        endpoints = [vertex for index in selected for vertex in edges[index]]
        rng.shuffle(endpoints)
        new_edges = [
            tuple(sorted((endpoints[2 * i], endpoints[2 * i + 1]))) for i in range(k)
        ]
        if any(u == v for u, v in new_edges) or len(set(new_edges)) != k:
            continue
        untouched = existing - {edges[index] for index in selected}
        if any(edge in untouched for edge in new_edges):
            continue
        candidate = edges[:]
        for index, edge in zip(selected, new_edges):
            candidate[index] = edge
        key = canonical(candidate)
        if key == canonical(edges) or key in local_seen or key in global_seen:
            continue
        if not is_diagonal_safe(candidate):
            continue
        factor = validate_factor(37, candidate)
        assert factor["is_2factor"]
        local_seen.add(key)
        global_seen.add(key)
        results.append(
            {
                "parent": seed["name"],
                "destroyed_indices": sorted(selected),
                "destroy_size": k,
                "destroyed_hotness": sum(hot.get(index, 0) for index in selected),
                "edges": [list(edge) for edge in candidate],
                "bits": seed["bits"],
            }
        )
    return results, {str(index): value for index, value in hot.items()}, attempts


def generate_sequence(seed, target, min_k, max_k, rng, global_seen):
    edges = [tuple(edge) for edge in seed["edges"]]
    hot, checked_bad = defect_hotness(edges, seed["bits"])
    assert checked_bad == seed["bad_triples"]
    results = []
    local_seen = set()
    attempts = 0
    while len(results) < target and attempts < target * 200:
        attempts += 1
        steps = rng.randint(min_k, max_k)
        candidate = edges[:]
        sequence = []
        touched = set()
        for step in range(steps):
            moves = generate_switches(candidate)
            if not moves:
                break
            if step + 1 == steps:
                # Make the last move an explicit repair: enumerate only moves
                # whose resulting factor restores the diagonal hard invariant.
                repair_moves = []
                for move in moves:
                    trial = candidate[:]
                    trial[move[0]], trial[move[1]] = tuple(move[2]), tuple(move[3])
                    if is_diagonal_safe(trial):
                        repair_moves.append(move)
                moves = repair_moves
                if not moves:
                    break
            else:
                # Do not wander too far from the safe manifold: retain a
                # random hot-biased shortlist with at most one overfull
                # diagonal layer, so a final 2-switch can plausibly repair it.
                weighted = sorted(
                    moves,
                    key=lambda move: hot.get(move[0], 0) + hot.get(move[1], 0),
                    reverse=True,
                )[:300]
                rng.shuffle(weighted)
                near = []
                for move in weighted[:100]:
                    trial = candidate[:]
                    trial[move[0]], trial[move[1]] = tuple(move[2]), tuple(move[3])
                    if is_diagonal_safe(trial):
                        near.append(move)
                    else:
                        # Unsafe intermediates are allowed, but only sample a
                        # minority; the explicit final repair handles them.
                        if rng.random() < 0.15:
                            near.append(move)
                moves = near
                if not moves:
                    break
            weights = [1 + hot.get(move[0], 0) + hot.get(move[1], 0) for move in moves]
            left, right, e1, e2 = rng.choices(moves, weights=weights, k=1)[0]
            candidate[left], candidate[right] = tuple(e1), tuple(e2)
            touched.update((left, right))
            sequence.append(
                {
                    "indices": [left, right],
                    "new_edges": [list(e1), list(e2)],
                }
            )
        if len(sequence) != steps:
            continue
        key = canonical(candidate)
        if key == canonical(edges) or key in local_seen or key in global_seen:
            continue
        if not is_diagonal_safe(candidate):
            continue
        assert validate_factor(37, candidate)["is_2factor"]
        local_seen.add(key)
        global_seen.add(key)
        results.append(
            {
                "parent": seed["name"],
                "move_sequence": sequence,
                "destroyed_indices": sorted(touched),
                "destroy_size": steps,
                "destroyed_hotness": sum(hot.get(index, 0) for index in touched),
                "edges": [list(edge) for edge in candidate],
                "bits": seed["bits"],
            }
        )
    return results, {str(index): value for index, value in hot.items()}, attempts


def evaluate(payload):
    index, item, restarts = payload
    edges = [tuple(edge) for edge in item["edges"]]
    _, _, _, constant, jmat = build_state(edges)
    rng = random.Random(202607173000 + index)
    best, bits = local_descent(constant, jmat, item["bits"], rng, 5)
    for _ in range(restarts):
        start = [rng.getrandbits(1) for _ in edges]
        start[0] = 0
        value, candidate_bits = local_descent(constant, jmat, start, rng, 4)
        if value < best:
            best, bits = value, candidate_bits
    geometry = geometry_bad_count(37, edges, bits)
    assert best == geometry["bad_triples"]
    return {
        **item,
        "bad_triples": best,
        "bits": bits,
        "geometry": geometry,
    }


def diverse_select(results, width, slack):
    if not results:
        return []
    best = results[0]["bad_triples"]
    pool = [item for item in results if item["bad_triples"] <= best + slack]
    chosen = [pool.pop(0)]
    while pool and len(chosen) < width:
        item = max(
            pool,
            key=lambda x: (
                100 * min(edge_distance(x["edges"], y["edges"]) for y in chosen)
                - 5 * (x["bad_triples"] - best),
                x["destroyed_hotness"],
            ),
        )
        pool.remove(item)
        chosen.append(item)
    return chosen


def load_initial():
    records = json.loads(
        (OUT / "weighted_breakthrough_verified.json").read_text(encoding="utf-8")
    )
    return [
        {
            "name": item["name"],
            "edges": item["edges"],
            "bits": item["weighted_repeat_exact"]["bits"],
            "bad_triples": item["weighted_repeat_exact"]["violations"],
        }
        for item in records
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--beam", type=int, default=6)
    parser.add_argument("--per-seed", type=int, default=30)
    parser.add_argument("--min-k", type=int, default=2)
    parser.add_argument("--max-k", type=int, default=5)
    parser.add_argument("--restarts", type=int, default=6)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--beam-slack", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=4)
    parser.add_argument("--exact-time", type=float, default=120.0)
    parser.add_argument("--mode", choices=("matching", "sequence"), default="matching")
    parser.add_argument("--out", default="weighted_destroy_repair.json")
    args = parser.parse_args()

    beam = load_initial()
    seen = {canonical(item["edges"]) for item in beam}
    payload = {"parameters": vars(args), "initial": beam, "layers": []}
    started = time.time()
    for depth in range(1, args.depth + 1):
        generated = []
        generation = []
        for seed_index, seed in enumerate(beam):
            generator = generate_sequence if args.mode == "sequence" else generate_repair
            candidates, hot, attempts = generator(
                seed,
                args.per_seed,
                args.min_k,
                args.max_k,
                random.Random(202607174000 + depth * 100 + seed_index),
                seen,
            )
            generated.extend(candidates)
            generation.append(
                {
                    "seed": seed["name"],
                    "bad_triples": seed["bad_triples"],
                    "hotness": hot,
                    "attempts": attempts,
                    "generated": len(candidates),
                }
            )
        print(
            f"layer {depth}: seeds={len(beam)} generated={len(generated)}",
            flush=True,
        )
        if not generated:
            break
        jobs = [(index, item, args.restarts) for index, item in enumerate(generated)]
        results = []
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
        results.sort(key=lambda x: (x["bad_triples"], -x["destroyed_hotness"]))
        best = results[0]["bad_triples"]
        improvements = [item for item in results if item["bad_triples"] < 48]
        exact_pool = (improvements or results)[: args.exact_top]
        exact = []
        for rank, item in enumerate(exact_pool, 1):
            solved = exact_weighted(item, args.exact_time)
            exact.append({"rank": rank, "candidate": item, "solve": solved})
            print(
                f"  exact {rank}: feasible={item['bad_triples']} "
                f"status={solved.get('status')} value={solved.get('violations')}",
                flush=True,
            )
        next_beam = diverse_select(results, args.beam, args.beam_slack)
        for index, item in enumerate(next_beam, 1):
            item["name"] = f"layer{depth}_beam{index}"
        layer = {
            "depth": depth,
            "generation": generation,
            "evaluated": len(results),
            "best_feasible": best,
            "top50": results[:50],
            "exact": exact,
            "next_beam": next_beam,
        }
        payload["layers"].append(layer)
        payload["elapsed_s"] = round(time.time() - started, 3)
        (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if improvements:
            break
        beam = next_beam
    print(OUT / args.out)


if __name__ == "__main__":
    main()
