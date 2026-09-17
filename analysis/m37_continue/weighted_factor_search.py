"""Outer 2-factor search scored by exact multiplicity-weighted geometry energy."""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import math
import random
import time
from collections import Counter
from pathlib import Path

from joint_plateau_lns import local_descent
from signed_nae_core import c4_lifts, geometry_bad_count, solve_cp_sat
from spectral_neighbor_search import generate_switches
from weighted_geometry_ising import collinear_count


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def pair_vector(lifts, i, j):
    values = []
    for bits in range(4):
        points = lifts[i][bits & 1] + lifts[j][(bits >> 1) & 1]
        values.append(collinear_count(points))
    return values


def triple_vector(lifts, a, b, c):
    values = []
    for bits in range(8):
        ga = lifts[a][bits & 1]
        gb = lifts[b][(bits >> 1) & 1]
        gc = lifts[c][(bits >> 2) & 1]
        count = 0
        for p in ga:
            for q in gb:
                for r in gc:
                    det = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
                    count += det == 0
        values.append(count)
    return values


def apply_pair(constant, jmat, i, j, values, multiplier):
    for bits in range(4):
        if bits > (bits ^ 3):
            continue
        weight = values[bits]
        assert weight == values[bits ^ 3]
        if not weight:
            continue
        signs = [1 if ((bits >> k) & 1) == 0 else -1 for k in range(2)]
        constant += multiplier * 2 * weight
        delta = multiplier * 2 * weight * signs[0] * signs[1]
        jmat[i][j] += delta
        jmat[j][i] += delta
    return constant


def apply_triple(constant, jmat, triple, values, multiplier):
    a, b, c = triple
    for bits in range(8):
        if bits > (bits ^ 7):
            continue
        weight = values[bits]
        assert weight == values[bits ^ 7]
        if not weight:
            continue
        constant += multiplier * weight
        signs = [1 if ((bits >> k) & 1) == 0 else -1 for k in range(3)]
        verts = (a, b, c)
        for x, y in ((0, 1), (0, 2), (1, 2)):
            i, j = verts[x], verts[y]
            delta = multiplier * weight * signs[x] * signs[y]
            jmat[i][j] += delta
            jmat[j][i] += delta
    return constant


def build_state(edges):
    lifts = [(c4_lifts(37, e), c4_lifts(37, e[::-1])) for e in edges]
    pair_map = {}
    triple_map = {}
    jmat = [[0] * len(edges) for _ in edges]
    constant = 0
    for i, j in itertools.combinations(range(len(edges)), 2):
        values = pair_vector(lifts, i, j)
        pair_map[(i, j)] = values
        constant = apply_pair(constant, jmat, i, j, values, 1)
    for triple in itertools.combinations(range(len(edges)), 3):
        values = triple_vector(lifts, *triple)
        triple_map[triple] = values
        constant = apply_triple(constant, jmat, triple, values, 1)
    return lifts, pair_map, triple_map, constant, jmat


def is_diagonal_safe(edges):
    plus = Counter()
    minus = Counter()
    for edge in edges:
        for x, y in c4_lifts(37, edge):
            plus[x - y] += 1
            minus[x + y] += 1
    return max([*plus.values(), *minus.values()]) <= 2


def expand_base(payload):
    name, raw_edges, warm_bits, sample, restarts, seed, safe_only = payload
    edges = [tuple(e) for e in raw_edges]
    _, pair_map, triple_map, base_constant, base_jmat = build_state(edges)
    switches = generate_switches(edges)
    rng = random.Random(seed)
    rng.shuffle(switches)
    if safe_only:
        switches = [
            move
            for move in switches
            if is_diagonal_safe(
                edges[: move[0]]
                + [tuple(move[2])]
                + edges[move[0] + 1 : move[1]]
                + [tuple(move[3])]
                + edges[move[1] + 1 :]
            )
        ]
    switches = switches[: min(sample, len(switches))]
    results = []
    for move_no, (left, right, e1, e2) in enumerate(switches):
        candidate_edges = edges[:]
        candidate_edges[left], candidate_edges[right] = tuple(e1), tuple(e2)
        lifts = [
            (c4_lifts(37, e), c4_lifts(37, e[::-1])) for e in candidate_edges
        ]
        constant = base_constant
        jmat = [row[:] for row in base_jmat]
        changed = {left, right}
        for i, j in itertools.combinations(range(len(edges)), 2):
            if changed.isdisjoint((i, j)):
                continue
            constant = apply_pair(constant, jmat, i, j, pair_map[(i, j)], -1)
            constant = apply_pair(constant, jmat, i, j, pair_vector(lifts, i, j), 1)
        for triple in itertools.combinations(range(len(edges)), 3):
            if changed.isdisjoint(triple):
                continue
            constant = apply_triple(
                constant, jmat, triple, triple_map[triple], -1
            )
            constant = apply_triple(
                constant, jmat, triple, triple_vector(lifts, *triple), 1
            )
        move_rng = random.Random(seed ^ (move_no * 0x9E3779B1))
        value, bits = local_descent(constant, jmat, warm_bits, move_rng, 4)
        for _ in range(restarts):
            random_bits = [move_rng.getrandbits(1) for _ in edges]
            random_bits[0] = 0
            candidate_v, candidate_bits = local_descent(
                constant, jmat, random_bits, move_rng, 3
            )
            if candidate_v < value:
                value, bits = candidate_v, candidate_bits
        assert value == geometry_bad_count(37, candidate_edges, bits)["bad_triples"]
        results.append(
            {
                "parent": name,
                "switch_indices": [left, right],
                "new_edges": [list(e1), list(e2)],
                "edges": [list(e) for e in candidate_edges],
                "geometric_bad_triples": value,
                "bits": bits,
            }
        )
    return {"parent": name, "results": results}


