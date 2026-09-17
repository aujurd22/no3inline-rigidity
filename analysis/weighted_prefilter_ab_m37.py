#!/usr/bin/env python3
"""Equal-budget A/B test of raw versus heatmap-weighted m=37 pair prefilters.

Pool: legal 2-switch mutations of the best72 undirected factor.
Ranking: locally minimized raw or weighted pair potential, with direct bad
pairs forbidden by a large penalty.
Evaluation: identical exact line-energy SA for every selected factor.  A line
containing s lifted points contributes C(s,3), the same unit as Board.verify_total().
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import random
import time
from pathlib import Path

import numpy as np


M = 37
PENALTY = 1_000_000.0


def mutate(edges, rng, switches):
    out = list(edges)
    for _ in range(switches):
        for _attempt in range(100):
            i, j = rng.sample(range(len(out)), 2)
            a, b = out[i]; c, d = out[j]
            if len({a, b, c, d}) < 4:
                continue
            choices = [((a, c), (b, d)), ((a, d), (b, c))]
            rng.shuffle(choices)
            old_i, old_j = out[i], out[j]
            rest = set(out)
            rest.remove(old_i); rest.remove(old_j)
            accepted = False
            for e1, e2 in choices:
                e1 = tuple(sorted(e1)); e2 = tuple(sorted(e2))
                if e1 == e2 or e1 in rest or e2 in rest:
                    continue
                out[i], out[j] = e1, e2
                accepted = True
                break
            if accepted:
                break
    return tuple(sorted(out))


def pair_tables(edges, raw_matrix, weighted_matrix, direct_bad):
    E = len(edges)
    raw = np.zeros((E, E, 2, 2), dtype=float)
    weighted = np.zeros_like(raw)
    bad = np.zeros((E, E, 2, 2), dtype=bool)
    for i, (u, v) in enumerate(edges):
        ui = (u * M + v, v * M + u)
        for j in range(i + 1, E):
            x, y = edges[j]
            vj = (x * M + y, y * M + x)
            for a in range(2):
                for b in range(2):
                    raw[i, j, a, b] = raw_matrix[ui[a], vj[b]]
                    weighted[i, j, a, b] = weighted_matrix[ui[a], vj[b]]
                    bad[i, j, a, b] = direct_bad[ui[a], vj[b]]
    return raw, weighted, bad


def quadratic_local_min(table, bad, rng, restarts):
    E = table.shape[0]
    upper_i, upper_j = np.triu_indices(E, 1)
    best_energy, best_bits, best_direct = math.inf, None, None
    for _ in range(restarts):
        bits = rng.integers(0, 2, E, dtype=np.int8)

        def pair_value(i, j, bi, bj):
            return table[i, j, bi, bj] + PENALTY * bad[i, j, bi, bj]

        penalized = table + PENALTY * bad
        energy = float(penalized[upper_i, upper_j, bits[upper_i], bits[upper_j]].sum())
        while True:
            deltas = np.zeros(E, dtype=float)
            for i in range(E):
                old, new = int(bits[i]), 1 - int(bits[i])
                delta = 0.0
                if i:
                    jj = np.arange(i)
                    delta += float((penalized[jj, i, bits[jj], new] -
                                    penalized[jj, i, bits[jj], old]).sum())
                if i + 1 < E:
                    jj = np.arange(i + 1, E)
                    delta += float((penalized[i, jj, new, bits[jj]] -
                                    penalized[i, jj, old, bits[jj]]).sum())
                deltas[i] = delta
            move = int(np.argmin(deltas))
            if deltas[move] >= -1e-9:
                break
            bits[move] ^= 1
            energy += deltas[move]
        direct = int(bad[upper_i, upper_j, bits[upper_i], bits[upper_j]].sum())
        if energy < best_energy:
            best_energy, best_bits, best_direct = float(energy), bits.copy(), direct
    return best_energy, best_bits, int(best_direct)


def exact_line_model(edges, constraints, incidence):
    """Return relevant line factors and per-variable incidence."""
    line_options = {}
    for e, (u, v) in enumerate(edges):
        ids = (u * M + v, v * M + u)
        for state, cell in enumerate(ids):
            for line_no, weight in incidence[cell].items():
                by_edge = line_options.setdefault(line_no, {})
                option = by_edge.setdefault(e, [0, 0])
                option[state] = weight
    factors = []
    occurrence = [[] for _ in edges]
    constant = 0
    for line_no, by_edge in line_options.items():
        if sum(max(w) for w in by_edge.values()) <= 2:
            continue
        options = [(e, w[0], w[1]) for e, w in by_edge.items()]
        index = len(factors)
        factors.append(options)
        if all(w0 == w1 for _, w0, w1 in options):
            s = sum(w0 for _, w0, _ in options)
            constant += math.comb(s, 3) if s >= 3 else 0
        else:
            for e, w0, w1 in options:
                if w0 != w1:
                    occurrence[e].append(index)
    return factors, occurrence, constant


def line_cost(s):
    return s * (s - 1) * (s - 2) // 6 if s >= 3 else 0


def exact_orientation_sa(edges, constraints, incidence, seed, restarts, moves):
    factors, occurrence, constant = exact_line_model(edges, constraints, incidence)
    rng = np.random.default_rng(seed)
    E = len(edges)
    best_cost, best_bits = math.inf, None
    for restart in range(restarts):
        bits = rng.integers(0, 2, E, dtype=np.int8)
        sums = np.asarray([sum(w1 if bits[e] else w0 for e, w0, w1 in options)
                           for options in factors], dtype=np.int16)
        cost = int(sum(line_cost(int(s)) for s in sums))
        local_best = cost
        T0 = max(4.0, cost / 25.0)
        for step in range(moves):
            e = int(rng.integers(E))
            old, new = int(bits[e]), 1 - int(bits[e])
            delta = 0
            changes = []
            for fidx in occurrence[e]:
                options = factors[fidx]
                w0 = w1 = 0
                for ee, a, b in options:
                    if ee == e:
                        w0, w1 = a, b
                        break
                ds = (w1 - w0) if new else (w0 - w1)
                if not ds:
                    continue
                before = int(sums[fidx]); after = before + ds
                delta += line_cost(after) - line_cost(before)
                changes.append((fidx, ds))
            t = T0 * (0.02 / T0) ** (step / max(1, moves - 1))
            if delta <= 0 or rng.random() < math.exp(-delta / t):
                bits[e] = new
                cost += delta
                for fidx, ds in changes:
                    sums[fidx] += ds
                local_best = min(local_best, cost)
                if cost < best_cost:
                    best_cost, best_bits = cost, bits.copy()
        # Deterministic steepest descent from the final state.
        while True:
            best_delta, best_e, best_changes = 0, None, None
            for e in range(E):
                old, new = int(bits[e]), 1 - int(bits[e])
                delta, changes = 0, []
                for fidx in occurrence[e]:
                    w0 = w1 = 0
                    for ee, a, b in factors[fidx]:
                        if ee == e:
                            w0, w1 = a, b; break
                    ds = (w1 - w0) if new else (w0 - w1)
                    if ds:
                        before = int(sums[fidx]); after = before + ds
                        delta += line_cost(after) - line_cost(before)
                        changes.append((fidx, ds))
                if delta < best_delta:
                    best_delta, best_e, best_changes = delta, e, changes
            if best_e is None:
                break
            bits[best_e] ^= 1; cost += best_delta
            for fidx, ds in best_changes:
                sums[fidx] += ds
            if cost < best_cost:
                best_cost, best_bits = cost, bits.copy()
    return {"best_geometric_bad": int(best_cost), "bits": best_bits.tolist(),
            "relevant_lines": len(factors), "constant_bad": int(constant)}


def summarize(rows):
    values = np.asarray([r["exact"]["best_geometric_bad"] for r in rows])
    return {"count": len(rows), "best": int(values.min()),
            "median": float(np.median(values)), "mean": float(values.mean()),
            "values": values.tolist()}


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--pool", type=int, default=600)
    ap.add_argument("--evaluate", type=int, default=8)
    ap.add_argument("--score-restarts", type=int, default=8)
    ap.add_argument("--exact-restarts", type=int, default=12)
    ap.add_argument("--exact-moves", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=20260722)
    ap.add_argument(
        "--seed-input", type=Path,
        help="JSON with edges and bits; defaults to historical best72 artifacts",
    )
    ap.add_argument("--out", type=Path, default=here / "results" /
                    "pair_codegree_37" / "weighted_prefilter_ab_m37.json")
    args = ap.parse_args()
    began = time.time()
    raw_matrix = np.load(here / "co3_m37.npy", mmap_mode="r")
    weighted_matrix = np.load(here / "weighted_co3_m37.npy", mmap_mode="r")
    direct_bad = np.load(here / "direct_bad_m37.npy", mmap_mode="r")
    with (here / "line_cons_m37.pkl").open("rb") as f:
        constraints, incidence = pickle.load(f)
    if args.seed_input:
        clause_data = json.loads(args.seed_input.read_text(encoding="utf-8"))
        solved = None
    else:
        clause_data = json.loads((here / "results" /
                                  "swarm_D1_2_best72_clauses.json").read_text())
        solved = json.loads((here / "results" /
                             "swarm_D1_2_best72_solved.json").read_text())
    seed_edges = tuple(sorted(tuple(e) for e in clause_data["edges"]))

    # The exact line model must reproduce the independently stored Board score.
    factors, _, _ = exact_line_model(seed_edges, constraints, incidence)
    source_bits = (clause_data.get("bits") if args.seed_input else
                   solved["maxsat_solution"])
    known_bits_by_edge = {tuple(e): int(bit)
                          for e, bit in zip(map(tuple, clause_data["edges"]),
                                            source_bits)}
    known_bits = np.asarray([known_bits_by_edge[e] for e in seed_edges], dtype=np.int8)
    known_cost = sum(line_cost(sum(w1 if known_bits[e] else w0
                                   for e, w0, w1 in options)) for options in factors)
    stored_cost = (clause_data.get("verified_board_total", clause_data.get("objective"))
                   if args.seed_input else solved["maxsat_verify_total"])
    if known_cost != stored_cost:
        raise AssertionError(f"exact line model {known_cost} != stored {stored_cost}")

    py_rng = random.Random(args.seed)
    candidates = {}
    while len(candidates) < args.pool:
        switches = py_rng.randint(1, 8)
        edges = mutate(seed_edges, py_rng, switches)
        if edges == seed_edges or edges in candidates:
            continue
        raw, weighted, bad = pair_tables(edges, raw_matrix, weighted_matrix, direct_bad)
        # Identical random starts make the raw/weighted ranking comparison fair.
        score_seed = args.seed + sum((i + 1) * (u * M + v + 1)
                                     for i, (u, v) in enumerate(edges))
        raw_score, raw_bits, raw_direct = quadratic_local_min(
            raw, bad, np.random.default_rng(score_seed), args.score_restarts)
        weighted_score, weighted_bits, weighted_direct = quadratic_local_min(
            weighted, bad, np.random.default_rng(score_seed), args.score_restarts)
        candidates[edges] = {
            "edges": [list(e) for e in edges], "switches_requested": switches,
            "raw_score": raw_score, "weighted_score": weighted_score,
            "raw_direct_bad": raw_direct, "weighted_direct_bad": weighted_direct,
            "raw_bits": raw_bits.tolist(), "weighted_bits": weighted_bits.tolist(),
        }
        if len(candidates) % 100 == 0:
            print(f"  scored {len(candidates)}/{args.pool} factors", flush=True)

    all_rows = list(candidates.values())
    eligible_raw = [r for r in all_rows if r["raw_direct_bad"] == 0]
    eligible_weighted = [r for r in all_rows if r["weighted_direct_bad"] == 0]
    raw_pick = sorted(eligible_raw, key=lambda r: r["raw_score"])[:args.evaluate]
    weighted_pick = sorted(eligible_weighted, key=lambda r: r["weighted_score"])[:args.evaluate]
    baseline_pick = py_rng.sample(all_rows, args.evaluate)
    groups = {"baseline_random": baseline_pick, "raw_prefilter": raw_pick,
              "weighted_prefilter": weighted_pick}

    exact_cache = {}
    for group, rows in groups.items():
        print(f"  exact group {group} ({len(rows)})", flush=True)
        for row in rows:
            key = tuple(map(tuple, row["edges"]))
            if key not in exact_cache:
                # Candidate-specific seed makes overlap receive exactly the same budget/result.
                cseed = args.seed + sum((i + 1) * (u * M + v + 1)
                                        for i, (u, v) in enumerate(key))
                exact_cache[key] = exact_orientation_sa(
                    key, constraints, incidence, cseed,
                    args.exact_restarts, args.exact_moves)
            row["exact"] = exact_cache[key]
    summaries = {name: summarize(rows) for name, rows in groups.items()}
    union = list({id(row): row for rows in groups.values() for row in rows}.values())
    y = np.asarray([r["exact"]["best_geometric_bad"] for r in union], dtype=float)
    correlations = {
        "evaluated_unique": len(union),
        "raw_score_vs_exact": float(np.corrcoef([r["raw_score"] for r in union], y)[0, 1]),
        "weighted_score_vs_exact": float(np.corrcoef(
            [r["weighted_score"] for r in union], y)[0, 1]),
    } if len(union) >= 3 else None
    payload = {
        "definition": "equal-budget prefilter A/B around one m=37 factor",
        "seed_input": str(args.seed_input) if args.seed_input else "historical best72",
        "parameters": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
        "known_seed_crosscheck": {"line_model_bad": known_cost,
                                    "stored_board_bad": stored_cost},
        "pool": {"size": len(all_rows), "raw_direct_free": len(eligible_raw),
                 "weighted_direct_free": len(eligible_weighted)},
        "summaries": summaries, "score_correlations_on_evaluated_union": correlations,
        "groups": groups, "seconds": time.time() - began,
        "ruling": ("weighted prefilter wins this pilot" if
                   summaries["weighted_prefilter"]["median"] <
                   summaries["raw_prefilter"]["median"] else
                   "weighted prefilter does not beat raw in this pilot"),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"summaries": summaries, "correlations": correlations,
                      "seconds": payload["seconds"], "ruling": payload["ruling"]}, indent=2))


if __name__ == "__main__":
    main()
