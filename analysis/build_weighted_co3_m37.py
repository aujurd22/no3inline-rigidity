#!/usr/bin/env python3
"""Build the full m=37 heatmap-weighted third-cell pair matrix.

For compatible oriented cells a,b and every line constraint containing them,
add the projected one-cell enrichment of each possible dangerous third cell.
Directly incompatible pairs are recorded separately.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import numpy as np


M = 37


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--constraints", type=Path, default=here / "line_cons_m37.pkl")
    ap.add_argument("--volume", type=Path, default=here / "results" /
                    "volume_heatmap_37" / "ntil_volume_37.npz")
    ap.add_argument("--out", type=Path, default=here / "weighted_co3_m37.npy")
    ap.add_argument("--bad-out", type=Path, default=here / "direct_bad_m37.npy")
    ap.add_argument("--summary", type=Path, default=here / "results" /
                    "pair_codegree_37" / "weighted_co3_build.json")
    args = ap.parse_args()
    began = time.time()
    with args.constraints.open("rb") as f:
        constraints, _ = pickle.load(f)
    enrich = np.load(args.volume)["prediction_m37"].reshape(-1).astype(float)
    enrich /= enrich.mean()
    nc = M * M
    weighted = np.zeros((nc, nc), dtype=np.float32)
    direct_bad = np.zeros((nc, nc), dtype=bool)
    compatible_pair_updates = 0
    direct_pair_updates = 0
    for number, d in enumerate(constraints, 1):
        ids = list(d)
        mass = float(enrich[ids].sum())
        for i, a in enumerate(ids):
            wa = d[a]
            for b in ids[i + 1:]:
                if wa + d[b] > 2:
                    direct_bad[a, b] = direct_bad[b, a] = True
                    direct_pair_updates += 1
                else:
                    value = mass - enrich[a] - enrich[b]
                    weighted[a, b] += value
                    weighted[b, a] += value
                    compatible_pair_updates += 1
        if number % 250_000 == 0:
            print(f"  {number}/{len(constraints)} constraints, {time.time()-began:.1f}s",
                  flush=True)
    np.save(args.out, weighted)
    np.save(args.bad_out, direct_bad)
    payload = {
        "definition": "sum projected m37 enrichment over third-cell line mechanisms",
        "constraints": len(constraints),
        "compatible_pair_updates": compatible_pair_updates,
        "direct_pair_updates": direct_pair_updates,
        "distinct_direct_bad_pairs": int(np.triu(direct_bad, 1).sum()),
        "weighted_min": float(weighted.min()), "weighted_max": float(weighted.max()),
        "weighted_nonzero_pairs": int(np.triu(weighted != 0, 1).sum()),
        "seconds": time.time() - began,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
