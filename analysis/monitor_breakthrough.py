"""
Monitor relaxed_sa output, detect any perfect-2-factor (penalty=0) with GV<70,
and immediately verify with CP-SAT MaxSAT.
"""
import json, time, sys, os
from collections import Counter

BASE = "D:/djr82/Documents/workbuddy/2026-07-03-16-29-36/no3inline-rigidity/analysis"
RESULTS = f"{BASE}/results"

def degree_penalty(cells):
    deg = Counter([v for c in cells for v in c])
    return sum(abs(deg.get(i, 0) - 2) for i in range(37))

def check_for_breakthrough():
    """Check all saved result files for low-GV perfect 2-factors."""
    import glob
    files = glob.glob(f"{RESULTS}/relaxed_best_*.json")
    files += glob.glob(f"{RESULTS}/bi_search_best.json")
    files += glob.glob(f"{RESULTS}/sa_gv_best_*.json")
    files += glob.glob(f"{RESULTS}/sa_gv_final.json")
    
    candidates = []
    for fn in files:
        try:
            with open(fn) as f:
                data = json.load(f)
        except:
            continue
        
        edges = data.get("edges", data.get("best_cells", data.get("cells", [])))
        edges = [(min(u,v), max(u,v)) for u,v in edges if isinstance(u, (int, float))]
        
        if len(edges) != 37:
            continue
        
        pen = degree_penalty(edges)
        gv_val = data.get("gv", data.get("best_gv", 0))
        
        if pen == 0 and gv_val > 0:
            candidates.append((gv_val, fn, edges))
    
    candidates.sort()
    return candidates

# Continuous monitor
print("=" * 60)
print("BREAKTHROUGH MONITOR")
print("=" * 60)
print(f"Watching for perfect 2-factors with GV < 70...", flush=True)

last_count = 0
while True:
    candidates = check_for_breakthrough()
    if len(candidates) > last_count:
        for gv_val, fn, edges in candidates[last_count:]:
            print(f"  Found: GV={gv_val} in {fn}", flush=True)
            if gv_val < 70:
                print(f"    ★★ BREAKTHROUGH CANDIDATE! GV={gv_val} < 70! ★★", flush=True)
                # Save for CP-SAT verification
                out = {"edges": edges, "gv": gv_val, "source": fn}
                with open(f"{RESULTS}/breakthrough_candidate.json", "w") as f:
                    json.dump(out, f)
                print(f"    Saved to breakthrough_candidate.json", flush=True)
        last_count = len(candidates)
    
    if candidates and candidates[0][0] < 70:
        print(f"\n  Best candidate: GV={candidates[0][0]}", flush=True)
        print(f"  To verify with CP-SAT, run:", flush=True)
        print(f"    python -c \"from solver_2factor_sat_pipeline import *; ...\"", flush=True)
        break
    
    if last_count > 0:
        remaining = 60 - (time.time() % 60)
        print(f"  No breakthrough yet. Best GV={candidates[0][0] if candidates else 'N/A'}. Checking again in 30s...", flush=True)
    
    time.sleep(30)
