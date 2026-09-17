"""NumPy-only comparison of the exact Ising matrices produced by the core."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def gini(values):
    x = np.sort(np.asarray(values, dtype=float))
    if x.size == 0 or x.sum() == 0:
        return 0.0
    n = x.size
    return float((2 * np.dot(np.arange(1, n + 1), x) / (n * x.sum())) - (n + 1) / n)


def analyze(case):
    j = np.asarray(case["j_matrix"], dtype=float)
    n = len(j)
    a = j / 2.0  # s^T A s = sum_{i<j} J_ij s_i s_j
    eig = np.linalg.eigvalsh(a)
    pairs = case["complement_pairs"]
    chosen = case.get("exact", {}).get("bits")
    source = "exact"
    if chosen is None:
        chosen = case.get("supplied", {}).get("bits")
        source = "supplied"
    if chosen is None:
        raise ValueError(f"no orientation for {case['name']}")
    s = np.where(np.asarray(chosen) == 0, 1.0, -1.0)
    switched = j * np.outer(s, s)
    row_sums = switched.sum(axis=1)
    energy = float(sum(switched[i, k] for i in range(n) for k in range(i + 1, n)))
    value = (pairs + energy) / 4.0
    abs_degrees = np.abs(j).sum(axis=1)

    weights = [j[i, k] for i in range(n) for k in range(i + 1, n) if j[i, k] != 0]
    abs_sum = float(sum(abs(w) for w in weights))
    frustration_weight = (energy + abs_sum) / 2.0

    inconsistent_triangles = 0
    weighted_inconsistent = 0.0
    supported_triangles = 0
    for i in range(n):
        for k in range(i + 1, n):
            if not j[i, k]:
                continue
            for q in range(k + 1, n):
                if not j[i, q] or not j[k, q]:
                    continue
                supported_triangles += 1
                # Each J edge prefers product -sign(J). A cycle is inconsistent
                # when the product of preferred edge products is -1.
                pref_product = (-np.sign(j[i, k])) * (-np.sign(j[i, q])) * (-np.sign(j[k, q]))
                if pref_product < 0:
                    inconsistent_triangles += 1
                    weighted_inconsistent += min(abs(j[i, k]), abs(j[i, q]), abs(j[k, q]))

    spectral_real = pairs / 4.0 + n * eig[0] / 4.0
    return {
        "n": n,
        "orientation_source": source,
        "violations": value,
        "pair_energy": energy,
        "zero_target_energy": -pairs,
        "energy_gap_to_zero": energy + pairs,
        "lambda_min_A": float(eig[0]),
        "lambda_max_A": float(eig[-1]),
        "matrix_rank": int(np.linalg.matrix_rank(a, tol=1e-9)),
        "spectral_lower_bound_real": spectral_real,
        "spectral_lower_bound_integer": math.ceil(spectral_real - 1e-9),
        "abs_coupling_degree_min": float(abs_degrees.min()),
        "abs_coupling_degree_max": float(abs_degrees.max()),
        "abs_coupling_degree_mean": float(abs_degrees.mean()),
        "abs_coupling_degree_cv": float(abs_degrees.std() / abs_degrees.mean()),
        "abs_coupling_degree_gini": gini(abs_degrees),
        "switched_row_sum_min": float(row_sums.min()),
        "switched_row_sum_max": float(row_sums.max()),
        "switched_row_sum_mean": float(row_sums.mean()),
        "single_flip_stable": bool(np.all(row_sums <= 1e-9)),
        "pairwise_relaxation_lb": pairs / 4.0 - abs_sum / 4.0,
        "pairwise_frustration_weight": frustration_weight,
        "supported_signed_triangles": supported_triangles,
        "inconsistent_signed_triangles": inconsistent_triangles,
        "inconsistent_triangle_fraction": inconsistent_triangles / max(1, supported_triangles),
        "weighted_inconsistent_triangles": weighted_inconsistent,
        "lowest_eigenvalues": [float(x) for x in eig[:8]],
    }


def main():
    source = OUT / "signed_nae_results.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    analyses = {case["name"]: analyze(case) for case in data["cases"]}
    (OUT / "spectral_results.json").write_text(
        json.dumps(analyses, indent=2), encoding="utf-8"
    )

    lines = [
        "# Independent signed-NAE / Ising findings",
        "",
        "The orientation formula was rebuilt from integer geometry. Each complementary",
        "forbidden pair contributes a signed NAE term and all odd Fourier degrees cancel.",
        "",
        "| case | clauses | pairs | optimum V | energy gap to zero | spectral LB | coupling CV | inconsistent triangles |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    by_name = {case["name"]: case for case in data["cases"]}
    for name, item in analyses.items():
        raw = by_name[name]
        lines.append(
            f"| {name} | {raw['clauses']} | {raw['complement_pairs']} | "
            f"{item['violations']:.0f} | {item['energy_gap_to_zero']:.0f} | "
            f"{item['spectral_lower_bound_real']:.2f} | "
            f"{item['abs_coupling_degree_cv']:.3f} | "
            f"{item['inconsistent_signed_triangles']}/{item['supported_signed_triangles']} |"
        )

    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- Clause count is not an existence surrogate: the m=36 solution can have more",
        "  clauses while its signed Ising system reaches exactly zero.",
        "- A positive instance-specific optimum is not a universal m=37 lower bound.",
        "- Spectral and pairwise relaxations are certificates only at their reported",
        "  values; they may be too weak to prove the integer optimum.",
        "- The useful object for a general theorem is the switching class of J(E), not",
        "  the raw hot-edge or span histogram.",
        "",
    ]
    (OUT / "research_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(OUT / "research_report.md")


if __name__ == "__main__":
    main()

