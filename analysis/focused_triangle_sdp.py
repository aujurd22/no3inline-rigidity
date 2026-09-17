"""
focused_triangle_sdp.py — triangle-only SDP lower bound on min_viol for the three
key configs (m37-408, m37-448, m36-SAT). No odd-cycle enumeration (too heavy).
Purpose: complete the optimality-proof table and VALIDATE direction via m36 (must be <= 0).
"""
import sys, os, json, time
import numpy as np
import cvxpy as cp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ising_reduction import build_J
from solver_2factor_sat_pipeline import enumerate_clauses


def sdp_triangle(m, edges, time_limit=120, solver=cp.CLARABEL):
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    J, missing, n_cl = build_J(clauses)
    n = m
    Y = cp.Variable((n, n), symmetric=True)
    cons = [Y >> 0, cp.diag(Y) == np.ones(n)]
    obj = 0
    for (i, j), v in J.items():
        obj += v * Y[i, j]
    # triangle inequalities (cut-polytope valid facets)
    import itertools
    for (i, j, k) in itertools.combinations(range(n), 3):
        cons.append(Y[i, j] + Y[j, k] + Y[k, i] >= -1)
        cons.append(Y[i, j] - Y[i, k] - Y[j, k] >= -1)
        cons.append(Y[i, k] - Y[i, j] - Y[j, k] >= -1)
        cons.append(Y[j, k] - Y[i, j] - Y[i, k] >= -1)
    prob = cp.Problem(cp.Minimize(obj), cons)
    prob.solve(solver=solver, time_limit=time_limit, verbose=False)
    if prob.status not in ("optimal", "optimal_inaccurate") or prob.value is None:
        # fallback SCS
        prob.solve(solver=cp.SCS, verbose=False, max_iters=20000)
    SDP_min = float(prob.value) if prob.value is not None else None
    lb = (n_cl + SDP_min) / 8.0 if SDP_min is not None else None
    return {"n_clauses": n_cl, "SDP_min": SDP_min, "min_viol_lb": lb,
            "status": prob.status, "closure_missing": missing}


def load_config(path, m):
    d = json.load(open(path))
    if m == 36:
        return [tuple(sorted(c)) for c in d["cells"]]
    edges = []
    for x in d["edges"]:
        if isinstance(x, (list, tuple)) and len(x) == 2:
            u, v = x[0], x[1]
        elif isinstance(x, int):
            u = v = x
        else:
            raise ValueError(f"bad edge {x!r}")
        edges.append((min(u, v), max(u, v)))
    return edges


def main():
    cfgs = {
        "m37_408": ("results/config_408_edges.json", 37, 16),
        "m37_448": ("results/mutation_448_satchk.json", 37, 17),
        "m36_SAT": ("results/solutions/m36.json", 36, 0),
    }
    out = {}
    for name, (path, m, known) in cfgs.items():
        edges = load_config(path, m)
        r = sdp_triangle(m, edges, time_limit=120)
        out[name] = {"known_min_viol": known, **r}
        print(f"{name}: known={known} n_cl={r['n_clauses']} "
              f"SDP_min={r['SDP_min']:.4f} min_viol_lb={r['min_viol_lb']:.4f} "
              f"status={r['status']}", flush=True)
    json.dump(out, open("results/focused_triangle_sdp.json", "w"), indent=2)
    print("\nsaved results/focused_triangle_sdp.json")
    # validation: m36 must be <= 0
    v36 = out["m36_SAT"]["min_viol_lb"]
    print(f"\nVALIDATION m36 bound <= 0 ? {v36} -> {v36 <= 0}")
    for name, r in out.items():
        lb = r["min_viol_lb"]
        if lb is None:
            print(f"  {name}: bound FAILED (inconclusive)")
        else:
            proven = lb >= r["known_min_viol"] - 1e-6
            print(f"  {name}: lb={lb:.4f} known={r['known_min_viol']} "
                  f"-> {'PROVEN >= known (optimal)' if proven else 'not closed'}")


if __name__ == "__main__":
    main()
