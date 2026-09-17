"""Verify whether archive values 44/52/60 are real (correct oracle) or buggy
artifacts.  If they survive as 44/52/60, then bad_triples can be ≡4 mod 8,
so 36 is theoretically reachable.  If they collapse to ≡0 mod 8 (e.g. 48/56/64),
then every true value is ≡0 mod 8 and 36 is IMPOSSIBLE -> strong structural theorem.
"""
from __future__ import annotations
import json, sys, time
sys.path.insert(0, ".")
from signed_nae_core import geometry_bad_count, solve_cp_sat
from weighted_geometry_ising import enumerate_weighted, enumerate_pair_weighted, build_weighted_ising

m = 37
arch = json.load(open("outputs/exact_factor_archive.json"))
factors = {e["id"]: e for e in arch["archive"]}
reps = ["v44_01", "v52_01", "v60_01"]

report = []
for rid in reps:
    e = factors[rid]
    edges = [tuple(sorted(tuple(ee))) for ee in e["edges"]]
    bits = e["bits"]
    geo_truth = geometry_bad_count(m, edges, bits)["bad_triples"]
    pp = enumerate_pair_weighted(m, edges)
    pat = enumerate_weighted(m, edges)
    const, jmat, miss, uneq = build_weighted_ising(m, pat, pp)
    t0 = time.time()
    res = solve_cp_sat(const, jmat, time_limit=120.0, hint=bits)
    dt = time.time() - t0
    opt = res.get("violations")
    print(f"{rid}: archived={e['value']} geo_stored={geo_truth} correct_OPTIMAL={opt} "
          f"status={res.get('status')} consistent={not miss and not uneq} ({dt:.1f}s)")
    report.append({"id": rid, "archived": e["value"], "geo_stored": geo_truth,
                   "correct_optimal": opt, "consistent": not miss and not uneq})

json.dump(report, open("outputs/mod8_reps_recheck.json", "w"), indent=2)
print("Saved -> outputs/mod8_reps_recheck.json")
