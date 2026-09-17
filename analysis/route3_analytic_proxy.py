"""
route3_analytic_proxy.py — Look for an analytic universal lower bound.

Consumes results/route3_joint_relaxation.json (validation + m=37 diverse sample)
plus the known 408/448 configs, and:
  1. Validates the SDP discriminator (SDP_lb <= true_min; SAT => SDP_lb <= 0).
  2. Regresses sdp_lb on structural features to find the strongest predictor and
     test whether a clean monotone inequality (sdp_lb >= f(features)) holds for
     ALL m=37 2-factors in the sample — the empirical basis for a universal bound.
  3. Tests specific candidate inequalities (per-clause spectral, odd-cycle count,
     frustrated-triangle count) and reports the worst-case margin.

Run AFTER route3_joint_relaxation.py completes.
"""
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from solver_2factor_sat_pipeline import enumerate_clauses
from ising_reduction import build_J
from route3_joint_relaxation import n_frustrated_triangles, cycle_lengths

DATA = "results/route3_joint_relaxation.json"
SDP408 = "results/sdp_frustration_cert.json"


def features(m, edges):
    clauses, _ = enumerate_clauses(m, edges, verbose=False)
    J, missing, n_cl = build_J(clauses)
    cyc = cycle_lengths(edges, m)
    fr = n_frustrated_triangles(J)
    return {"m": m, "n_clauses": n_cl, "n_edges": len(edges),
            "cycle_lengths": cyc,
            "n_odd_cycles": sum(1 for L in cyc if L % 2 == 1),
            "n_frustrated_triangles": fr}


def main():
    R = json.load(open(DATA))
    out = {}

    # ── 1. validation tables ──
    val_tbl = {}
    for m, blk in R["validation"].items():
        rows = []
        ok_lb = ok_sat = sat = 0
        for rec in blk["records"]:
            tm = rec.get("true_min")
            lb = rec.get("sdp_lb")
            ok = (tm is not None and lb is not None and lb <= tm + 1e-6)
            if ok:
                ok_lb += 1
            if tm == 0:
                sat += 1
                if lb is not None and lb <= 1e-6:
                    ok_sat += 1
            rows.append((rec["n_clauses"], lb, tm, rec["cycle_lengths"]))
        val_tbl[m] = {"n": blk["n_configs"], "sdp_le_true": ok_lb,
                      "sat_configs": sat, "sat_sdp_le0": ok_sat,
                      "min_sdp_lb": min(r[1] for r in rows if r[1] is not None),
                      "min_true_min": min(r[2] for r in rows if r[2] is not None)}
    out["validation"] = val_tbl
    for m, v in val_tbl.items():
        print(f"m={m}: {v['n']} configs | SDP<=true: {v['sdp_le_true']}/{v['n']} | "
              f"SAT={v['sat_configs']}, SDP<=0 on SAT: {v['sat_sdp_le0']}/{v['sat_configs']} | "
              f"min_sdp_lb={v['min_sdp_lb']:.3f} min_true={v['min_true_min']}", flush=True)

    # ── 2. assemble m=37 feature matrix (sample + known 408/448) ──
    pts = []
    for rec in R["m37_sample"]:
        if rec.get("sdp_lb") is None:
            continue
        pts.append({"lb": rec["sdp_lb"], "n_clauses": rec["n_clauses"],
                    "n_odd_cycles": rec["n_odd_cycles"],
                    "n_frustrated_triangles": rec["n_frustrated_triangles"],
                    "src": "sample"})
    # add known 408/448 (sdp_lb from SDP cert; features recomputed)
    sdp = json.load(open(SDP408))
    extras = [
        ("results/config_408_edges.json", sdp["m37_408"]["min_viol_lb_sdp"], 37),
        ("results/mutation_448_satchk.json", sdp["m37_448"]["min_viol_lb_sdp"], 37),
    ]
    for path, lb, m in extras:
        d = json.load(open(path))
        if "edges" in d:
            edges = [tuple(sorted((min(e[0], e[1]), max(e[0], e[1])) if isinstance(e, (list, tuple)) and len(e) == 2
                                 else (e, e))) for e in d["edges"]]
        else:
            edges = [tuple(sorted(c)) for c in d["cells"]]
        f = features(m, edges)
        pts.append({"lb": lb, "n_clauses": f["n_clauses"],
                    "n_odd_cycles": f["n_odd_cycles"],
                    "n_frustrated_triangles": f["n_frustrated_triangles"],
                    "src": path.split("/")[-1]})

    n = len(pts)
    print(f"\nm=37 points (sample + known): {n}", flush=True)
    lbs = [p["lb"] for p in pts]
    print(f"  sdp_lb: min={min(lbs):.3f} max={max(lbs):.3f} "
          f"mean={sum(lbs)/n:.3f}", flush=True)

    # regression: lb ~ n_clauses + n_odd_cycles + n_frustrated_triangles + 1
    X = np.array([[p["n_clauses"], p["n_odd_cycles"], p["n_frustrated_triangles"], 1.0]
                  for p in pts], dtype=float)
    y = np.array(lbs, dtype=float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ coef
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    print("\n  Regression  sdp_lb ~ b1*n_clauses + b2*n_odd + b3*n_frust_tri + b0", flush=True)
    print(f"    b1(n_clauses)={coef[0]:.5f}  b2(n_odd)={coef[1]:.4f}  "
          f"b3(frust_tri)={coef[2]:.5f}  b0={coef[3]:.3f}  R2={r2:.3f}", flush=True)

    # candidate universal inequalities: worst-case margin across sample
    def worst_margin(expr_fn, label):
        margins = [(p["src"], expr_fn(p) - p["lb"]) for p in pts]
        worst = min(m[1] for m in margins)
        print(f"  [{label}] min(lb - predicted) over sample = {worst:.3f} "
              f"(>=0 means predicted <= lb everywhere)", flush=True)
        return worst, margins

    worst_margin(lambda p: 0.03 * p["n_clauses"] - 2.0, "0.03*n_cl - 2")
    worst_margin(lambda p: p["n_frustrated_triangles"] * 0.04 - 1.0,
                 "0.04*n_frust_tri - 1")
    worst_margin(lambda p: p["n_odd_cycles"] * 1.0 + 8.0, "n_odd + 8")
    worst_margin(lambda p: coef[0]*p["n_clauses"]+coef[1]*p["n_odd_cycles"]
                 + coef[2]*p["n_frustrated_triangles"] + coef[3], "full regression")

    out["m37_regression"] = {"coef": coef.tolist(), "r2": r2,
                             "n_points": n, "min_lb": min(lbs),
                             "max_lb": max(lbs), "mean_lb": sum(lbs)/n}
    json.dump(out, open("results/route3_analytic_proxy.json", "w"), indent=2)
    print("\nsaved results/route3_analytic_proxy.json")


if __name__ == "__main__":
    main()
