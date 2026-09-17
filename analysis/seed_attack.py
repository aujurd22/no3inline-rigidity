"""
seed_attack.py — Feed the [29,8] best config into SDP certification.
If SDP lower bound < 16, this config can potentially beat the current best.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sdp_frustration_cert import sdp_min_viol_lb

HERE = os.path.dirname(os.path.abspath(__file__))

# Load [29,8] edges
with open(os.path.join(HERE, "results", "best_gv_63_edges.json")) as f:
    d298 = json.load(f)
edges_298 = [tuple(e) for e in d298["edges"]]
print(f"[29,8] edges loaded: {len(edges_298)} edges", flush=True)
print(f"Cycle type: {d298.get('cycle_type', 'unknown')}", flush=True)
print(f"GV (naive orientation): {d298.get('geometric_violations', 'unknown')}", flush=True)

# Load config_408 for comparison
with open(os.path.join(HERE, "results", "config_408_edges.json")) as f:
    d408 = json.load(f)
edges_408 = [tuple(e) for e in d408["edges"]]

print("\n=== Running SDP certification ===", flush=True)
print(f"Config [29,8] ...", flush=True)
t0 = time.time()
r298 = sdp_min_viol_lb(37, edges_298)
t298 = time.time() - t0
print(f"  Done in {t298:.1f}s", flush=True)

print(f"Config [9,28] (config_408) ...", flush=True)
t0 = time.time()
r408 = sdp_min_viol_lb(37, edges_408)
t408 = time.time() - t0
print(f"  Done in {t408:.1f}s", flush=True)

print("\n" + "=" * 60)
print("SDP CERTIFICATION RESULTS")
print("=" * 60)
print(f"{'Metric':<25s} {'[29,8]':>12s} {'[9,28] config_408':>18s}")
print("-" * 60)
for key in ["n_clauses", "sum_abs_J", "M_sdp", "min_viol_lb_sdp", "sdp_time_s"]:
    v298 = r298[key]
    v408 = r408[key]
    if isinstance(v298, float):
        print(f"{key:<25s} {v298:>12.3f} {v408:>18.3f}")
    else:
        print(f"{key:<25s} {str(v298):>12s} {str(v408):>18s}")
print(f"{'known_min_viol':<25s} {'?':>12s} {'16':>18s}")

print(f"\n{'closure_missing':<25s} {str(r298['closure_missing']):>12s} {str(r408['closure_missing']):>18s}")
print(f"{'sdp_status':<25s} {r298['sdp_status']:>12s} {r408['sdp_status']:>18s}")

# Interpret
lb298 = r298["min_viol_lb_sdp"]
lb408 = r408["min_viol_lb_sdp"]
print(f"\n{'='*60}")
if lb298 < lb408:
    print(f"✅ [29,8] LOWER BOUND ({lb298:.2f}) < config_408 ({lb408:.2f})")
    print(f"   → [29,8] can potentially beat 16 violations!")
    print(f"   Gap from known best: {lb298 - 16:.2f} (negative = can beat)")
elif lb298 > lb408:
    print(f"❌ [29,8] LOWER BOUND ({lb298:.2f}) > config_408 ({lb408:.2f})")
    print(f"   → [29,8] is provably worse than config_408")
else:
    print(f"→ [29,8] and config_408 have essentially the same SDP bound")
