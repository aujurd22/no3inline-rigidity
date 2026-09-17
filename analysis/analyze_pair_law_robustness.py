#!/usr/bin/env python3
"""Robustness audit for the empirical NTIL pair-codegree law.

The Flammenkamp files are constructive archives, not uniform samples.  This
script therefore checks (1) linear versus quadratic response and (2) whether
the fitted slope changes across consecutive file blocks more than across a
random partition of the same records.
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np

from analyze_pair_codegree_37 import pair_geometry
from build_volume_heatmap_37 import decode_compact, decode_mvr, structural_cells


def load_ordered(path: Path, n: int):
    decoder = decode_mvr if path.name.endswith(".mvr") else decode_compact
    out, seen = [], set()
    for line in path.read_text(encoding="ascii", errors="ignore").splitlines():
        if not line.strip():
            continue
        cells = structural_cells(decoder(line, n), n)
        if cells not in seen:
            seen.add(cells); out.append(cells)
    return out


def fit_poisson(x: np.ndarray, obs: np.ndarray, base: np.ndarray, degree: int):
    X = np.column_stack([np.ones(len(x))] + [x ** k for k in range(1, degree + 1)])
    beta = np.zeros(degree + 1)
    ln2 = math.log(2.0)
    for _ in range(60):
        mean = np.maximum(base, 1e-12) * np.exp(np.clip(ln2 * (X @ beta), -30, 30))
        gradient = ln2 * X.T @ (obs - mean)
        hessian = ln2 * ln2 * X.T @ (mean[:, None] * X)
        step = np.linalg.solve(hessian, gradient)
        beta += step
        if np.max(np.abs(step)) < 1e-11:
            break
    mean = np.maximum(base, 1e-12) * np.exp(np.clip(ln2 * (X @ beta), -30, 30))
    positive = obs > 0
    terms = mean - obs
    terms[positive] += obs[positive] * np.log(obs[positive] / mean[positive])
    return {"coefficients": beta.tolist(), "deviance": 2.0 * float(terms.sum())}


def sufficient_statistics(groups, m, count):
    nc = m * m
    marginal = np.zeros((count, nc), dtype=float)
    cooccur = np.zeros((count, nc, nc), dtype=float)
    size = np.zeros(count, dtype=int)
    for cells, g in groups:
        size[g] += 1
        ids = np.fromiter((x * m + y for x, y in cells), dtype=np.int32)
        tids = np.fromiter((y * m + x for x, y in cells), dtype=np.int32)
        for seq in (ids, tids):
            marginal[g, seq] += 0.5
            block = np.ix_(seq, seq)
            cooccur[g][block] += 0.5
            cooccur[g, seq, seq] -= 0.5
    return marginal, cooccur, size


def group_fit(marginal, cooccur, size, pa, pb, d, m):
    rows = []
    x = d / m
    for g, N in enumerate(size):
        p = marginal[g] / N
        base = N * p[pa] * p[pb]
        obs = cooccur[g, pa, pb]
        mask = base > 1e-10
        linear = fit_poisson(x[mask], obs[mask], base[mask], 1)
        quadratic = fit_poisson(x[mask], obs[mask], base[mask], 2)
        rows.append({
            "group": g, "solutions": int(N), "supported_pairs": int(mask.sum()),
            "linear": linear, "quadratic": quadratic,
            "quadratic_deviance_gain": linear["deviance"] - quadratic["deviance"],
            "quadratic_fraction_of_linear_deviance":
                (linear["deviance"] - quadratic["deviance"]) / linear["deviance"],
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=28)
    ap.add_argument("--blocks", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--cache", type=Path,
                    default=Path(__file__).with_name("flammenkamp_cache"))
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "results" / "pair_codegree_37" /
                    "pair_law_robustness_m28.json")
    args = ap.parse_args()
    m, n = args.m, 2 * args.m
    candidates = [args.cache / f"n{n}_rot4", args.cache / f"n{n}_rot4.few",
                  args.cache / f"n{n}_rot4.mvr"]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise FileNotFoundError(f"no rot4 cache for n={n}")
    solutions = load_ordered(path, n)
    codegree, bad, _ = pair_geometry(m)
    cells = [(x, y) for x in range(m) for y in range(m)]
    pa, pb = [], []
    for a, u in enumerate(cells):
        for b in range(a + 1, m * m):
            v = cells[b]
            if not bad[a, b] and {u[0], u[1]}.isdisjoint({v[0], v[1]}):
                pa.append(a); pb.append(b)
    pa, pb = np.asarray(pa), np.asarray(pb)
    d = codegree[pa, pb].astype(float)

    N, k = len(solutions), args.blocks
    sequential_id = np.minimum(k - 1, np.arange(N) * k // N)
    rng = np.random.default_rng(args.seed)
    random_id = sequential_id[rng.permutation(N)]
    all_id = np.zeros(N, dtype=int)
    analyses = {}
    for name, ids, count in (("full", all_id, 1),
                             ("sequential_blocks", sequential_id, k),
                             ("random_blocks", random_id, k)):
        stats = sufficient_statistics(zip(solutions, ids), m, count)
        analyses[name] = group_fit(*stats, pa, pb, d, m)
    seq_slopes = [r["linear"]["coefficients"][1] for r in analyses["sequential_blocks"]]
    rnd_slopes = [r["linear"]["coefficients"][1] for r in analyses["random_blocks"]]
    payload = {
        "m": m, "source": path.name, "solutions": N, "blocks": k,
        "warning": "constructive archive; neither full file nor blocks are uniform samples",
        "analyses": analyses,
        "block_comparison": {
            "sequential_slope_mean": float(np.mean(seq_slopes)),
            "sequential_slope_std": float(np.std(seq_slopes)),
            "sequential_slope_range": [float(min(seq_slopes)), float(max(seq_slopes))],
            "random_slope_mean": float(np.mean(rnd_slopes)),
            "random_slope_std": float(np.std(rnd_slopes)),
            "random_slope_range": [float(min(rnd_slopes)), float(max(rnd_slopes))],
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"full": analyses["full"][0],
                      "block_comparison": payload["block_comparison"]}, indent=2))


if __name__ == "__main__":
    main()
