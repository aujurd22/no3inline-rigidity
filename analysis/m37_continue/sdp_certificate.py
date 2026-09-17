"""Compute the standard MaxCut SDP and its diagonal-loading dual certificate."""

from __future__ import annotations

import json
from pathlib import Path

import cvxpy as cp
import numpy as np


HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


def solve_case(case):
    j = np.asarray(case["j_matrix"], dtype=float)
    n = len(j)
    a = j / 2.0
    pairs = case["complement_pairs"]

    # Dual of min <A,X>, diag(X)=1, X>=0:
    # max sum(d), A-diag(d)>=0.
    d = cp.Variable(n)
    constraint = a - cp.diag(d) >> 0
    problem = cp.Problem(cp.Maximize(cp.sum(d)), [constraint])
    value = problem.solve(
        solver="CLARABEL",
        tol_gap_abs=1e-9,
        tol_feas=1e-9,
        tol_gap_rel=1e-9,
        max_iter=1000,
    )
    dval = np.asarray(d.value, dtype=float)
    slack = a - np.diag(dval)
    min_slack_eig = float(np.linalg.eigvalsh(slack)[0])
    violation_lb = pairs / 4.0 + value / 4.0
    return {
        "status": problem.status,
        "dual_energy_lb": float(value),
        "violation_lb": float(violation_lb),
        # CLARABEL's dual certificate can sit a few 1e-7 above an exact
        # integer at numerical optimum (the m=36 zero case is the canary).
        # Round only for the displayed integer consequence; retain the raw
        # floating-point bound and PSD slack above for auditing.
        "integer_violation_lb": int(np.ceil(violation_lb - 1e-5)),
        "min_psd_slack_eigenvalue": min_slack_eig,
        "diagonal_certificate": [float(x) for x in dval],
    }


def main():
    data = json.loads((OUT / "signed_nae_results.json").read_text(encoding="utf-8"))
    results = {}
    for case in data["cases"]:
        print(f"SDP {case['name']} ...", flush=True)
        results[case["name"]] = solve_case(case)
        print(results[case["name"]], flush=True)
    (OUT / "sdp_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
