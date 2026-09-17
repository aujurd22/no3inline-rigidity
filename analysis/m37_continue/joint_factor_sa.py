"""Simulated annealing directly on diagonal-safe factor plus orientation states."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import random
from collections import Counter, deque
from pathlib import Path

from joint_plateau_lns import local_descent
from signed_nae_core import geometry_bad_count
from weighted_factor_search import build_state, exact_weighted, is_diagonal_safe


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def factor_key(edges):
    return tuple(sorted(tuple(sorted(edge)) for edge in edges))


def polish(edges, bits, rng):
    _, _, _, constant, jmat = build_state(edges)
    value, result = local_descent(constant, jmat, bits, rng, 5)
    # One kicked restart preserves speed while allowing orientation-basin changes.
    kicked = result[:]
    for index in rng.sample(range(1, 37), 4):
        kicked[index] ^= 1
    other_value, other = local_descent(constant, jmat, kicked, rng, 4)
    if other_value < value:
        value, result = other_value, other
    assert value == geometry_bad_count(37, edges, result)["bad_triples"]
    return value, result


def propose(edges, bits, rng):
    existing = set(edges)
    for _ in range(80):
        i, j = rng.sample(range(37), 2)
        if i > j:
            i, j = j, i
        a, b = edges[i]
        c, d = edges[j]
        if len({a, b, c, d}) < 4:
            continue
        if rng.getrandbits(1):
            e1, e2 = tuple(sorted((a, c))), tuple(sorted((b, d)))
        else:
            e1, e2 = tuple(sorted((a, d))), tuple(sorted((b, c)))
        others = existing - {edges[i], edges[j]}
        if e1 == e2 or e1 in others or e2 in others:
            continue
        candidate_edges = edges[:]
        candidate_edges[i], candidate_edges[j] = e1, e2
        if not is_diagonal_safe(candidate_edges):
            continue
        best_value = 10**9
        best_bits = None
        for bi in (0, 1):
            for bj in (0, 1):
                candidate_bits = bits[:]
                candidate_bits[i], candidate_bits[j] = bi, bj
                value = geometry_bad_count(37, candidate_edges, candidate_bits)["bad_triples"]
                if value < best_value:
                    best_value, best_bits = value, candidate_bits
        return candidate_edges, best_bits, best_value
    return None


def run_trajectory(payload):
    trajectory, seed_item, moves, epoch, polish_every, tabu_size = payload
    rng = random.Random(202607173000 + trajectory * 0x9E3779B1)
    edges = [tuple(edge) for edge in seed_item["edges"]]
    bits = list(seed_item["bits"])
    value = geometry_bad_count(37, edges, bits)["bad_triples"]
    value, bits = polish(edges, bits, rng)
    best_value = value
    best = {factor_key(edges): (value, edges[:], bits[:])}
    tabu_queue = deque([factor_key(edges)])
    tabu = {factor_key(edges)}
    accepted = 0
    safe_proposals = 0
    value_visits = Counter([value])

    for step in range(moves):
        proposal = propose(edges, bits, rng)
        if proposal is None:
            continue
        safe_proposals += 1
        candidate_edges, candidate_bits, candidate_value = proposal
        key = factor_key(candidate_edges)
        phase = (step % epoch) / max(1, epoch - 1)
        temperature = 14.0 * (0.06 ** phase)
        delta = candidate_value - value
        accept = delta <= 0 or rng.random() < math.exp(-delta / temperature)
        if key in tabu and candidate_value >= best_value:
            accept = False
        if not accept:
            continue
        edges, bits, value = candidate_edges, candidate_bits, candidate_value
        accepted += 1
        if accepted % polish_every == 0:
            value, bits = polish(edges, bits, rng)
        value_visits[value] += 1
        key = factor_key(edges)
        tabu_queue.append(key)
        tabu.add(key)
        while len(tabu_queue) > tabu_size:
            old = tabu_queue.popleft()
            if old not in tabu_queue:
                tabu.discard(old)
        if value <= max(44, best_value):
            old = best.get(key)
            if old is None or value < old[0]:
                best[key] = (value, edges[:], bits[:])
            best_value = min(best_value, value)
            if best_value <= 36:
                break

    records = []
    for value, record_edges, record_bits in sorted(best.values(), key=lambda x: x[0])[:30]:
        records.append(
            {
                "trajectory": trajectory,
                "seed": seed_item["id"],
                "bad_triples": value,
                "edges": [list(edge) for edge in record_edges],
                "bits": record_bits,
            }
        )
    return {
        "trajectory": trajectory,
        "seed": seed_item["id"],
        "moves": moves,
        "safe_proposals": safe_proposals,
        "accepted": accepted,
        "best_value": best_value,
        "value_visits": dict(sorted(value_visits.items())),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectories", type=int, default=12)
    parser.add_argument("--moves", type=int, default=12000)
    parser.add_argument("--epoch", type=int, default=1200)
    parser.add_argument("--polish-every", type=int, default=60)
    parser.add_argument("--tabu-size", type=int, default=240)
    parser.add_argument("--seed-max", type=int, default=44)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=20)
    parser.add_argument("--exact-time", type=float, default=60.0)
    parser.add_argument("--out", default="joint_factor_sa.json")
    args = parser.parse_args()

    archive = json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))
    seeds = [
        item
        for item in archive["archive"]
        if item["value"] <= args.seed_max and item["diagonal_safe"]
    ]
    assert seeds
    jobs = [
        (
            index,
            seeds[index % len(seeds)],
            args.moves,
            args.epoch,
            args.polish_every,
            args.tabu_size,
        )
        for index in range(args.trajectories)
    ]
    summaries = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_trajectory, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            summaries.append(result)
            print(
                f"trajectory={result['trajectory']} seed={result['seed']} "
                f"accepted={result['accepted']} best={result['best_value']}",
                flush=True,
            )

    by_factor = {}
    for summary in summaries:
        for item in summary["records"]:
            key = factor_key(item["edges"])
            old = by_factor.get(key)
            if old is None or item["bad_triples"] < old["bad_triples"]:
                by_factor[key] = item
    records = sorted(by_factor.values(), key=lambda x: x["bad_triples"])
    exact_pool = records[: args.exact_top]
    exact = []
    for rank, item in enumerate(exact_pool, 1):
        solve = exact_weighted(item, args.exact_time)
        exact.append({"rank": rank, "candidate": item, "solve": solve})
        print(
            f"exact {rank}: warm={item['bad_triples']} "
            f"{solve.get('status')} {solve.get('violations')}",
            flush=True,
        )
    payload = {
        "parameters": vars(args),
        "seed_ids": [item["id"] for item in seeds],
        "trajectory_summaries": sorted(summaries, key=lambda x: x["trajectory"]),
        "unique_elite_factors": len(records),
        "elite_histogram": dict(sorted(Counter(x["bad_triples"] for x in records).items())),
        "top100": records[:100],
        "exact": exact,
    }
    path = OUT / args.out
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(path, flush=True)


if __name__ == "__main__":
    main()
