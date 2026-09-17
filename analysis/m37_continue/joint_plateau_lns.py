"""Diverse beam/LNS over 2-factors, scored by the true Ising objective.

The search deliberately does not optimize clause count.  Each beam state is a
factor plus an orientation that already realizes its recorded violation count.
Workers sample legal 2-switches, update only clauses touching the two changed
cells, and locally re-optimize the exact signed-NAE energy from a warm start and
random restarts.  Any feasible value below 16 is sent to CP-SAT immediately.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import random
import time
from pathlib import Path

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


def canonical_factor(edges):
    return tuple(sorted(tuple(sorted(e)) for e in edges))


def triple_mask(lifts, triple):
    a, b, c = triple
    mask = 0
    for bits in range(8):
        pts = (
            lifts[a][(bits >> 0) & 1]
            + lifts[b][(bits >> 1) & 1]
            + lifts[c][(bits >> 2) & 1]
        )
        if has_collinear_triple(pts):
            mask |= 1 << bits
    return mask


def ising_value(pairs, jmat, spins):
    energy = sum(
        jmat[i][j] * spins[i] * spins[j]
        for i in range(len(jmat))
        for j in range(i + 1, len(jmat))
    )
    numerator = pairs + energy
    assert numerator % 4 == 0
    return numerator // 4


def local_descent(pairs, jmat, bits, rng, kick_rounds=3):
    n = len(jmat)
    spins = [1 if bit == 0 else -1 for bit in bits]
    # Global complement is redundant; pin spin 0.
    if spins[0] < 0:
        spins = [-s for s in spins]
    best_value = 10**9
    best_spins = None
    for kick in range(kick_rounds):
        while True:
            best_delta = 0
            best_i = None
            for i in range(1, n):
                field = sum(jmat[i][k] * spins[k] for k in range(n))
                delta_energy = -2 * spins[i] * field
                if delta_energy < best_delta:
                    best_delta, best_i = delta_energy, i
            if best_i is None:
                break
            spins[best_i] *= -1
        value = ising_value(pairs, jmat, spins)
        if value < best_value:
            best_value = value
            best_spins = spins[:]
        if kick + 1 < kick_rounds:
            for i in rng.sample(range(1, n), 3):
                spins[i] *= -1
    return best_value, [0 if s == 1 else 1 for s in best_spins]


def optimise_orientation(pairs, jmat, warm_bits, rng, restarts):
    best_v, best_bits = local_descent(pairs, jmat, warm_bits, rng, 4)
    n = len(jmat)
    for _ in range(restarts):
        bits = [rng.getrandbits(1) for _ in range(n)]
        bits[0] = 0
        value, candidate = local_descent(pairs, jmat, bits, rng, 3)
        if value < best_v:
            best_v, best_bits = value, candidate
    return best_v, best_bits


def expand_seed(payload):
    name, m, raw_edges, warm_bits, sample, restarts, seed = payload
    edges = [tuple(e) for e in raw_edges]
    clauses = enumerate_clauses(m, edges)
    masks = masks_from_clauses(clauses)
    pair_list, base_jmat, missing = build_ising(len(edges), clauses)
    assert not missing
    base_pairs = len(pair_list)
    switches = generate_switches(edges)
    rng = random.Random(seed)
    rng.shuffle(switches)
    switches = switches[: min(sample, len(switches))]
    results = []

    for move_index, (i, j, e1, e2) in enumerate(switches):
        candidate_edges = edges[:]
        candidate_edges[i], candidate_edges[j] = tuple(e1), tuple(e2)
        lifts = [
            (c4_lifts(m, (u, v)), c4_lifts(m, (v, u)))
            for u, v in candidate_edges
        ]
        jmat = [row[:] for row in base_jmat]
        pairs = base_pairs
        clause_count = len(clauses)
        changed = {i, j}
        for triple in itertools.combinations(range(len(edges)), 3):
            if changed.isdisjoint(triple):
                continue
            old = masks.get(triple, 0)
            new = triple_mask(lifts, triple)
            if old == new:
                continue
            pairs += add_mask(jmat, triple, old, -1)
            pairs += add_mask(jmat, triple, new, +1)
            clause_count += new.bit_count() - old.bit_count()

        value, bits = optimise_orientation(
            pairs,
            jmat,
            warm_bits,
            random.Random(seed ^ (move_index * 0x9E3779B1)),
            restarts,
        )
        results.append(
            {
                "parent": name,
                "switch_indices": [i, j],
                "new_edges": [list(e1), list(e2)],
                "edges": [list(e) for e in candidate_edges],
                "clauses": clause_count,
                "violations": value,
                "bits": bits,
            }
        )
    return {"parent": name, "tested": len(results), "candidates": results}


def load_initial_beam():
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["cases"]
    base = next(c for c in cases if c["name"] == "m37_408_optimal16")
    signed = json.loads((OUT / "signed_nae_results.json").read_text(encoding="utf-8"))["cases"]
    solved = next(c for c in signed if c["name"] == "m37_408_optimal16")
    beam = [
        {
            "name": "base_408",
            "edges": base["edges"],
            "bits": solved["exact"]["bits"],
            "violations": 16,
            "clauses": 408,
        }
    ]
    neighbours = json.loads(
        (OUT / "spectral_neighbor_results.json").read_text(encoding="utf-8")
    )["exact"]
    for item in neighbours:
        if item["solve"].get("violations") == 16:
            beam.append(
                {
                    "name": f"seed_rank{item['rank']}",
                    "edges": item["candidate"]["edges"],
                    "bits": item["solve"]["bits"],
                    "violations": 16,
                    "clauses": item["candidate"]["clauses"],
                }
            )
    return beam


def load_resume_beam(path):
    previous = json.loads(Path(path).read_text(encoding="utf-8"))
    beam = previous["layers"][-1]["next_beam"]
    if not beam:
        raise ValueError(f"no next_beam in {path}")
    return beam


def edge_distance(a, b):
    return len(set(canonical_factor(a)) ^ set(canonical_factor(b)))


def diverse_select(candidates, width, seen, slack=0):
    unique = {}
    for item in candidates:
        key = canonical_factor(item["edges"])
        if key in seen:
            continue
        current = unique.get(key)
        if current is None or item["violations"] < current["violations"]:
            unique[key] = item
    pool = sorted(unique.values(), key=lambda x: (x["violations"], x["clauses"]))
    if not pool:
        return []
    cutoff = min(item["violations"] for item in pool)
    # A small explicit slack lets the beam cross the V+1 saddles that separate
    # distinct V=14 basins.  The best objective is always selected first.
    pool = [item for item in pool if item["violations"] <= cutoff + slack]
    chosen = [pool.pop(0)]
    while pool and len(chosen) < width:
        item = max(
            pool,
            key=lambda x: (
                100 * min(edge_distance(x["edges"], y["edges"]) for y in chosen)
                - 20 * (x["violations"] - cutoff),
                abs(x["clauses"] - 408),
            ),
        )
        pool.remove(item)
        chosen.append(item)
    return chosen


def exact_check(item, time_limit):
    edges = [tuple(e) for e in item["edges"]]
    clauses = enumerate_clauses(37, edges)
    solved = solve_clause_cp_sat(clauses, len(edges), time_limit)
    if solved.get("bits") is not None:
        solved["geometry"] = geometry_bad_count(37, edges, solved["bits"])
    return solved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--beam", type=int, default=8)
    parser.add_argument("--sample-per-seed", type=int, default=70)
    parser.add_argument("--restarts", type=int, default=10)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=10)
    parser.add_argument("--exact-time", type=float, default=60.0)
    parser.add_argument("--known-best", type=int, default=16)
    parser.add_argument("--beam-slack", type=int, default=0)
    parser.add_argument("--resume-from", default="")
    parser.add_argument("--out", default="joint_plateau_lns.json")
    args = parser.parse_args()

    beam = load_resume_beam(args.resume_from) if args.resume_from else load_initial_beam()
    seen = {canonical_factor(item["edges"]) for item in beam}
    payload = {"parameters": vars(args), "initial_beam": beam, "layers": []}
    start = time.time()

    for depth in range(1, args.depth + 1):
        print(f"layer {depth}: expanding {len(beam)} seeds", flush=True)
        jobs = [
            (
                item["name"],
                37,
                item["edges"],
                item["bits"],
                args.sample_per_seed,
                args.restarts,
                2026071700 + depth * 1000 + i,
            )
            for i, item in enumerate(beam)
        ]
        expanded = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(expand_seed, job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                expanded.extend(result["candidates"])
                best = min(x["violations"] for x in result["candidates"])
                print(
                    f"  {result['parent']}: tested={result['tested']} bestV={best}",
                    flush=True,
                )

        expanded.sort(key=lambda x: (x["violations"], x["clauses"]))
        best_v = expanded[0]["violations"]
        print(
            f"layer {depth}: total={len(expanded)} bestV={best_v} "
            f"clauses={expanded[0]['clauses']}",
            flush=True,
        )

        exact_candidates = []
        breakthrough = [x for x in expanded if x["violations"] < args.known_best]
        check_pool = breakthrough or expanded[: args.exact_top]
        for rank, item in enumerate(check_pool, 1):
            solved = exact_check(item, args.exact_time)
            exact_candidates.append({"rank": rank, "candidate": item, "solve": solved})
            print(
                f"  exact {rank}: feasibleV={item['violations']} "
                f"clauses={item['clauses']} -> {solved.get('status')} "
                f"optV={solved.get('violations')}",
                flush=True,
            )

        next_beam = diverse_select(expanded, args.beam, seen, args.beam_slack)
        for i, item in enumerate(next_beam, 1):
            item["name"] = f"layer{depth}_beam{i}"
            seen.add(canonical_factor(item["edges"]))
        layer = {
            "depth": depth,
            "expanded": len(expanded),
            "best_feasible_violations": best_v,
            "top50": expanded[:50],
            "exact": exact_candidates,
            "next_beam": next_beam,
        }
        payload["layers"].append(layer)
        payload["elapsed_s"] = round(time.time() - start, 3)
        (OUT / args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if breakthrough or not next_beam:
            break
        beam = next_beam

    print(OUT / args.out)


if __name__ == "__main__":
    main()
