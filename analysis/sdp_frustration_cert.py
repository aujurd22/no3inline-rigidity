"""
sdp_frustration_cert.py — Rigorous SDP lower bound on min_violations via the
signed MAX-CUT SDP (Goemans-Williamson relaxation, dual = lower bound).

For a fixed 2-factor with Ising coupling J (over all clauses):
    E_min = min_s Σ_{i<j} J_{ij} s_i s_j = Σ|J| - 4 M*,
where M* = signed MAX-CUT optimum:
    M* = max_s Σ_{i<j} |J_{ij}| (1 - sign(J_{ij}) s_i s_j)/4 .
The GW SDP relaxation (V PSD, diag=1, maximize same objective) has optimum M_SDP ≥ M*,
so a rigorous lower bound on min_violations is
    min_viol ≥ n_clauses/8 + Σ|J|/8 - M_SDP/2 .
If SDP is tight (M_SDP = M*), this PROVES min_viol = (known) and hence optimality.
"""
import sys, os, json, time
import numpy as np
import cvxpy as cp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ising_reduction import build_J
from solver_2factor_sat_pipeline import enumerate_clauses


def sdp_min_viol_lb(m, edges, time_limit=60):
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    J, missing, n_cl = build_J(clauses)
    n = m
    absw = {k: abs(v) for k, v in J.items()}
    sign = {k: (1 if v > 0 else -1) for k, v in J.items()}
    sum_abs = sum(absw.values())

    V = cp.Variable((n, n), PSD=True)
    constraints = [cp.diag(V) == np.ones(n)]
    obj = 0
    for (i, j), w in absw.items():
        obj += (w / 4.0) * (1 - sign[(i, j)] * V[i, j])
    prob = cp.Problem(cp.Maximize(obj), constraints)
    t0 = time.time()
    prob.solve(solver=cp.SCS, verbose=False, max_iters=20000)
    M_sdp = prob.value
    min_viol_lb = n_cl / 8.0 + sum_abs / 8.0 - M_sdp / 2.0
    return {
        "m": m, "n_clauses": n_cl, "closure_missing": missing,
        "sum_abs_J": sum_abs, "M_sdp": float(M_sdp),
        "sdp_status": prob.status,
        "min_viol_lb_sdp": float(min_viol_lb),
        "sdp_time_s": round(time.time() - t0, 1),
    }


def main():
    out = {}
    # m=37-408
    d = json.load(open("results/config_408_edges.json"))
    edges408 = [tuple(e) for e in d["edges"]]
    r = sdp_min_viol_lb(37, edges408)
    r["known_min_viol"] = 16
    out["m37_408"] = r
    print(f"m37-408: M_sdp={r['M_sdp']:.2f}, min_viol_lb(SDP)={r['min_viol_lb_sdp']:.3f} "
          f"(known 16, closure={r['closure_missing']})", flush=True)

    # m=37-448
    s = json.load(open("results/mutation_448_satchk.json"))
    edges448 = [(min(x[0], x[1]), max(x[0], x[1])) for x in s["edges"]]
    r = sdp_min_viol_lb(37, edges448)
    r["known_min_viol"] = 17
    out["m37_448"] = r
    print(f"m37-448: M_sdp={r['M_sdp']:.2f}, min_viol_lb(SDP)={r['min_viol_lb_sdp']:.3f} "
          f"(known 17, closure={r['closure_missing']})", flush=True)

    # m=36 (SAT, lower bound should be <= 0)
    m36 = json.load(open("results/solutions/m36.json"))
    edges36 = [tuple(sorted(c)) for c in m36["cells"]]
    r = sdp_min_viol_lb(36, edges36)
    r["known_min_viol"] = 0
    out["m36"] = r
    print(f"m36:     M_sdp={r['M_sdp']:.2f}, min_viol_lb(SDP)={r['min_viol_lb_sdp']:.3f} "
          f"(known 0, closure={r['closure_missing']})", flush=True)

    json.dump(out, open("results/sdp_frustration_cert.json", "w"), indent=2)
    print("saved results/sdp_frustration_cert.json")


if __name__ == "__main__":
    main()
