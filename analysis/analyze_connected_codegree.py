#!/usr/bin/env python3
"""Separate one-cell main effects from the NTIL pair-codegree interaction.

For every compatible endpoint-disjoint pair, fit the weighted additive model

    D(u,v) = h(u) + h(v) + R(u,v)

under the empirical independent-pair weight P(u)P(v).  The residual R is the
connected part of pair codegree: it cannot be assigned to either cell alone.
We then compare the empirical pair co-selection ratio against D/m and R/m.

This is a diagnostic, not a proof.  In particular, the solution cache is not
known to be a uniform sample.  Transposition is averaged explicitly because
it is an exact symmetry of the problem.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from itertools import combinations
from pathlib import Path

import numpy as np

from analyze_pair_codegree_37 import pair_geometry, weighted_quantiles
from build_volume_heatmap_37 import load_solutions


def aggregate_response(x: np.ndarray, obs: np.ndarray, base: np.ndarray,
                       m: int, bins: int = 16) -> dict:
    edges = np.unique(weighted_quantiles(
        x, np.maximum(base, 1e-12), np.linspace(0.0, 1.0, bins + 1)))
    group = np.clip(np.searchsorted(edges, x, side="right") - 1,
                    0, len(edges) - 2)
    points = []
    for q in range(len(edges) - 1):
        mask = group == q
        o = float(obs[mask].sum())
        e = float(base[mask].sum())
        points.append({
            "lo": float(edges[q]), "hi": float(edges[q + 1]),
            "x_over_m": float(np.average(x[mask],
                                             weights=np.maximum(base[mask], 1e-12)) / m),
            "observed": o, "expected": e,
            "ratio": float((o + 10.0) / (e + 10.0)),
            "pairs": int(mask.sum()),
        })
    xx = np.asarray([p["x_over_m"] for p in points])
    yy = np.log2(np.asarray([p["ratio"] for p in points]))
    X = np.stack([np.ones(len(xx)), xx], axis=1)
    beta, *_ = np.linalg.lstsq(X, yy, rcond=None)
    pred = X @ beta
    ss = float(np.sum((yy - yy.mean()) ** 2))
    r2 = 1.0 - float(np.sum((yy - pred) ** 2)) / ss if ss else 1.0
    return {"intercept": float(beta[0]), "slope": float(beta[1]),
            "r2": r2, "points": points}


def poisson_response(x: np.ndarray, obs: np.ndarray, base: np.ndarray,
                     m: int) -> dict:
    """Unbinned Poisson-offset fit of log2(obs/base) against x/m."""
    X = np.stack([np.ones(len(x)), x / m], axis=1)
    beta = np.zeros(2, dtype=float)
    ln2 = math.log(2.0)
    for _ in range(50):
        mean = np.maximum(base, 1e-12) * np.exp(
            np.clip(ln2 * (X @ beta), -30.0, 30.0))
        gradient = ln2 * (X.T @ (obs - mean))
        hessian = ln2 * ln2 * (X.T @ (mean[:, None] * X))
        step = np.linalg.solve(hessian, gradient)
        beta += step
        if float(np.max(np.abs(step))) < 1e-11:
            break
    return {"intercept": float(beta[0]), "slope": float(beta[1]),
            "iterations_converged": True}


def additive_projection(a: np.ndarray, b: np.ndarray, d: np.ndarray,
                        weight: np.ndarray, nc: int) -> tuple[np.ndarray, np.ndarray]:
    """Exact weighted least-squares projection D_ab ~= h_a+h_b."""
    normal = np.zeros((nc, nc), dtype=float)
    rhs = np.zeros(nc, dtype=float)
    incident = np.bincount(np.concatenate((a, b)),
                           weights=np.concatenate((weight, weight)), minlength=nc)
    normal[np.arange(nc), np.arange(nc)] = incident
    np.add.at(normal, (a, b), weight)
    np.add.at(normal, (b, a), weight)
    np.add.at(rhs, a, weight * d)
    np.add.at(rhs, b, weight * d)
    # Eligible-pair graphs here are connected and non-bipartite, hence the
    # unsigned incidence Gram matrix is positive definite.  lstsq remains a
    # safe fallback for an unexpectedly singular small-m graph.
    try:
        h = np.linalg.solve(normal, rhs)
    except np.linalg.LinAlgError:
        h, *_ = np.linalg.lstsq(normal, rhs, rcond=None)
    return h, d - h[a] - h[b]


def analyze(m: int, solutions) -> dict:
    started = time.time()
    nc = m * m
    cells = [(x, y) for x in range(m) for y in range(m)]
    codegree, direct_bad, _ = pair_geometry(m)
    N = len(solutions)
    marginal = np.zeros(nc, dtype=float)
    cooccur = np.zeros((nc, nc), dtype=float)
    for sol in solutions:
        ids = [x * m + y for x, y in sol]
        tids = [y * m + x for x, y in sol]
        for sequence in (ids, tids):
            for u in sequence:
                marginal[u] += 0.5
            for u, v in combinations(sequence, 2):
                cooccur[u, v] += 0.5
                cooccur[v, u] += 0.5
    marginal /= N

    aa, bb = [], []
    for a, u in enumerate(cells):
        for b in range(a + 1, nc):
            v = cells[b]
            if not direct_bad[a, b] and {u[0], u[1]}.isdisjoint({v[0], v[1]}):
                aa.append(a); bb.append(b)
    a = np.asarray(aa, dtype=np.int32)
    b = np.asarray(bb, dtype=np.int32)
    d = codegree[a, b].astype(float)
    base = N * marginal[a] * marginal[b]
    obs = cooccur[a, b]

    h, residual = additive_projection(a, b, d, np.maximum(base, 1e-12), nc)
    fitted = h[a] + h[b]
    total_var = float(np.average((d - np.average(d, weights=base)) ** 2, weights=base))
    residual_var = float(np.average(residual ** 2, weights=base))

    enrichment = np.log2(np.maximum(marginal * m, 1e-300))
    positive = marginal > 0
    h_enrichment_corr = float(np.corrcoef(h[positive] / m, enrichment[positive])[0, 1])

    raw_law = aggregate_response(d, obs, base, m)
    connected_law = aggregate_response(residual, obs, base, m)
    fitted_law = aggregate_response(fitted, obs, base, m)
    return {
        "m": m, "solutions": N, "eligible_pairs": int(len(a)),
        "transposition_symmetrized_pairs": True,
        "projection": {
            "formula": "D(u,v)=h(u)+h(v)+R(u,v)",
            "weighted_variance_explained_by_one_cell_terms":
                1.0 - residual_var / total_var if total_var else 0.0,
            "weighted_residual_mean": float(np.average(residual, weights=base)),
            "weighted_residual_std_over_m": math.sqrt(residual_var) / m,
            "corr_h_over_m_with_log2_cell_enrichment": h_enrichment_corr,
        },
        "raw_codegree_law": raw_law,
        "raw_codegree_poisson_unbinned": poisson_response(d, obs, base, m),
        "raw_codegree_bin_sensitivity": {
            str(bins): aggregate_response(d, obs, base, m, bins=bins)["slope"]
            for bins in (8, 12, 16, 24, 32)
        },
        "additive_component_law": fitted_law,
        "connected_codegree_law": connected_law,
        "connected_codegree_poisson_unbinned": poisson_response(
            residual, obs, base, m),
        "poisson_reference_slope": -1.0 / math.log(2.0),
        "seconds": time.time() - started,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, nargs="+", default=[20, 24, 28])
    ap.add_argument("--cache", type=Path,
                    default=Path(__file__).with_name("flammenkamp_cache"))
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "results" /
                    "pair_codegree_37" / "connected_codegree.json")
    args = ap.parse_args()
    by_m, *_ = load_solutions(args.cache)
    results = []
    for m in args.m:
        print(f"[m={m}] connected codegree", flush=True)
        row = analyze(m, by_m[m])
        results.append(row)
        p = row["projection"]
        print(f"  one-cell variance={p['weighted_variance_explained_by_one_cell_terms']:.4f}; "
              f"raw slope={row['raw_codegree_law']['slope']:.4f}; "
              f"connected slope={row['connected_codegree_law']['slope']:.4f}; "
              f"R2={row['connected_codegree_law']['r2']:.4f}", flush=True)
    payload = {
        "definition": "weighted additive projection of pair codegree",
        "results": results,
        "cross_m": {
            "raw_slope_mean": float(np.mean([r["raw_codegree_law"]["slope"] for r in results])),
            "connected_slope_mean": float(np.mean([r["connected_codegree_law"]["slope"] for r in results])),
            "connected_slope_std": float(np.std([r["connected_codegree_law"]["slope"] for r in results])),
            "one_cell_variance_mean": float(np.mean([
                r["projection"]["weighted_variance_explained_by_one_cell_terms"] for r in results])),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["cross_m"], indent=2))


if __name__ == "__main__":
    main()
