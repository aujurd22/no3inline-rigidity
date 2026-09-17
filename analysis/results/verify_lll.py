#!/usr/bin/env python3
"""Verify the Lovasz Local Lemma (symmetric) condition for the (X)-conflict layer
of the rot4-NTIL problem, on the product cell-selection probability space.

We model: each of the m^2 candidate quadrant cells is selected independently
with probability q.  A bad event is "a specific collinear (X)-triple of cells is
fully selected" (collinearity is deterministic once the 3 cells are fixed).

Symmetric LLL: if e * p * (d+1) <= 1, then with positive probability NO bad event
fires -> there exists an (X)-conflict-free selection of cells.

We then check that the expected number of selected cells is >= m (so a subset of
size >= m, hence a candidate fundamental domain, exists).

NOTE (honest scope, see lll_existence_sketch.md):
- This proves existence of an (X)-conflict-free m-subset.  It does NOT by itself
  prove rot4-NTIL existence, because (a) the (S) slope-+-1 line layer and
  (b) the 2-regular / permutation structure must also be satisfied.  Those are
  handled in the permutation model (FDR = Sidon layer + R9b 2-regularity), and
  are the subject of the pending closing lemma.
"""
import json, math

DATA = json.load(open("analysis/results/conflict_hypergraph_params.json"))

# We pick q so that mean selected cells = m^2 * q >= m  (take q = c/m, c>=1).
# Use the largest c still satisfying the LLL bound; report c=1 and c=2.
results = {}
for key, d in DATA.items():
    m = d["m"]
    x_deg_max = d["x_deg_max"]          # max # (X)-triples containing a fixed CELL
    d_dep = 3 * x_deg_max               # an (X)-event shares a cell with <= 3*x_deg_max others
    row = {"m": m, "x_deg_max": x_deg_max, "d_dependency": d_dep,
           "q_options": {}}
    for c in (1, 2, 3):
        q = c / m
        p = q ** 3                       # P(specific 3 cells all selected)
        bound = math.e * p * (d_dep + 1) # symmetric LLL LHS
        mean_sel = (m * m) * q           # expected # selected cells
        row["q_options"][f"c={c} (q={q:.4f})"] = {
            "p_event": p,
            "e_p_d1": bound,
            "LLL_ok": bound <= 1.0,
            "mean_selected": mean_sel,
            "mean_ge_m": mean_sel >= m,
        }
    # threshold q_max s.t. e*q^3*(d+1)=1
    q_max = (1.0 / (math.e * (d_dep + 1))) ** (1.0 / 3.0)
    row["q_max_LLL"] = q_max
    row["mean_selected_at_qmax"] = (m * m) * q_max
    results[key] = row

print(f"{'m':>3} {'x_deg_max':>9} {'d_dep':>6} {'q_max':>7} {'mean@qmax':>10}  "
      f"{'c=1 LLL':>9} {'c=2 LLL':>9} {'c=3 LLL':>9}")
for key, r in results.items():
    m = r["m"]
    o1 = r["q_options"]["c=1 (q=%.4f)" % (1/m)]
    o2 = r["q_options"]["c=2 (q=%.4f)" % (2/m)]
    o3 = r["q_options"]["c=3 (q=%.4f)" % (3/m)]
    def f(b): return "OK" if b else "FAIL"
    print(f"{m:>3} {r['x_deg_max']:>9} {r['d_dependency']:>6} "
          f"{r['q_max_LLL']:>7.4f} {r['mean_selected_at_qmax']:>10.1f}  "
          f"{f(o1['LLL_ok']):>9} {f(o2['LLL_ok']):>9} {f(o3['LLL_ok']):>9}")

json.dump(results, open("analysis/results/verify_lll.json", "w"), indent=2)
print("\nSaved -> analysis/results/verify_lll.json")
