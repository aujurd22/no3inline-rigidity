"""Resolve the 10 UNKNOWN LNS runs from the 44/48/52 probe.

Each UNKNOWN had time-limit=15s and best_bound=None (CP-SAT could not even
construct a <=36 candidate). We re-run the SAME neighborhoods (make_neighborhoods
is deterministic in seed) with time-limit=60s to get a closed verdict
(INFEASIBLE == provably no <=36 config in that neighborhood, or a real find).

This is a closed, finite enumeration -- not an open-ended search.
"""
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # m37_continue
HERE = os.path.join(ROOT, "my_work")
ORDER = ["v44_01", "v44_02", "v44_03", "v48_01", "v48_02", "v48_03",
         "v52_01", "v52_02", "v52_03"]
SEED0 = 202607175000


def main():
    unknown = set()
    for fn in sorted(glob.glob(os.path.join(ROOT, "outputs", "my_lns_anybase_k*.json"))):
        k = int(fn.split("_k")[1].split(".")[0])
        a = json.load(open(fn))
        for r in a["runs"]:
            if r["solve"]["status"] == "UNKNOWN":
                unknown.add((r["base"], k))
    print(f"resolving {len(unknown)} (base,k) combos -> "
          f"{sum(2 for _ in unknown)} neighborhoods at 60s each", flush=True)
    for base, k in sorted(unknown):
        bi = ORDER.index(base)
        seed0 = SEED0 + bi
        out = f"outputs/resolve_k{k}_{base}.json"
        cmd = [sys.executable,
               os.path.join(HERE, "my_lns_anybase.py"),
               "--bases", base, "--k", str(k), "--iterations", "2",
               "--target", "36", "--time-limit", "60",
               "--seed0", str(seed0), "--out", out]
        print(f"--- resolve base={base} k={k} seed0={seed0} ---", flush=True)
        subprocess.run(cmd, cwd=ROOT, check=False)
    print("=== RESOLVE DONE ===", flush=True)


if __name__ == "__main__":
    main()
