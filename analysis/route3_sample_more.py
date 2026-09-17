"""
route3_sample_more.py — Extend the m=37 diverse 2-factor SDP sample.

Loads results/route3_joint_relaxation.json, generates ADDITIONAL independent random
2-factors for m=37, computes the SDP lower bound for each, and appends to m37_sample.
Purpose: tighten the empirical floor (route3_sdp_report.md, Option 1) — if every
additional sample also has SDP_lb >= ~45, the impossibility evidence for m=37 becomes
overwhelming.

Run as background; saves incrementally so partial progress survives interruption.
"""
import sys, os, json, time, random
import numpy as np  # noqa  (kept for parity with imported modules)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from route3_joint_relaxation import evaluate, random_2factor

OUT = "results/route3_joint_relaxation.json"
M = 37
ADD = 80            # additional 2-factors to sample
SDP_TIME = 60       # seconds per SDP solve
SEED = 98765        # new seed (independent of the original N=20 run)


def main():
    results = json.load(open(OUT))
    sample = results.get("m37_sample", [])
    start_idx = max((s.get("sample_idx", 0) for s in sample), default=-1) + 1
    rng = random.Random(SEED)
    t0 = time.time()
    print(f"Extending m={M} sample: start_idx={start_idx}, ADD={ADD}, seed={SEED}",
          flush=True)
    lbs = [s["sdp_lb"] for s in sample if s.get("sdp_lb") is not None]
    for k in range(ADD):
        idx = start_idx + k
        edges = random_2factor(M, rng)
        rec = evaluate(M, edges, compute_exact=False, sdp_time=SDP_TIME)
        rec["sample_idx"] = idx
        sample.append(rec)
        if rec.get("sdp_lb") is not None:
            lbs.append(rec["sdp_lb"])
        print(f"  [+{k+1}/{ADD}] idx={idx} sdp_lb={rec.get('sdp_lb')} "
              f"n_cl={rec['n_clauses']} n_odd={rec['n_odd_cycles']} "
              f"fr_tri={rec['n_frustrated_triangles']}", flush=True)
        results["m37_sample"] = sample
        results["meta"]["m37_sample_summary"] = {
            "n": len(lbs),
            "min_lb": min(lbs),
            "max_lb": max(lbs),
            "mean_lb": sum(lbs) / len(lbs),
        }
        results["meta"]["total_time_s"] = round(time.time() - t0, 1)
        json.dump(results, open(OUT, "w"), indent=2)
    print(f"\nDone. total m=37 samples now = {len(sample)}; "
          f"min_sdp_lb={min(lbs):.3f} max={max(lbs):.3f} "
          f"mean={sum(lbs)/len(lbs):.3f}", flush=True)


if __name__ == "__main__":
    main()
