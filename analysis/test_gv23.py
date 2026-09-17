"""
test_gv23.py — Run SDP certification on the GV=23 config.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdp_frustration_cert import sdp_min_viol_lb

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "results", "mutate_gv23.json")) as f:
    d = json.load(f)
edges = [tuple(e) for e in d["edges"]]
print(f"GV=23 config: {len(edges)} edges", flush=True)

# Quick clause count
from solver_2factor_sat_pipeline import enumerate_clauses
cls, _ = enumerate_clauses(37, edges, verbose=False)
print(f"Clause count: {cls}", flush=True)

print(f"\nRunning SDP...", flush=True)
r = sdp_min_viol_lb(37, edges)
print(f"SDP lb = {r['min_viol_lb_sdp']:.3f}", flush=True)
print(f"Status: {r['sdp_status']}", flush=True)

# Compare with config_408
print(f"\nconfig_408: SDP lb = 12.524, violations=16 (proven optimal)")
print(f"GV=23:     SDP lb = {r['min_viol_lb_sdp']:.3f}")

if r['min_viol_lb_sdp'] < 12.524:
    print(f"\n✅ GV=23 config has LOWER SDP bound than config_408!")
    print(f"   Potential to beat 16 violations!")
else:
    print(f"\n❌ SDP bound is not better than config_408")
    print(f"   The GV metric was misleading (as before)")
