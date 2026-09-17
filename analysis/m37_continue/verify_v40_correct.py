"""Decisive cross-check: re-evaluate the 4 archived v40_* solutions with the
CORRECT multiplicity-weighted oracle (enumerate_weighted + build_weighted_ising
+ solve_cp_sat), not the buggy enumerate_clauses model.

For each v40_* we report three numbers:
  - geometry_bad_count(archived bits)   : ground truth for the stored orientation
  - weighted_value(archived bits)        : correct model on stored orientation
  - correct CP-SAT OPTIMAL               : true best orientation for that 2-factor
"""
from __future__ import annotations
import json, sys, time
sys.path.insert(0, ".")
from signed_nae_core import geometry_bad_count, solve_cp_sat
from weighted_geometry_ising import enumerate_weighted, enumerate_pair_weighted, build_weighted_ising, weighted_value

m = 37
ARCHIVE = "outputs/exact_factor_archive.json"

with open(ARCHIVE) as f:
    data = json.load(f)
factors = {e["id"]: e for e in data["archive"]}
v40 = [factors[k] for k in ("v40_01", "v40_02", "v40_03", "v40_04") if k in factors]

print(f"Found {len(v40)} v40 entries to re-check\n")
report = []
for e in v40:
    edges = [tuple(sorted(tuple(ee))) for ee in e["edges"]]
    bits = e["bits"]
    assert len(edges) == m and len(bits) == m
    t0 = time.time()
    geo_truth = geometry_bad_count(m, edges, bits)["bad_triples"]
    pair_patterns = enumerate_pair_weighted(m, edges)
    patterns = enumerate_weighted(m, edges)
    const, jmat, missing, unequal = build_weighted_ising(m, patterns, pair_patterns)
    wv = weighted_value(patterns, pair_patterns, bits)
    t1 = time.time()
    res = solve_cp_sat(const, jmat, time_limit=120.0, hint=bits)
    t2 = time.time()
    opt = res.get("violations")
    opt_geo = geometry_bad_count(m, edges, res["bits"])["bad_triples"] if res.get("bits") else None
    ok_model = (not missing) and (not unequal)
    print(f"{e['id']}:")
    print(f"  archived 'value' field      = {e.get('value')}")
    print(f"  geometry_bad_count(stored)  = {geo_truth}   (ground truth)")
    print(f"  weighted_value(stored)      = {wv}   model_self_consistent={ok_model}")
    print(f"  correct CP-SAT status       = {res.get('status')} (optimal={res.get('optimal')})")
    print(f"  correct CP-SAT OPTIMAL val  = {opt}  -> geometry recheck = {opt_geo}")
    print(f"  timing: enumerate {t1-t0:.1f}s, cp-sat {t2-t1:.1f}s\n")
    report.append({
        "id": e["id"], "archived_value": e.get("value"),
        "geo_truth_stored": geo_truth, "weighted_stored": wv,
        "cpsat_status": res.get("status"), "cpsat_optimal_value": opt,
        "cpsat_optimal_geo": opt_geo, "model_consistent": ok_model,
    })

with open("outputs/v40_correct_oracle_recheck.json", "w") as f:
    json.dump(report, f, indent=2)
print("Saved -> outputs/v40_correct_oracle_recheck.json")
