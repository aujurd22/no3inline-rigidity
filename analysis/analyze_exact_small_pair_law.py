#!/usr/bin/env python3
"""Fit the pair-codegree law to exact labelled small-m solution spaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_pair_codegree_37 import pair_geometry
from analyze_pair_law_robustness import fit_poisson


def read_counts(path: Path):
    lines = path.read_text(encoding="ascii").splitlines()
    m, total, nodes, seconds = lines[0].split()
    m, total = int(m), int(total)
    marginal = np.fromstring(lines[1], sep=" ", dtype=np.float64)
    pair = np.fromstring(lines[2], sep=" ", dtype=np.float64).reshape(m * m, m * m)
    return m, total, int(nodes), float(seconds), marginal, pair


def analyze(path: Path):
    m, N, nodes, seconds, marginal_count, cooccur = read_counts(path)
    cells = [(x, y) for x in range(m) for y in range(m)]
    D, bad, _ = pair_geometry(m)
    pa, pb = [], []
    for a, u in enumerate(cells):
        for b in range(a + 1, m * m):
            v = cells[b]
            if not bad[a, b] and {u[0], u[1]}.isdisjoint({v[0], v[1]}):
                pa.append(a); pb.append(b)
    pa, pb = np.asarray(pa), np.asarray(pb)
    base = marginal_count[pa] * marginal_count[pb] / N
    obs = cooccur[pa, pb]
    support = base > 0
    if not np.any(support):
        return {
            "m": m, "exact_labelled_solutions": N, "search_nodes": nodes,
            "enumeration_seconds": seconds, "supported_eligible_pairs": 0,
            "observed_supported_pairs": 0, "distinct_supported_codegrees": 0,
            "linear_log2_ratio_vs_D_over_m": None,
            "intercept_only_deviance": None, "pair_deviance_explained": None,
        }
    x = D[pa, pb][support] / m
    null = fit_poisson(np.zeros(int(support.sum())), obs[support], base[support], 0)
    if len(np.unique(x)) >= 2:
        linear = fit_poisson(x, obs[support], base[support], 1)
        explained = (1.0 - linear["deviance"] / null["deviance"]
                     if null["deviance"] else 0.0)
    else:
        linear = None
        explained = None
    # A law can be statistically fitted yet useless.  Report its actual
    # reduction of exact-space pair deviance against the intercept-only null.
    return {
        "m": m, "exact_labelled_solutions": N, "search_nodes": nodes,
        "enumeration_seconds": seconds, "supported_eligible_pairs": int(support.sum()),
        "observed_supported_pairs": int((obs[support] > 0).sum()),
        "distinct_supported_codegrees": int(len(np.unique(x))),
        "linear_log2_ratio_vs_D_over_m": linear,
        "intercept_only_deviance": null["deviance"],
        "pair_deviance_explained": explained,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path,
                    default=Path(__file__).parent / "results" / "pair_codegree_37")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "results" / "pair_codegree_37" /
                    "exact_small_pair_law.json")
    args = ap.parse_args()
    rows = [analyze(path) for path in sorted(args.dir.glob("exact_pair_counts_m*.txt"),
                                             key=lambda p: int(p.stem.rsplit("m", 1)[1]))]
    payload = {
        "definition": "exact labelled C4-NTIL solution spaces, no sampling",
        "results": rows,
        "warning": "very small solution counts make per-m slopes unstable",
    }
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for r in rows:
        law = r['linear_log2_ratio_vs_D_over_m']
        slope = f"{law['coefficients'][1]:.5f}" if law else "not-identifiable"
        dev = (f"{r['pair_deviance_explained']:.4f}"
               if r['pair_deviance_explained'] is not None else "not-identifiable")
        print(f"m={r['m']} N={r['exact_labelled_solutions']} "
              f"slope={slope} "
              f"dev.expl={dev}")


if __name__ == "__main__":
    main()
