"""Search 2-switch neighbours using the Ising spectral bound, not clause count."""

from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import json
import random
import time
from pathlib import Path

import numpy as np

from signed_nae_core import (
    build_ising,
    c4_lifts,
    enumerate_clauses,
    geometry_bad_count,
    has_collinear_triple,
    solve_clause_cp_sat,
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
G = {}


def heuristic_ground_state(pairs, jmat, seed, restarts=24):
    """Fast exact-objective multistart descent on the 37-spin Ising model."""
    rng = random.Random(seed)
    n = len(jmat)
    best_value = 10**9
    best_bits = None
    for restart in range(restarts):
        spins = [1 if rng.getrandbits(1) == 0 else -1 for _ in range(n)]
        spins[0] = 1
        # Occasional random kicks make this an iterated local search, while all
        # scoring remains the exact signed-NAE objective.
        for kick_round in range(5):
            while True:
                best_delta = 0
                best_i = None
                for i in range(1, n):
                    field = sum(jmat[i][k] * spins[k] for k in range(n))
                    delta = -2 * spins[i] * field
                    if delta < best_delta:
                        best_delta, best_i = delta, i
                if best_i is None:
                    break
                spins[best_i] *= -1
            energy = sum(
                jmat[i][k] * spins[i] * spins[k]
                for i in range(n)
                for k in range(i + 1, n)
            )
            value = (pairs + energy) // 4
            if value < best_value:
                best_value = value
                best_bits = [0 if s == 1 else 1 for s in spins]
            if kick_round < 4:
                for i in rng.sample(range(1, n), 3):
                    spins[i] *= -1
    return best_value, best_bits


def masks_from_clauses(clauses):
    masks = {}
    for a, b, c, bits in clauses:
        triple = (a, b, c)
        masks[triple] = masks.get(triple, 0) | (1 << bits)
    return masks


def add_mask(jmat, triple, mask, multiplier):
    pair_delta = 0
    for bits in range(8):
        if not ((mask >> bits) & 1) or bits > (bits ^ 7):
            continue
        pair_delta += multiplier
        signs = [1 if ((bits >> k) & 1) == 0 else -1 for k in range(3)]
        for x, y in ((0, 1), (0, 2), (1, 2)):
            i, j = triple[x], triple[y]
            w = multiplier * signs[x] * signs[y]
            jmat[i][j] += w
            jmat[j][i] += w
    return pair_delta


def init_worker(m, edges, masks, jmat, pairs, clause_count):
    G.update(
        m=m,
        edges=[tuple(e) for e in edges],
        masks={tuple(map(int, k.split(","))): v for k, v in masks.items()},
        jmat=jmat,
        pairs=pairs,
        clause_count=clause_count,
    )


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


def evaluate(spec):
    i, j, e1, e2 = spec
    edges = list(G["edges"])
    edges[i], edges[j] = tuple(e1), tuple(e2)
    lifts = [
        (c4_lifts(G["m"], (u, v)), c4_lifts(G["m"], (v, u)))
        for u, v in edges
    ]
    jmat = [row[:] for row in G["jmat"]]
    pairs = G["pairs"]
    clause_count = G["clause_count"]
    changed = {i, j}
    n = len(edges)
    for triple in itertools.combinations(range(n), 3):
        if changed.isdisjoint(triple):
            continue
        old = G["masks"].get(triple, 0)
        new = triple_mask(lifts, triple)
        if old == new:
            continue
        pairs += add_mask(jmat, triple, old, -1)
        pairs += add_mask(jmat, triple, new, +1)
        clause_count += new.bit_count() - old.bit_count()
    a = np.asarray(jmat, dtype=float) / 2.0
    lam = float(np.linalg.eigvalsh(a)[0])
    spectral_lb = pairs / 4.0 + n * lam / 4.0
    seed = hash((i, j, tuple(e1), tuple(e2), 20260716)) & 0xFFFFFFFF
    heuristic_v, heuristic_bits = heuristic_ground_state(pairs, jmat, seed)
    return {
        "switch_indices": [i, j],
        "new_edges": [list(e1), list(e2)],
        "edges": [list(e) for e in edges],
        "clauses": clause_count,
        "pairs": pairs,
        "lambda_min_A": lam,
        "spectral_lb": spectral_lb,
        "spectral_ratio": (-n * lam / pairs) if pairs else 0.0,
        "heuristic_violations": heuristic_v,
        "heuristic_bits": heuristic_bits,
    }


def generate_switches(edges):
    existing = set(edges)
    seen = set()
    out = []
    for i, j in itertools.combinations(range(len(edges)), 2):
        a, b = edges[i]
        c, d = edges[j]
        if len({a, b, c, d}) < 4:
            continue
        for raw1, raw2 in (((a, c), (b, d)), ((a, d), (b, c))):
            e1, e2 = tuple(sorted(raw1)), tuple(sorted(raw2))
            if e1 == e2:
                continue
            others = existing - {edges[i], edges[j]}
            if e1 in others or e2 in others:
                continue
            key = tuple(sorted((i, j, e1, e2), key=str))
            final_key = tuple(sorted(others | {e1, e2}))
            if final_key in seen:
                continue
            seen.add(final_key)
            out.append((i, j, e1, e2))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=320)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exact-top", type=int, default=6)
    parser.add_argument("--exact-time", type=float, default=90.0)
    parser.add_argument(
        "--base-neighbor-rank",
        type=int,
        default=0,
        help="use an exact candidate rank from a previous output as the base",
    )
    parser.add_argument("--out", default="spectral_neighbor_results.json")
    args = parser.parse_args()

    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["cases"]
    base = next(c for c in cases if c["name"] == "m37_408_optimal16")
    m = base["m"]
    known_optimum = 16
    if args.base_neighbor_rank:
        previous = json.loads(
            (OUT / "spectral_neighbor_results.json").read_text(encoding="utf-8")
        )
        chosen = previous["exact"][args.base_neighbor_rank - 1]
        edges = [tuple(e) for e in chosen["candidate"]["edges"]]
        known_optimum = chosen["solve"].get("violations")
        print(
            f"using previous exact rank {args.base_neighbor_rank}, V={known_optimum}",
            flush=True,
        )
    else:
        edges = [tuple(e) for e in base["edges"]]
    print("enumerating base", flush=True)
    clauses = enumerate_clauses(m, edges)
    masks = masks_from_clauses(clauses)
    pairs_list, jmat, missing = build_ising(len(edges), clauses)
    assert not missing
    a = np.asarray(jmat, dtype=float) / 2.0
    base_lam = float(np.linalg.eigvalsh(a)[0])
    base_spec = len(pairs_list) / 4 + len(edges) * base_lam / 4

    switches = generate_switches(edges)
    rng = random.Random(2026071623)
    rng.shuffle(switches)
    switches = switches[: min(args.sample, len(switches))]
    packed_masks = {",".join(map(str, k)): v for k, v in masks.items()}
    print(
        f"base clauses={len(clauses)} spectral_lb={base_spec:.4f}; "
        f"testing {len(switches)} switches",
        flush=True,
    )
    started = time.time()
    results = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=args.workers,
        initializer=init_worker,
        initargs=(m, edges, packed_masks, jmat, len(pairs_list), len(clauses)),
    ) as pool:
        for idx, item in enumerate(pool.map(evaluate, switches, chunksize=1), 1):
            results.append(item)
            if idx % 50 == 0:
                best = min(
                    results,
                    key=lambda x: (x["heuristic_violations"], x["clauses"]),
                )
                print(
                    f"  {idx}: best heuristicV={best['heuristic_violations']} "
                    f"spectral_lb={best['spectral_lb']:.3f} clauses={best['clauses']}",
                    flush=True,
                )

    results.sort(
        key=lambda x: (
            x["heuristic_violations"],
            x["clauses"],
            x["spectral_lb"],
        )
    )
    exact = []
    for rank, item in enumerate(results[: args.exact_top], 1):
        print(
            f"exact rank {rank}: heuristicV={item['heuristic_violations']} "
            f"spec={item['spectral_lb']:.3f} clauses={item['clauses']}",
            flush=True,
        )
        candidate_edges = [tuple(e) for e in item["edges"]]
        candidate_clauses = enumerate_clauses(m, candidate_edges)
        solved = solve_clause_cp_sat(
            candidate_clauses, len(candidate_edges), args.exact_time
        )
        if solved.get("bits") is not None:
            solved["geometry"] = geometry_bad_count(
                m, candidate_edges, solved["bits"]
            )
        exact.append({"rank": rank, "candidate": item, "solve": solved})
        print(
            f"  -> {solved.get('status')} V={solved.get('violations')} "
            f"bound={solved.get('best_bound')}",
            flush=True,
        )

    payload = {
        "base": {
            "clauses": len(clauses),
            "pairs": len(pairs_list),
            "lambda_min_A": base_lam,
            "spectral_lb": base_spec,
            "known_optimum": known_optimum,
        },
        "sampled": len(results),
        "elapsed_s": round(time.time() - started, 3),
        "top20": results[:20],
        "exact": exact,
    }
    OUT.mkdir(exist_ok=True)
    target = OUT / args.out
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