def exact_weighted(item, time_limit):
    edges = [tuple(e) for e in item["edges"]]
    _, _, _, constant, jmat = build_state(edges)
    solved = solve_cp_sat(constant, jmat, time_limit, hint=item["bits"])
    if solved.get("bits") is not None:
        solved["geometry"] = geometry_bad_count(37, edges, solved["bits"])
    return solved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-per-seed", type=int, default=80)
    parser.add_argument("--restarts", type=int, default=3)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=8)
    parser.add_argument("--exact-time", type=float, default=120.0)
    parser.add_argument(
        "--seed-source",
        choices=(
            "v14",
            "safe",
            "safe_walk",
            "breakthrough",
            "best40",
            "best40_family",
        ),
        default="v14",
    )
    parser.add_argument("--diagonal-safe-only", action="store_true")
    parser.add_argument("--out", default="weighted_factor_search.json")
    args = parser.parse_args()

    seeds = []
    if args.seed_source == "v14":
        verified = json.loads(
            (OUT / "joint_breakthrough_verified.json").read_text(encoding="utf-8")
        )
        weighted = json.loads(
            (OUT / "weighted_geometry_results.json").read_text(encoding="utf-8")
        )
        weighted_by_name = {item["name"]: item for item in weighted}
        for base in verified:
            solved = weighted_by_name[base["name"]]["weighted_exact"]
            if solved["violations"] == 56:
                seeds.append(
                    {
                        "name": base["name"],
                        "edges": base["edges"],
                        "bits": solved["bits"],
                    }
                )
    elif args.seed_source == "safe":
        safe = json.loads(
            (OUT / "ranked_diagonal_safe.json").read_text(encoding="utf-8")
        )
        for item in safe["exact"]:
            if item["solve"].get("violations") == 56:
                seeds.append(
                    {
                        "name": f"safe_rank{item['rank']}",
                        "edges": item["candidate"]["edges"],
                        "bits": item["solve"]["bits"],
                    }
                )
    elif args.seed_source == "safe_walk":
        previous = json.loads(
            (OUT / "weighted_safe_factor_search.json").read_text(encoding="utf-8")
        )
        for item in previous["exact"]:
            if item["solve"].get("violations") == 56:
                seeds.append(
                    {
                        "name": f"safe_walk_rank{item['rank']}",
                        "edges": item["candidate"]["edges"],
                        "bits": item["solve"]["bits"],
                    }
                )
    elif args.seed_source == "breakthrough":
        breakthroughs = json.loads(
            (OUT / "weighted_breakthrough_verified.json").read_text(encoding="utf-8")
        )
        for item in breakthroughs:
            solved = item["weighted_repeat_exact"]
            seeds.append(
                {
                    "name": item["name"],
                    "edges": item["edges"],
                    "bits": solved["bits"],
                }
            )
    elif args.seed_source == "best40":
        best40 = json.loads((OUT / "weighted_40_verified.json").read_text(encoding="utf-8"))
        seeds.append(
            {
                "name": best40["name"],
                "edges": best40["edges"],
                "bits": best40["weighted_repeat_exact"]["bits"],
            }
        )
    else:
        original = json.loads(
            (OUT / "weighted_40_verified.json").read_text(encoding="utf-8")
        )
        seeds.append(
            {
                "name": "best40_original",
                "edges": original["edges"],
                "bits": original["weighted_repeat_exact"]["bits"],
            }
        )
        family = json.loads(
            (OUT / "partial_hitting_40_slack2.json").read_text(encoding="utf-8")
        )
        for item in family["exact"]:
            if item["solve"].get("violations") == 40:
                seeds.append(
                    {
                        "name": f"best40_family_rank{item['rank']}",
                        "edges": item["candidate"]["edges"],
                        "bits": item["solve"]["bits"],
                    }
                )
    jobs = [
        (
            seed["name"],
            seed["edges"],
            seed["bits"],
            args.sample_per_seed,
            args.restarts,
            202607171000 + i,
            args.diagonal_safe_only,
        )
        for i, seed in enumerate(seeds)
    ]
    print(f"expanding {len(jobs)} weighted seeds", flush=True)
    started = time.time()
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(expand_base, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.extend(result["results"])
            print(
                f"  {result['parent']}: tested={len(result['results'])} "
                f"best={min(x['geometric_bad_triples'] for x in result['results'])}",
                flush=True,
            )
    results.sort(key=lambda x: x["geometric_bad_triples"])
    best = results[0]["geometric_bad_triples"]
    exact_pool = [x for x in results if x["geometric_bad_triples"] < 56]
    if not exact_pool:
        exact_pool = results[: args.exact_top]
    else:
        exact_pool = exact_pool[: args.exact_top]
    exact = []
    for rank, item in enumerate(exact_pool, 1):
        solved = exact_weighted(item, args.exact_time)
        exact.append({"rank": rank, "candidate": item, "solve": solved})
        print(
            f"exact {rank}: feasible={item['geometric_bad_triples']} "
            f"-> {solved.get('status')} {solved.get('violations')}",
            flush=True,
        )
    payload = {
        "parameters": vars(args),
        "seed_count": len(seeds),
        "tested": len(results),
        "elapsed_s": round(time.time() - started, 3),
        "best_feasible_bad_triples": best,
        "top50": results[:50],
        "exact": exact,
    }
    (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(OUT / args.out)


if __name__ == "__main__":
    main()
