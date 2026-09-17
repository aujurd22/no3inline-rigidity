#!/usr/bin/env python3
"""Validate whether the empirical pair-codegree potential is useful at m=37.

This is deliberately a diagnostic, not a solver.  It compares existing basin
artifacts with random 2-factors, then holds the best72 factor fixed and measures
how its orientation energy correlates with the exact forbidden-clause count.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


M = 37


def potential(co3: np.ndarray, cells) -> int:
    ids = np.array([x * M + y for x, y in cells], dtype=np.int32)
    return int(co3[np.ix_(ids, ids)].sum() // 2)


def degree_ok(cells) -> bool:
    degree = [0] * M
    for x, y in cells:
        degree[x] += 1
        degree[y] += 1
    return len(cells) == M and len(set(map(tuple, cells))) == M and all(d == 2 for d in degree)


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--results", type=Path, default=here / "results")
    ap.add_argument("--co3", type=Path, default=here / "co3_m37.npy")
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--random-factors", type=int, default=20_000)
    ap.add_argument("--random-orientations", type=int, default=50_000)
    ap.add_argument("--greedy-restarts", type=int, default=3_000)
    ap.add_argument("--out", type=Path,
                    default=here / "results" / "pair_codegree_37" /
                    "m37_pair_potential_validation.json")
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    co3 = np.load(args.co3, mmap_mode="r")

    # Compare available oriented 2-factor candidates against random permutation factors.
    candidates = []
    for path in args.results.glob("best_*_edges.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        cells = data.get("edges", [])
        if data.get("m") == M and degree_ok(cells):
            candidates.append({"name": path.name, "violations": data.get("viol", data.get("cls")),
                               "potential": potential(co3, cells)})

    solved = json.loads((args.results / "swarm_D1_2_best72_solved.json").read_text())
    best72_cells = solved["maxsat_cells"]
    best72_potential = potential(co3, best72_cells)
    candidates.append({"name": "best72_maxsat_cells", "violations": solved["maxsat_n_violated"],
                       "potential": best72_potential})

    random_factor_energy = np.empty(args.random_factors, dtype=np.int64)
    for k in range(args.random_factors):
        perm = rng.permutation(M)
        ids = np.arange(M) * M + perm
        random_factor_energy[k] = co3[np.ix_(ids, ids)].sum() // 2
    for row in candidates:
        row["random_factor_lower_tail"] = float(np.mean(random_factor_energy <= row["potential"]))
        row["random_factor_z"] = float((row["potential"] - random_factor_energy.mean()) /
                                        random_factor_energy.std())

    numeric = [r for r in candidates if isinstance(r["violations"], (int, float))]
    candidate_corr = float(np.corrcoef([r["potential"] for r in numeric],
                                       [r["violations"] for r in numeric])[0, 1])
    ordinary = [r for r in numeric if r["name"] != "best72_maxsat_cells"]
    candidate_corr_without_best72 = float(np.corrcoef(
        [r["potential"] for r in ordinary], [r["violations"] for r in ordinary])[0, 1])

    # Orientation-only experiment on the fixed best72 undirected factor.
    clauses_data = json.loads((args.results / "swarm_D1_2_best72_clauses.json").read_text())
    edges = [tuple(e) for e in clauses_data["edges"]]
    clauses = np.asarray(clauses_data["clauses"], dtype=np.int16)
    exact_bits = np.asarray(solved["maxsat_solution"], dtype=np.int8)
    ecount = len(edges)
    J = np.zeros((ecount, ecount, 2, 2), dtype=np.int32)
    for i in range(ecount):
        for j in range(i + 1, ecount):
            for a in range(2):
                for b in range(2):
                    u = edges[i] if a == 0 else edges[i][::-1]
                    v = edges[j] if b == 0 else edges[j][::-1]
                    J[i, j, a, b] = co3[u[0] * M + u[1], v[0] * M + v[1]]

    def bit_energy(bits) -> int:
        return sum(int(J[i, j, bits[i], bits[j]])
                   for i in range(ecount) for j in range(i + 1, ecount))

    def violations(bits) -> int:
        return int(np.all(bits[clauses[:, :3]] == clauses[:, 3:], axis=1).sum())

    B = rng.integers(0, 2, (args.random_orientations, ecount), dtype=np.int8)
    energies = np.zeros(args.random_orientations, dtype=np.int32)
    for i in range(ecount):
        for j in range(i + 1, ecount):
            energies += J[i, j, B[:, i], B[:, j]]
    bad = np.zeros(args.random_orientations, dtype=np.int16)
    for e1, e2, e3, a, b, c in clauses:
        bad += (B[:, e1] == a) & (B[:, e2] == b) & (B[:, e3] == c)
    order = np.argsort(energies)
    deciles = []
    for rank, ids in enumerate(np.array_split(order, 10)):
        deciles.append({"decile_low_to_high": rank + 1, "mean_potential": float(energies[ids].mean()),
                        "mean_violations": float(bad[ids].mean()), "min_violations": int(bad[ids].min())})

    local = []
    best = (10**18, None, None)
    for _ in range(args.greedy_restarts):
        bits = rng.integers(0, 2, ecount, dtype=np.int8)
        current = bit_energy(bits)
        while True:
            deltas = []
            for i in range(ecount):
                old, new = int(bits[i]), 1 - int(bits[i])
                delta = 0
                for j in range(ecount):
                    if j < i:
                        delta += int(J[j, i, bits[j], new] - J[j, i, bits[j], old])
                    elif j > i:
                        delta += int(J[i, j, new, bits[j]] - J[i, j, old, bits[j]])
                deltas.append(delta)
            move = int(np.argmin(deltas))
            if deltas[move] >= 0:
                break
            bits[move] ^= 1
            current += deltas[move]
        v = violations(bits)
        local.append((current, v))
        if current < best[0]:
            best = (current, v, bits.copy())

    payload = {
        "definition": "pair potential = sum_{u<v in S} co3[u,v]",
        "random_factor_baseline": {
            "samples": args.random_factors, "mean": float(random_factor_energy.mean()),
            "std": float(random_factor_energy.std()), "min": int(random_factor_energy.min()),
            "quantiles": {str(q): float(np.quantile(random_factor_energy, q))
                          for q in (0.001, 0.01, 0.05, 0.5, 0.95)},
        },
        "candidates": sorted(candidates, key=lambda row: row["potential"]),
        "candidate_potential_violation_correlation": candidate_corr,
        "candidate_potential_violation_correlation_without_best72": candidate_corr_without_best72,
        "best72_orientation": {
            "maxsat_potential": bit_energy(exact_bits),
            "maxsat_violations": violations(exact_bits),
            "random_samples": args.random_orientations,
            "random_potential_violation_correlation": float(np.corrcoef(energies, bad)[0, 1]),
            "maxsat_potential_z": float((bit_energy(exact_bits) - energies.mean()) / energies.std()),
            "maxsat_potential_lower_tail": float(np.mean(energies <= bit_energy(exact_bits))),
            "deciles": deciles,
            "greedy_restarts": args.greedy_restarts,
            "greedy_lowest_potential": int(best[0]),
            "greedy_lowest_potential_violations": int(best[1]),
            "greedy_best_violation_count": int(min(v for _, v in local)),
            "greedy_mean_violations": float(np.mean([v for _, v in local])),
            "greedy_energy_violation_correlation": float(np.corrcoef(np.asarray(local).T)[0, 1]),
            "greedy_lowest_potential_bits": best[2].tolist(),
        },
        "ruling": "use pair potential as a coarse gate or prior, not as the final optimization objective",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(args.out), "candidate_corr": candidate_corr,
                      "candidate_corr_without_best72": candidate_corr_without_best72,
                      "orientation_corr": payload["best72_orientation"]["random_potential_violation_correlation"],
                      "best72_factor_z": next(r["random_factor_z"] for r in candidates
                                              if r["name"] == "best72_maxsat_cells"),
                      "best72_orientation_tail": payload["best72_orientation"]["maxsat_potential_lower_tail"],
                      "greedy_lowest": [int(best[0]), int(best[1])]}, indent=2))


if __name__ == "__main__":
    main()
