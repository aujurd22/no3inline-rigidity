#!/usr/bin/env python3
# verify_lll_perm.py
# Symmetric LLL bound for the (X) quadratic layer of rot4-NTIL,
# computed on the PRODUCT cell-selection space (the correct model:
# cells chosen independently with prob q=c/m; (X) event = 3 specific
# cells all selected; dependency d = 3 * (max (X)-degree of a cell)).
#
# Two degree bounds are checked:
#   (T) trivial : D_cell <= m^2  (each cell can pair with <= m^2 others,
#                 at most 1 third cell per pair lies on the lift-line)
#   (E) empirical: D_cell <= x_deg_max  (measured, conflict_hypergraph_params.json)
#
# Symmetric LLL condition: e * p * (d+1) <= 1,  p = (c/m)^3.
# If it holds, an (X)-conflict-free subset of expected size c*m exists.
import json, math

params = json.load(open("analysis/results/conflict_hypergraph_params.json"))
e = math.e
rows = []
for key in sorted(params, key=lambda k: int(k)):
    m = params[key]["m"]
    xmax = params[key]["x_deg_max"]
    for c in (1, 2):
        q = c / m
        p = q ** 3
        # trivial bound
        dT = 3 * (m * m)            # 3 cells of the triple, each in <= m^2 (X)-triples
        bT = e * p * (dT + 1)
        # empirical bound
        dE = 3 * xmax
        bE = e * p * (dE + 1)
        rows.append({
            "m": m, "c": c, "q": round(q, 4), "p": f"{p:.2e}",
            "d_trivial": dT, "bound_trivial": round(bT, 3),
            "d_empirical": dE, "bound_empirical": round(bE, 3),
            "LLL_trivial_ok": bT <= 1.0, "LLL_empirical_ok": bE <= 1.0,
        })

print(f"{'m':>3} {'c':>1} {'q':>7} {'p':>9} | {'dT':>7} {'bT':>6} | {'dE':>5} {'bE':>6} | T  E")
print("-" * 70)
for r in rows:
    print(f"{r['m']:>3} {r['c']:>1} {r['q']:>7} {r['p']:>9} | {r['d_trivial']:>7} {r['bound_trivial']:>6} | {r['d_empirical']:>5} {r['bound_empirical']:>6} | {'Y' if r['LLL_trivial_ok'] else 'N'}  {'Y' if r['LLL_empirical_ok'] else 'N'}")

# Threshold (trivial bound): smallest m with bound<=1 at c=1
thr = None
for r in rows:
    if r["c"] == 1 and r["LLL_trivial_ok"]:
        thr = r["m"]; break
print(f"\nTrivial-bound LLL threshold (c=1, (X)-layer): first m with bound<=1 is m={thr}")

json.dump(rows, open("analysis/results/verify_lll_perm.json", "w"), indent=2)
print("saved analysis/results/verify_lll_perm.json")
