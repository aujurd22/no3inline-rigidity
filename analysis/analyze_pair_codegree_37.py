#!/usr/bin/env python3
"""Second-order NTIL heatmap: pair co-selection after structural nulls.

For selected fundamental cells u,v, compare observed co-selection with the
product of their one-cell marginals.  The comparison is conditioned on:
  * u and v having disjoint 2-factor endpoints;
  * the two C4 orbits being directly compatible (no triple using only u,v).

Then fit and remove the empirical response to pair codegree
  D(u,v) = number of third-cell conflict mechanisms containing u and v.
If a displacement pattern survives, it is a candidate higher-order effect;
if it vanishes, pair codegree explains the apparent conditional pattern.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from build_volume_heatmap_37 import load_solutions


K = 10


def c4_orbit(cell: tuple[int, int], n: int):
    p = cell
    out = []
    for _ in range(4):
        out.append(p)
        p = (n - 1 - p[1], p[0])
    return out


def reduced_directions(n: int):
    out = set()
    for dx in range(-(n - 1), n):
        for dy in range(n):
            if dx == 0 and dy == 0:
                continue
            g = math.gcd(abs(dx), dy) or 1
            a, b = dx // g, dy // g
            if a < 0 or (a == 0 and b < 0):
                a, b = -a, -b
            out.add((a, b))
    return out


def pair_geometry(m: int):
    """Return line-multiplicity codegree and direct-incompatibility matrices."""
    n = 2 * m
    cells = [(x, y) for x in range(m) for y in range(m)]
    directions = reduced_directions(n)
    line_w = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for i, cell in enumerate(cells):
        for X, Y in c4_orbit(cell, n):
            for dx, dy in directions:
                line_w[(dx, dy)][-dy * X + dx * Y][i] += 1

    constraints = [dict(d) for lines in line_w.values() for d in lines.values()
                   if sum(d.values()) > 2]
    del line_w
    nc = m * m
    co3 = np.zeros((nc, nc), dtype=np.int32)
    bad = np.zeros((nc, nc), dtype=bool)
    for d in constraints:
        ids = np.fromiter(d.keys(), dtype=np.int32)
        weights = np.fromiter(d.values(), dtype=np.int16)
        L = len(ids)
        if L < 2:
            continue
        ii, jj = np.triu_indices(L, 1)
        a, b = ids[ii], ids[jj]
        direct = weights[ii] + weights[jj] > 2
        bad[a[direct], b[direct]] = True
        good = ~direct
        # For a compatible pair both line weights are one, so each other cell
        # on this line is a third-cell conflict mechanism.
        co3[a[good], b[good]] += L - 2
    co3 += co3.T
    bad |= bad.T
    return co3, bad, len(constraints)


def weighted_quantiles(values: np.ndarray, weights: np.ndarray, probs: np.ndarray):
    order = np.argsort(values, kind="mergesort")
    v, w = values[order], weights[order]
    cumulative = np.cumsum(w)
    if cumulative[-1] <= 0:
        return np.quantile(v, probs)
    return np.interp(probs * cumulative[-1], cumulative, v)


def displacement_bin(a: int, b: int, m: int):
    ax, ay = divmod(a, m)
    bx, by = divmod(b, m)
    dx, dy = sorted((abs(ax - bx) / (m - 1), abs(ay - by) / (m - 1)))
    return min(K - 1, int(dx * K)), min(K - 1, int(dy * K))


def analyze_m(m: int, solutions, strata: int = 12):
    started = time.time()
    nc = m * m
    cells = [(x, y) for x in range(m) for y in range(m)]
    co3, direct_bad, line_count = pair_geometry(m)

    N = len(solutions)
    marginal = np.zeros(nc, dtype=float)
    cooccur = np.zeros((nc, nc), dtype=np.int32)
    observed_disjoint_pairs = 0
    for sol in solutions:
        ids = [x * m + y for x, y in sol]
        # Exact transpose symmetry of the problem, not a statistical assumption.
        for a in ids:
            x, y = divmod(a, m)
            marginal[a] += 0.5
            marginal[y * m + x] += 0.5
        for a, b in combinations(ids, 2):
            ax, ay = cells[a]
            bx, by = cells[b]
            if {ax, ay}.isdisjoint({bx, by}):
                if direct_bad[a, b]:
                    raise AssertionError(f"observed solution contains directly bad pair at m={m}")
                cooccur[a, b] += 1
                cooccur[b, a] += 1
                observed_disjoint_pairs += 1
    marginal /= N

    pa, pb, bi, bj = [], [], [], []
    for a, u in enumerate(cells):
        for b in range(a + 1, nc):
            v = cells[b]
            if direct_bad[a, b] or not {u[0], u[1]}.isdisjoint({v[0], v[1]}):
                continue
            i, j = displacement_bin(a, b, m)
            pa.append(a); pb.append(b); bi.append(i); bj.append(j)
    pa = np.asarray(pa, dtype=np.int32)
    pb = np.asarray(pb, dtype=np.int32)
    bi = np.asarray(bi, dtype=np.int8)
    bj = np.asarray(bj, dtype=np.int8)
    base = N * marginal[pa] * marginal[pb]
    obs = cooccur[pa, pb].astype(float)
    danger = co3[pa, pb].astype(float)

    # Equal expected-mass codegree strata keep sparse extreme codegrees visible.
    edges = weighted_quantiles(danger, np.maximum(base, 1e-12), np.linspace(0, 1, strata + 1))
    edges = np.unique(edges)
    if len(edges) < 4:
        raise RuntimeError(f"too few distinct codegree strata for m={m}")
    qbin = np.searchsorted(edges, danger, side="right") - 1
    qbin = np.clip(qbin, 0, len(edges) - 2)
    response = np.ones(len(edges) - 1, dtype=float)
    qrows = []
    for q in range(len(response)):
        mask = qbin == q
        o, e = float(obs[mask].sum()), float(base[mask].sum())
        response[q] = (o + 10.0) / (e + 10.0)
        qrows.append({
            "lo": float(edges[q]), "hi": float(edges[q + 1]),
            "mean_codegree": float(np.average(danger[mask], weights=np.maximum(base[mask], 1e-12))),
            "observed_pairs": o, "independent_expected": e,
            "co_selection_ratio": float(response[q]),
        })
    adjusted = base * response[qbin]
    adjusted *= obs.sum() / adjusted.sum()

    H = np.zeros((K, K), dtype=float)
    H0 = np.zeros_like(H)
    H1 = np.zeros_like(H)
    for k in range(len(pa)):
        i, j = int(bi[k]), int(bj[k])
        H[i, j] += obs[k]
        H0[i, j] += base[k]
        H1[i, j] += adjusted[k]
    H0 *= H.sum() / H0.sum()
    H1 *= H.sum() / H1.sum()
    raw = np.log2((H + 10.0) / (H0 + 10.0))
    residual = np.log2((H + 10.0) / (H1 + 10.0))
    valid_bins = H1 > 100
    raw_rms = float(np.sqrt(np.mean(raw[valid_bins] ** 2)))
    residual_rms = float(np.sqrt(np.mean(residual[valid_bins] ** 2)))

    # A compact monotonic-law fit.  The x coordinate D/m makes scales comparable.
    xs = np.array([r["mean_codegree"] / m for r in qrows])
    ys = np.log2(np.array([r["co_selection_ratio"] for r in qrows]))
    fit = np.stack([np.ones(len(xs)), xs], axis=1)
    beta, *_ = np.linalg.lstsq(fit, ys, rcond=None)
    pred = fit @ beta
    ss = float(np.sum((ys - ys.mean()) ** 2))
    fit_r2 = 1.0 - float(np.sum((ys - pred) ** 2)) / ss if ss else 1.0

    return {
        "m": m, "solutions": N, "line_constraints": line_count,
        "candidate_pairs_after_conditioning": int(len(pa)),
        "observed_disjoint_pairs": observed_disjoint_pairs,
        "directly_bad_pairs": int(np.triu(direct_bad, 1).sum()),
        "codegree_strata": qrows,
        "codegree_law": {"formula": "log2 ratio = intercept + slope * (D/m)",
                           "intercept": float(beta[0]), "slope": float(beta[1]), "r2": fit_r2},
        "raw_log2_ratio": raw.tolist(),
        "codegree_adjusted_log2_residual": residual.tolist(),
        "raw_rms_log2": raw_rms, "adjusted_rms_log2": residual_rms,
        "rms_fraction_remaining": residual_rms / raw_rms if raw_rms else 0.0,
        "raw_diagonal": np.diag(raw).tolist(),
        "adjusted_diagonal": np.diag(residual).tolist(),
        "seconds": time.time() - started,
    }


def corr_upper(a: np.ndarray, b: np.ndarray):
    mask = np.triu(np.ones_like(a, dtype=bool))
    x, y = a[mask], b[mask]
    return float(np.corrcoef(x, y)[0, 1])


def color(v: float, limit: float):
    t = max(-1.0, min(1.0, v / limit))
    if t >= 0:
        return 225, int(238 - 155 * t), int(238 - 190 * t)
    t = -t
    return int(238 - 185 * t), int(240 - 125 * t), 230


def tile(a: np.ndarray, title: str, size=205, limit=0.65):
    im = Image.new("RGB", (size, size + 35), "white")
    d = ImageDraw.Draw(im)
    c = size / K
    for i in range(K):
        for j in range(K):
            d.rectangle((round(i*c), round((K-1-j)*c), round((i+1)*c), round((K-j)*c)),
                        fill=color(float(a[i, j]), limit))
    d.line((0, size, size, 0), fill=(30, 30, 30), width=1)
    d.text((5, size + 10), title, fill=(20, 20, 20))
    return im


def make_figure(path: Path, rows: list[dict]):
    if len(rows) > 6:
        pick = np.linspace(0, len(rows) - 1, 6).round().astype(int)
        rows = [rows[i] for i in pick]
    W, H = 1510, 720
    im = Image.new("RGB", (W, H), (248, 249, 251))
    d = ImageDraw.Draw(im)
    d.text((25, 18), "Second-order NTIL heatmap: displacement pair effect", fill=(15, 20, 30))
    d.text((25, 41), "top: after one-cell marginals + direct compatibility; bottom: after pair-codegree correction",
           fill=(60, 65, 75))
    for col, row in enumerate(rows):
        x = 25 + col * 245
        raw = tile(np.array(row["raw_log2_ratio"]), f"m={row['m']} raw", limit=.65)
        adj = tile(np.array(row["codegree_adjusted_log2_residual"]),
                   f"m={row['m']} adjusted", limit=.25)
        im.paste(raw, (x, 80)); im.paste(adj, (x, 350))
        d.text((x, 604), f"RMS: {row['raw_rms_log2']:.3f} -> {row['adjusted_rms_log2']:.3f}",
               fill=(45, 50, 60))
        d.text((x, 624), f"remain {100*row['rms_fraction_remaining']:.0f}%", fill=(45, 50, 60))
    d.text((25, 680), "Bins: min(|dx|,|dy|) horizontally; max(|dx|,|dy|) vertically. Dashed visual diagonal = |dx|=|dy|.",
           fill=(65, 70, 80))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, nargs="+", default=list(range(18, 29)))
    ap.add_argument("--cache", type=Path, default=Path(__file__).with_name("flammenkamp_cache"))
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "pair_codegree_37")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    by_m, *_ = load_solutions(args.cache)
    existing = {}
    for candidate in (() if args.force else (args.out / "pair_codegree_partial.json",
                                             args.out / "pair_codegree_summary.json")):
        if candidate.exists():
            try:
                old = json.loads(candidate.read_text(encoding="utf-8"))
                for row in old.get("per_m", []):
                    existing[int(row["m"])] = row
            except (OSError, ValueError, KeyError):
                pass
    rows = []
    for m in args.m:
        if m in existing:
            row = existing[m]
            print(f"[m={m}] reuse cached row", flush=True)
        else:
            print(f"[m={m}] start ({len(by_m.get(m, []))} solutions)", flush=True)
            row = analyze_m(m, by_m[m])
        rows.append(row)
        print(f"[m={m}] RMS {row['raw_rms_log2']:.4f} -> {row['adjusted_rms_log2']:.4f} "
              f"in {row['seconds']:.1f}s", flush=True)
        (args.out / "pair_codegree_partial.json").write_text(
            json.dumps({"per_m": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    raw = [np.array(r["raw_log2_ratio"]) for r in rows]
    adjusted = [np.array(r["codegree_adjusted_log2_residual"]) for r in rows]
    raw_corr = [corr_upper(raw[i], raw[j]) for i in range(len(raw)) for j in range(i+1, len(raw))]
    adj_corr = [corr_upper(adjusted[i], adjusted[j]) for i in range(len(adjusted))
                for j in range(i+1, len(adjusted))]
    slopes = [r["codegree_law"]["slope"] for r in rows]
    summary = {
        "definition": {
            "raw": "log2 observed pair count / independent marginal expectation, conditioned on disjoint endpoints and direct pair compatibility",
            "adjusted": "raw effect after fitting codegree-stratum response",
            "codegree": "line-multiplicity count of third-cell conflict mechanisms D(u,v)",
            "displacement_bins": "sorted normalized (|dx|,|dy|), 10 x 10",
        },
        "per_m": rows,
        "cross_m": {
            "raw_pairwise_correlation_median": float(np.median(raw_corr)),
            "adjusted_pairwise_correlation_median": float(np.median(adj_corr)),
            "median_rms_fraction_remaining": float(np.median([r["rms_fraction_remaining"] for r in rows])),
            "codegree_slope_mean": float(np.mean(slopes)),
            "codegree_slope_std": float(np.std(slopes)),
            "mean_raw_map": np.mean(raw, axis=0).tolist(),
            "mean_adjusted_map": np.mean(adjusted, axis=0).tolist(),
        },
    }
    (args.out / "pair_codegree_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "pair_codegree_partial.json").unlink(missing_ok=True)
    np.savez_compressed(args.out / "pair_codegree_volume.npz",
                        ms=np.array(args.m), raw=np.stack(raw), adjusted=np.stack(adjusted))
    make_figure(args.out / "pair_codegree_heatmap.png", rows)
    print(json.dumps(summary["cross_m"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
