"""gating_m37_only.py -- focused re-verification of switch-reducibility for m=37.

Prior gating_lll_r1.py stopped at m=30; m=37 was never tested. This fills the gap
for direction ① under a short budget (no long runs). Writes results/gating_m37.json
WITHOUT touching the original gating_lll_r1.json (which holds m=10..30).
"""
import os, json, random, time, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gating_lll_r1 import gating_one


def main():
    m = 37
    n_cfg, n_red, K = 150, 60, 200   # ~6-7 min in CPython for m=37
    rng = random.Random(20260713 + m)
    t0 = time.time()
    r = gating_one(m, rng, n_cfg, n_red, K)
    r["sec"] = round(time.time() - t0, 1)
    out = {
        "model": "config-model random 2-factor (2m stubs paired)",
        "note": "m=37 was absent from gating_lll_r1.json (which stopped at m=30). "
                "This re-verifies switch-reducibility (red_config_frac) for m=37 only, "
                "under a <10min budget. red_config_frac = fraction of bad configs that "
                "have >=1 strictly reducing 2-switch (the switching/entropy-compression "
                "viability criterion; ~1.0 for m>=14 previously).",
        "result": r,
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "results", "gating_m37.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(r, indent=2))
    print(f"[done] wrote {path}")


if __name__ == "__main__":
    main()
