"""Score the best VALID mutation config (GV=27) with SDP."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdp_frustration_cert import sdp_min_viol_lb

HERE = os.path.dirname(os.path.abspath(__file__))

for gv, name, expected_valid in [
    (27, "mutate_gv27.json", True),
    (29, "mutate_gv29.json", True),
    (31, "mutate_gv31.json", True),
    (33, "mutate_gv33.json", True),
]:
    with open(os.path.join(HERE, "results", name)) as f:
        d = json.load(f)
    edges = [tuple(e) for e in d["edges"]]
    
    # Validate
    n_uniq = len(set(edges))
    if n_uniq != 37:
        print(f"GV={gv}: ❌ INVALID ({n_uniq} unique), skipping", flush=True)
        continue
    
    print(f"\nGV={gv} valid config — running SDP...", flush=True)
    r = sdp_min_viol_lb(37, edges)
    print(f"  SDP_lb = {r['min_viol_lb_sdp']:.3f}, clauses = {r['n_clauses']}", flush=True)
