#!/usr/bin/env python3
"""Test whether the pair survival law is a configuration-model Poisson law.

For a compatible, endpoint-disjoint pair u,v, construct the set F_uv of
distinct third cells that would complete at least one C4 collinearity.  After
fixing u,v, the residual degree sequence has 2m-4 stubs.  The configuration
model first-moment mass of the danger set is

  mu(u,v) = sum_{w=(x,y) in F_uv} stub_weight(w)/(2m-5),

where stub_weight is r_x*r_y/2 for an oriented non-loop and C(r_x,2) for a
loop.  If danger hits are approximately Poisson, pair survival should be
proportional to exp(-mu), i.e. have log2 slope -1/ln(2).
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

from build_volume_heatmap_37 import load_solutions
from analyze_pair_codegree_37 import weighted_quantiles


def c4_orbit(cell, n):
    p = cell
    out = []
    for _ in range(4):
        out.append(p)
        p = (n - 1 - p[1], p[0])
    return out


def reduced_directions(n):
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


def geometry(m):
    n = 2 * m
    cells = [(x, y) for x in range(m) for y in range(m)]
    line_w = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    directions = reduced_directions(n)
    for i, cell in enumerate(cells):
        for X, Y in c4_orbit(cell, n):
            for dx, dy in directions:
                line_w[(dx, dy)][-dy * X + dx * Y][i] += 1
    constraints = [dict(d) for lines in line_w.values() for d in lines.values()
                   if sum(d.values()) > 2]
    del line_w

    nc = m * m
    co3 = np.zeros((nc, nc), dtype=np.int32)
    direct_bad = np.zeros((nc, nc), dtype=bool)
    incidence = [[] for _ in range(nc)]
    for line_no, d in enumerate(constraints):
        ids = np.fromiter(d.keys(), dtype=np.int32)
        weights = np.fromiter(d.values(), dtype=np.int16)
        for a in ids:
            incidence[int(a)].append(line_no)
        if len(ids) < 2:
            continue
        ii, jj = np.triu_indices(len(ids), 1)
        a, b = ids[ii], ids[jj]
        bad = weights[ii] + weights[jj] > 2
        direct_bad[a[bad], b[bad]] = True
        good = ~bad
        co3[a[good], b[good]] += len(ids) - 2
    co3 += co3.T
    direct_bad |= direct_bad.T
    return cells, constraints, incidence, co3, direct_bad


def danger_set(a, b, constraints, incidence):
    """Distinct third cells sharing a violating line with compatible pair a,b."""
    first, second = (a, b) if len(incidence[a]) <= len(incidence[b]) else (b, a)
    other_lines = set(incidence[second])
    danger = set()
    for line_no in incidence[first]:
        if line_no not in other_lines:
            continue
        d = constraints[line_no]
        if d[a] + d[b] <= 2:
            danger.update(k for k in d if k != a and k != b)
    return danger


def residual_degrees(pair, cells, m):
    degree = np.full(m, 2, dtype=np.int8)
    for index in pair:
        x, y = cells[index]
        if x == y:
            degree[x] -= 2
        else:
            degree[x] -= 1
            degree[y] -= 1
    if np.any(degree < 0) or int(degree.sum()) != 2 * m - 4:
        raise AssertionError("pair does not leave the expected residual degree sequence")
    return degree


def danger_features(a, b, danger, cells, m):
    residual = residual_degrees((a, b), cells, m)
    denominator = 2 * m - 5
    mass = 0.0
    eligible = 0
    touched = set()
    danger_degrees = np.zeros(m, dtype=np.int16)
    for w in danger:
        x, y = cells[w]
        if x == y:
            weight = residual[x] * (residual[x] - 1) / 2.0
        else:
            weight = residual[x] * residual[y] / 2.0
        if weight > 0:
            eligible += 1
            mass += weight / denominator
            touched.update((x, y))
            danger_degrees[x] += 1
            danger_degrees[y] += 1
    concentration = (float(np.dot(danger_degrees, danger_degrees)) /
                     max(1.0, float(danger_degrees.sum()) ** 2))
    wedges = int(np.sum(danger_degrees * (danger_degrees - 1) // 2))
    return {
        "U": len(danger), "eligible_U": eligible, "mu": mass,
        "vertices_touched": len(touched), "concentration": concentration,
        "max_danger_degree": int(danger_degrees.max()), "danger_wedges": wedges,
    }


def aggregate_law(rows, feature, bins=12):
    x = np.asarray([r[feature] for r in rows], dtype=float)
    base_weight = np.asarray([r["base"] * r["inverse_sampling"] for r in rows])
    observed = np.asarray([r["observed"] * r["inverse_sampling"] for r in rows])
    expected = base_weight
    edges = np.unique(weighted_quantiles(x, np.maximum(expected, 1e-12),
                                         np.linspace(0, 1, bins + 1)))
    group = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2)
    points = []
    for q in range(len(edges) - 1):
        mask = group == q
        o, e = observed[mask].sum(), expected[mask].sum()
        points.append({
            "lo": float(edges[q]), "hi": float(edges[q + 1]),
            "x": float(np.average(x[mask], weights=np.maximum(expected[mask], 1e-12))),
            "ratio": float((o + 10.0) / (e + 10.0)),
            "observed": float(o), "expected": float(e), "sample_pairs": int(mask.sum()),
        })
    xx = np.asarray([p["x"] for p in points])
    yy = np.log2(np.asarray([p["ratio"] for p in points]))
    X = np.stack([np.ones(len(xx)), xx], axis=1)
    beta, *_ = np.linalg.lstsq(X, yy, rcond=None)
    pred = X @ beta
    ss = float(np.sum((yy - yy.mean()) ** 2))
    r2 = 1.0 - float(np.sum((yy - pred) ** 2)) / ss if ss else 1.0
    return {"feature": feature, "intercept": float(beta[0]), "slope": float(beta[1]),
            "r2": r2, "points": points}


def conditional_quintiles(rows, feature):
    """Feature response after removing the 12 sampled codegree strata."""
    n = len(rows)
    strata = np.asarray([r["stratum"] for r in rows], dtype=int)
    obs = np.asarray([r["observed"] * r["inverse_sampling"] for r in rows], dtype=float)
    base = np.asarray([r["base"] * r["inverse_sampling"] for r in rows], dtype=float)
    values = np.asarray([r[feature] for r in rows], dtype=float)
    expected = base.copy()
    relative_rank = np.zeros(n, dtype=float)
    for q in np.unique(strata):
        mask = strata == q
        expected[mask] *= (obs[mask].sum() + 10.0) / (base[mask].sum() + 10.0)
        ids = np.flatnonzero(mask)
        order = ids[np.argsort(values[ids], kind="mergesort")]
        relative_rank[order] = (np.arange(len(order)) + 0.5) / len(order)
    expected *= obs.sum() / expected.sum()
    points = []
    for q in range(5):
        mask = (relative_rank >= q / 5) & (relative_rank < (q + 1) / 5)
        o, e = obs[mask].sum(), expected[mask].sum()
        points.append({
            "relative_quintile": q + 1,
            "mean_feature": float(np.average(values[mask], weights=np.maximum(base[mask], 1e-12))),
            "residual_ratio": float((o + 10.0) / (e + 10.0)),
            "sample_pairs": int(mask.sum()),
        })
    x = np.arange(1, 6, dtype=float)
    y = np.log2(np.asarray([p["residual_ratio"] for p in points]))
    slope = float(np.polyfit(x, y, 1)[0])
    return {"feature": feature, "log2_slope_per_quintile": slope, "points": points}


def poisson_potential_fit(rows, features):
    """Stratified-sample Poisson fit with log2 pair ratio as linear potential."""
    X = np.column_stack([
        np.ones(len(rows), dtype=float),
        *[np.asarray([r[name] for r in rows], dtype=float) for name in features],
    ])
    inverse = np.asarray([r["inverse_sampling"] for r in rows], dtype=float)
    observed = np.asarray([r["observed"] for r in rows], dtype=float) * inverse
    base = np.asarray([r["base"] for r in rows], dtype=float) * inverse
    beta = np.zeros(X.shape[1], dtype=float)
    ln2 = math.log(2.0)
    for _ in range(60):
        eta = np.clip(ln2 * (X @ beta), -30.0, 30.0)
        mean = np.maximum(base, 1e-12) * np.exp(eta)
        gradient = ln2 * (X.T @ (observed - mean))
        hessian = ln2 * ln2 * (X.T @ (mean[:, None] * X))
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step, *_ = np.linalg.lstsq(hessian, gradient, rcond=None)
        beta += step
        if float(np.max(np.abs(step))) < 1e-10:
            break
    eta = np.clip(ln2 * (X @ beta), -30.0, 30.0)
    mean = np.maximum(base, 1e-12) * np.exp(eta)
    null_mean = base * (observed.sum() / max(base.sum(), 1e-12))
    # Poisson deviance, with the y log(y/mu) term defined as zero at y=0.
    def deviance(mu):
        positive = observed > 0
        term = mu - observed
        term[positive] += observed[positive] * np.log(observed[positive] / mu[positive])
        return 2.0 * float(term.sum())
    null_dev = deviance(np.maximum(null_mean, 1e-12))
    fitted_dev = deviance(np.maximum(mean, 1e-12))
    return {
        "formula": "log2(observed/independent) = intercept + " +
                   " + ".join(f"beta_{name}*{name}" for name in features),
        "features": list(features), "intercept": float(beta[0]),
        "coefficients": {name: float(value) for name, value in zip(features, beta[1:])},
        "poisson_deviance_explained": 1.0 - fitted_dev / null_dev if null_dev else 0.0,
        "fitted_deviance": fitted_dev, "null_deviance": null_dev,
    }


def configuration_survival(a, b, danger, cells, m, draws, rng):
    """Monte Carlo survival in the residual configuration model, simple cells only."""
    residual = residual_degrees((a, b), cells, m)
    stubs = np.repeat(np.arange(m, dtype=np.int16), residual)
    selected = {a, b}
    survived = valid = attempts = 0
    max_attempts = max(10_000, draws * 20)
    while valid < draws and attempts < max_attempts:
        attempts += 1
        shuffled = rng.permutation(stubs)
        made = set()
        hit = False
        duplicate = False
        for k in range(0, len(shuffled), 2):
            x, y = int(shuffled[k]), int(shuffled[k + 1])
            if x != y and rng.integers(2):
                x, y = y, x
            w = x * m + y
            if w in selected or w in made:
                duplicate = True
                break
            made.add(w)
            if w in danger:
                hit = True
        if duplicate:
            continue
        valid += 1
        survived += not hit
    if valid < draws:
        raise RuntimeError(f"configuration sampler accepted only {valid}/{draws}")
    return survived, valid, attempts


def analyze(m, solutions, samples_per_stratum, seed, sim_pairs=0, sim_draws=0):
    started = time.time()
    cells, constraints, incidence, co3, bad = geometry(m)
    nc, N = m * m, len(solutions)
    marginal = np.zeros(nc, dtype=float)
    cooccur = np.zeros((nc, nc), dtype=np.int32)
    for sol in solutions:
        ids = [x * m + y for x, y in sol]
        for a in ids:
            x, y = divmod(a, m)
            marginal[a] += 0.5
            marginal[y * m + x] += 0.5
        for a, b in combinations(ids, 2):
            cooccur[a, b] += 1
            cooccur[b, a] += 1
    marginal /= N

    pairs = []
    for a, u in enumerate(cells):
        for b in range(a + 1, nc):
            v = cells[b]
            if not bad[a, b] and {u[0], u[1]}.isdisjoint({v[0], v[1]}):
                pairs.append((a, b))
    D = np.asarray([co3[a, b] for a, b in pairs])
    base = np.asarray([N * marginal[a] * marginal[b] for a, b in pairs])
    edges = np.unique(weighted_quantiles(D, np.maximum(base, 1e-12), np.linspace(0, 1, 13)))
    strata = np.clip(np.searchsorted(edges, D, side="right") - 1, 0, len(edges) - 2)
    rng = np.random.default_rng(seed + m)
    chosen = []
    for q in range(len(edges) - 1):
        ids = np.flatnonzero(strata == q)
        take = rng.choice(ids, size=min(samples_per_stratum, len(ids)), replace=False)
        inverse = len(ids) / len(take)
        chosen.extend((int(k), q, inverse) for k in take)

    rows = []
    for number, (index, stratum, inverse) in enumerate(chosen, 1):
        a, b = pairs[index]
        danger = danger_set(a, b, constraints, incidence)
        f = danger_features(a, b, danger, cells, m)
        if f["U"] and abs(D[index] / f["U"] - 4.0) > 4.0:
            raise AssertionError("unexpectedly large line-orbit multiplicity")
        ax, ay = cells[a]; bx, by = cells[b]
        f.update({
            "a": a, "b": b, "D": int(D[index]), "U_over_m": f["U"] / m,
            "observed": int(cooccur[a, b]), "base": float(base[index]),
            "inverse_sampling": float(inverse), "stratum": int(stratum),
            "diagonal_displacement": abs(abs(ax - bx) - abs(ay - by)) / (m - 1),
            "touch_fraction": f["vertices_touched"] / m,
            "eligible_fraction": f["eligible_U"] / max(1, f["U"]),
            "max_degree_fraction": f["max_danger_degree"] / max(1, f["U"]),
            "wedge_over_m2": f["danger_wedges"] / (m * m),
        })
        rows.append(f)

    laws = {name: aggregate_law(rows, name) for name in ("U_over_m", "mu")}
    ratios = [r["D"] / r["U"] for r in rows if r["U"]]
    result = {
        "m": m, "solutions": N, "sample_pairs": len(rows),
        "multiplicity_D_over_U": {"mean": float(np.mean(ratios)),
                                   "median": float(np.median(ratios)),
                                   "q10": float(np.quantile(ratios, .1)),
                                   "q90": float(np.quantile(ratios, .9))},
        "laws": laws,
        "poisson_target_log2_slope": -1.0 / math.log(2.0),
        "mu_over_U_over_m_mean": float(np.mean([r["mu"] / r["U_over_m"]
                                                 for r in rows if r["U_over_m"] > 0])),
        "conditional_shape_effects": {
            name: conditional_quintiles(rows, name)
            for name in ("touch_fraction", "concentration", "eligible_fraction",
                         "max_degree_fraction", "wedge_over_m2",
                         "diagonal_displacement")
        },
        "pair_potential_fits": {
            "first_order": poisson_potential_fit(rows, ("U_over_m",)),
            "with_wedges": poisson_potential_fit(rows, ("U_over_m", "wedge_over_m2")),
            "with_touch": poisson_potential_fit(rows, ("U_over_m", "touch_fraction")),
            "with_concentration": poisson_potential_fit(
                rows, ("U_over_m", "concentration")),
            "with_max_degree": poisson_potential_fit(
                rows, ("U_over_m", "max_degree_fraction")),
            "with_coverage": poisson_potential_fit(
                rows, ("U_over_m", "wedge_over_m2", "touch_fraction")),
        },
        "seconds": time.time() - started,
    }
    if sim_pairs and sim_draws:
        # Cover the full mu range instead of drawing mostly from its dense centre.
        order = np.argsort([r["mu"] for r in rows])
        positions = np.linspace(0, len(order) - 1, sim_pairs).round().astype(int)
        sim = []
        sim_rng = np.random.default_rng(seed + 1000 + m)
        for position in positions:
            r = rows[int(order[position])]
            danger = danger_set(r["a"], r["b"], constraints, incidence)
            survived, valid, attempts = configuration_survival(
                r["a"], r["b"], danger, cells, m, sim_draws, sim_rng)
            sim.append({"mu": r["mu"], "U_over_m": r["U_over_m"],
                        "survived": survived, "valid": valid, "attempts": attempts,
                        "survival": (survived + 0.5) / (valid + 1.0)})
        x = np.asarray([r["mu"] for r in sim])
        y = np.log2(np.asarray([r["survival"] for r in sim]))
        X = np.stack([np.ones(len(x)), x], axis=1)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = X @ beta
        ss = float(np.sum((y - y.mean()) ** 2))
        result["configuration_model_simulation"] = {
            "pairs": sim_pairs, "draws_per_pair": sim_draws,
            "intercept": float(beta[0]), "slope_log2_per_mu": float(beta[1]),
            "r2": 1.0 - float(np.sum((y - pred) ** 2)) / ss if ss else 1.0,
            "poisson_target": -1.0 / math.log(2.0), "samples": sim,
        }
    result["seconds"] = time.time() - started
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, nargs="+", default=[20, 24, 28])
    ap.add_argument("--samples-per-stratum", type=int, default=300)
    ap.add_argument("--config-sim-pairs", type=int, default=0)
    ap.add_argument("--config-sim-draws", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20260721)
    ap.add_argument("--cache", type=Path, default=Path(__file__).with_name("flammenkamp_cache"))
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" /
                    "pair_codegree_37" / "danger_mass_summary.json")
    args = ap.parse_args()
    by_m, *_ = load_solutions(args.cache)
    results = []
    for m in args.m:
        print(f"[m={m}] configuration danger mass", flush=True)
        row = analyze(m, by_m[m], args.samples_per_stratum, args.seed,
                      args.config_sim_pairs, args.config_sim_draws)
        results.append(row)
        print(f"  U/m slope={row['laws']['U_over_m']['slope']:.5f}; "
              f"mu slope={row['laws']['mu']['slope']:.5f}; "
              f"target={row['poisson_target_log2_slope']:.5f}; "
              f"R2(mu)={row['laws']['mu']['r2']:.4f}", flush=True)
        if "configuration_model_simulation" in row:
            sim = row["configuration_model_simulation"]
            print(f"  config simulation slope={sim['slope_log2_per_mu']:.5f}; "
                  f"R2={sim['r2']:.4f}", flush=True)
    payload = {
        "definition": "configuration-model danger mass test",
        "results": results,
        "cross_m": {
            "mu_slope_mean": float(np.mean([r["laws"]["mu"]["slope"] for r in results])),
            "mu_slope_std": float(np.std([r["laws"]["mu"]["slope"] for r in results])),
            "U_slope_mean": float(np.mean([r["laws"]["U_over_m"]["slope"] for r in results])),
            "poisson_target": -1.0 / math.log(2.0),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["cross_m"], indent=2))


if __name__ == "__main__":
    main()
