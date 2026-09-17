#!/usr/bin/env python3
"""Test a first-order-heatmap weighted pair cavity proxy at m=37.

For a compatible oriented pair u,v, replace the raw number of dangerous third
cells by the sum of their projected m=37 one-cell enrichments.  The test is
strictly on held-out random orientations of the fixed best72 undirected factor.
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np


M = 37


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--constraints", type=Path, default=here / "line_cons_m37.pkl")
    ap.add_argument("--co3", type=Path, default=here / "co3_m37.npy")
    ap.add_argument("--volume", type=Path, default=here / "results" /
                    "volume_heatmap_37" / "ntil_volume_37.npz")
    ap.add_argument("--samples", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--out", type=Path, default=here / "results" /
                    "pair_codegree_37" / "weighted_cavity_m37.json")
    args = ap.parse_args()

    results = here / "results"
    clauses_data = json.loads((results / "swarm_D1_2_best72_clauses.json").read_text())
    solved = json.loads((results / "swarm_D1_2_best72_solved.json").read_text())
    edges = [tuple(e) for e in clauses_data["edges"]]
    clauses = np.asarray(clauses_data["clauses"], dtype=np.int16)
    exact_bits = np.asarray(solved["maxsat_solution"], dtype=np.int8)
    volume = np.load(args.volume)
    weight_maps = {
        "combined_projection": volume["prediction_m37"].reshape(-1).astype(float),
        "pure_cross_m_trend": np.exp2(
            volume["prediction_pure_trend_log2"].reshape(-1).astype(float)),
        "recent_template": np.exp2(
            volume["prediction_recent_template_log2"].reshape(-1).astype(float)),
        "inverse_conflict_degree": 1.0 / volume["conflict_degree_m37"].reshape(-1).astype(float),
    }
    for name, values in weight_maps.items():
        weight_maps[name] = values / values.mean()
    co3 = np.load(args.co3, mmap_mode="r")
    with args.constraints.open("rb") as f:
        constraints, incidence = pickle.load(f)

    # Only the 74 orientations of the fixed factor are required.
    oriented_ids = sorted({x * M + y for x, y in edges for x, y in ((x, y), (y, x))})
    line_mass = {
        name: np.fromiter((sum(values[w] for w in d) for d in constraints),
                          dtype=float, count=len(constraints))
        for name, values in weight_maps.items()
    }
    pair_mass = {name: {} for name in weight_maps}
    mismatches = 0
    directly_bad = 0
    for pos, a in enumerate(oriented_ids):
        ia = incidence[a]
        for b in oriented_ids[pos + 1:]:
            ib = incidence[b]
            first, second = (ia, ib) if len(ia) <= len(ib) else (ib, ia)
            raw = 0
            weighted = {name: 0.0 for name in weight_maps}
            bad = False
            for line_no, wa in first.items():
                wb = second.get(line_no)
                if wb is None:
                    continue
                if wa + wb > 2:
                    bad = True
                    continue
                d = constraints[line_no]
                raw += len(d) - 2
                for name, values in weight_maps.items():
                    weighted[name] += (line_mass[name][line_no] -
                                       values[a] - values[b])
            if bad:
                directly_bad += 1
            expected = int(co3[a, b])
            mismatches += raw != expected
            for name in weight_maps:
                pair_mass[name][a, b] = pair_mass[name][b, a] = weighted[name]
    if mismatches:
        raise AssertionError(f"weighted construction disagrees with co3 on {mismatches} pairs")

    ecount = len(edges)
    J = np.zeros((ecount, ecount, 2, 2), dtype=np.int32)
    JW = {name: np.zeros((ecount, ecount, 2, 2), dtype=float)
          for name in weight_maps}
    for i in range(ecount):
        for j in range(i + 1, ecount):
            for a in range(2):
                for b in range(2):
                    u = edges[i] if a == 0 else edges[i][::-1]
                    v = edges[j] if b == 0 else edges[j][::-1]
                    ui, vi = u[0] * M + u[1], v[0] * M + v[1]
                    J[i, j, a, b] = co3[ui, vi]
                    for name in weight_maps:
                        JW[name][i, j, a, b] = pair_mass[name][ui, vi]

    rng = np.random.default_rng(args.seed)
    B = rng.integers(0, 2, (args.samples, ecount), dtype=np.int8)
    raw = np.zeros(args.samples, dtype=float)
    weighted = {name: np.zeros(args.samples, dtype=float) for name in weight_maps}
    for i in range(ecount):
        for j in range(i + 1, ecount):
            raw += J[i, j, B[:, i], B[:, j]]
            for name in weight_maps:
                weighted[name] += JW[name][i, j, B[:, i], B[:, j]]
    bad = np.zeros(args.samples, dtype=float)
    for e1, e2, e3, a, b, c in clauses:
        bad += (B[:, e1] == a) & (B[:, e2] == b) & (B[:, e3] == c)

    cut = args.samples // 2
    variant_results = {}
    for name, energy_values in weighted.items():
        Xtrain = np.column_stack((np.ones(cut), raw[:cut], energy_values[:cut]))
        beta, *_ = np.linalg.lstsq(Xtrain, bad[:cut], rcond=None)
        combined = np.column_stack((np.ones(args.samples - cut), raw[cut:],
                                    energy_values[cut:])) @ beta
        variant_results[name] = {
            "weighted_correlation_all": float(np.corrcoef(energy_values, bad)[0, 1]),
            "weighted_correlation_test": float(np.corrcoef(
                energy_values[cut:], bad[cut:])[0, 1]),
            "raw_plus_weighted_correlation_test": float(np.corrcoef(
                combined, bad[cut:])[0, 1]),
            "train_coefficients_intercept_raw_weighted": beta.tolist(),
        }
    all_names = list(weight_maps)
    Xall_train = np.column_stack(
        [np.ones(cut), raw[:cut]] + [weighted[name][:cut] for name in all_names])
    beta_all, *_ = np.linalg.lstsq(Xall_train, bad[:cut], rcond=None)
    pred_all = np.column_stack(
        [np.ones(args.samples - cut), raw[cut:]] +
        [weighted[name][cut:] for name in all_names]) @ beta_all

    def energy(bits, table):
        return float(sum(table[i, j, bits[i], bits[j]]
                         for i in range(ecount) for j in range(i + 1, ecount)))

    def lower_tail(values, target):
        return float(np.mean(values <= target))

    def low_percent_mean(values, percent=0.01):
        take = max(1, int(len(values) * percent))
        ids = np.argpartition(values, take - 1)[:take]
        return float(bad[ids].mean()), int(bad[ids].min())

    exact_raw = energy(exact_bits, J)
    exact_weighted = {name: energy(exact_bits, JW[name]) for name in weight_maps}
    for name, energy_values in weighted.items():
        variant_results[name]["lowest_1pct_mean_min_bad"] = low_percent_mean(energy_values)
        variant_results[name]["maxsat_energy"] = exact_weighted[name]
        variant_results[name]["maxsat_lower_tail"] = lower_tail(
            energy_values, exact_weighted[name])

    def candidate_weighted_potential(cells):
        ids = [x * M + y for x, y in cells]
        totals = {name: 0.0 for name in weight_maps}
        direct = 0
        for pos, a in enumerate(ids):
            ia = incidence[a]
            for b in ids[pos + 1:]:
                ib = incidence[b]
                first, second = (ia, ib) if len(ia) <= len(ib) else (ib, ia)
                pair_bad = False
                for line_no, wa in first.items():
                    wb = second.get(line_no)
                    if wb is None:
                        continue
                    if wa + wb > 2:
                        pair_bad = True
                        continue
                    for name, values in weight_maps.items():
                        totals[name] += (line_mass[name][line_no] -
                                         values[a] - values[b])
                direct += pair_bad
        raw_total = float(co3[np.ix_(ids, ids)].sum() / 2)
        return raw_total, totals, direct

    candidates = []
    for path in results.glob("best_*_edges.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        cells = data.get("edges", [])
        violations = data.get("viol", data.get("cls"))
        if data.get("m") != M or len(cells) != M or not isinstance(violations, (int, float)):
            continue
        raw_total, totals, direct = candidate_weighted_potential(cells)
        candidates.append({"name": path.name, "violations": violations,
                           "raw": raw_total, "weighted": totals,
                           "direct_bad_pairs": direct})
    candidates.append({"name": "best72_maxsat_cells",
                       "violations": int(solved["maxsat_n_violated"]),
                       "raw": exact_raw, "weighted": exact_weighted,
                       "direct_bad_pairs": 0})

    def candidate_correlations(rows):
        if len(rows) < 3:
            return None
        violations = [r["violations"] for r in rows]
        return {
            "count": len(rows),
            "raw": float(np.corrcoef([r["raw"] for r in rows], violations)[0, 1]),
            "weighted": {name: float(np.corrcoef(
                [r["weighted"][name] for r in rows], violations)[0, 1])
                for name in weight_maps},
        }

    def average_ranks(values):
        values = np.asarray(values)
        order = np.argsort(values, kind="mergesort")
        ranks = np.empty(len(values), dtype=float)
        start = 0
        while start < len(values):
            end = start + 1
            while end < len(values) and values[order[end]] == values[order[start]]:
                end += 1
            ranks[order[start:end]] = (start + end - 1) / 2.0
            start = end
        return ranks

    def small_sample_robustness(rows):
        y = np.asarray([r["violations"] for r in rows], dtype=float)
        metrics = {"raw": np.asarray([r["raw"] for r in rows], dtype=float)}
        metrics.update({name: np.asarray([r["weighted"][name] for r in rows], dtype=float)
                        for name in weight_maps})
        answer = {}
        for name, x in metrics.items():
            loo = []
            for i in range(len(rows)):
                keep = np.arange(len(rows)) != i
                loo.append(float(np.corrcoef(x[keep], y[keep])[0, 1]))
            answer[name] = {
                "pearson": float(np.corrcoef(x, y)[0, 1]),
                "spearman": float(np.corrcoef(average_ranks(x), average_ranks(y))[0, 1]),
                "leave_one_out_mean": float(np.mean(loo)),
                "leave_one_out_min": float(np.min(loo)),
                "leave_one_out_max": float(np.max(loo)),
                "leave_one_out_values": loo,
            }
        return answer
    payload = {
        "definition": "sum of projected m37 one-cell enrichment over dangerous third-cell mechanisms",
        "samples": args.samples, "train_samples": cut, "test_samples": args.samples - cut,
        "oriented_cells": len(oriented_ids), "direct_bad_pairs_seen": directly_bad,
        "co3_crosscheck_mismatches": mismatches,
        "random_orientation": {
            "raw_correlation": float(np.corrcoef(raw, bad)[0, 1]),
            "raw_correlation_test": float(np.corrcoef(raw[cut:], bad[cut:])[0, 1]),
            "raw_lowest_1pct_mean_min_bad": low_percent_mean(raw),
            "variants": variant_results,
            "all_variants_correlation_test": float(np.corrcoef(pred_all, bad[cut:])[0, 1]),
            "all_variants_train_coefficients": beta_all.tolist(),
            "all_variants_order": ["intercept", "raw", *all_names],
        },
        "maxsat_orientation": {
            "violations": int(solved["maxsat_n_violated"]),
            "raw_energy": exact_raw, "weighted_energy": exact_weighted,
            "raw_lower_tail": lower_tail(raw, exact_raw),
            "weighted_lower_tail": {
                name: lower_tail(weighted[name], exact_weighted[name]) for name in weight_maps
            },
        },
        "saved_candidate_factors": {
            "rows": candidates,
            "correlations_all": candidate_correlations(candidates),
            "correlations_without_best72": candidate_correlations(
                [r for r in candidates if r["name"] != "best72_maxsat_cells"]),
            "small_sample_robustness_without_best72": small_sample_robustness(
                [r for r in candidates if r["name"] != "best72_maxsat_cells"]),
            "warning": "small heterogeneous convenience sample; correlations are diagnostic only",
        },
    }
    raw_r = payload["random_orientation"]["raw_correlation_test"]
    best_name = max(variant_results,
                    key=lambda name: variant_results[name]["raw_plus_weighted_correlation_test"])
    best_r = variant_results[best_name]["raw_plus_weighted_correlation_test"]
    all_r = payload["random_orientation"]["all_variants_correlation_test"]
    payload["ruling"] = (
        "promote weighted cavity proxy" if best_r > raw_r + 0.02
        else "do not promote: projected one-cell weighting adds no material held-out signal"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"raw_test_r": raw_r, "variants": {
                          name: row["raw_plus_weighted_correlation_test"]
                          for name, row in variant_results.items()},
                      "best_variant": best_name, "best_test_r": best_r,
                      "all_variants_test_r": all_r,
                      "ruling": payload["ruling"]}, indent=2))


if __name__ == "__main__":
    main()
