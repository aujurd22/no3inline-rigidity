"""Matching-shell for an arbitrary base factor (default v40_02).

CLOSED-ENUMERATION (gives a definite answer), NOT open-loop search.
Each (base, distance, partition) is enumerated to closure (INFEASIBLE) for a
complete certificate. Results accumulate in shell_done.json so a crash can resume.

Modes:
  python run_shell_extension.py <base> <distance> [parts] [idx]
        -> run ONE partition, auto-picking 13 disjoint free edges for <base>
  python run_shell_extension.py --sweep
        -> run all unfinished partitions in PLAN (B: compare v40_01/03/04 vs v40_02)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MY = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
PY = "C:/Users/djr82/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SCRIPT = ROOT / "matching_master_enumerate.py"
DONE = MY / "shell_done.json"
PER_PART_TIMEOUT = 900

# B plan: compare basins. Each basin gets d=2..6; d=2 single-partition (cheap),
# d>=3 partitioned into 4 for tractability.
PLAN = {
    "v40_01": {2: 1, 3: 4, 4: 4, 5: 4, 6: 4},
    "v40_03": {2: 1, 3: 4, 4: 4, 5: 4, 6: 4},
    "v40_04": {2: 1, 3: 4, 4: 4, 5: 4, 6: 4},
}


def load_archive():
    return json.loads((OUT / "exact_factor_archive.json").read_text(encoding="utf-8"))


def pick13(edges):
    used, sel = set(), []
    for i, (u, v) in enumerate(edges):
        if u in used or v in used:
            continue
        sel.append(i); used.add(u); used.add(v)
        if len(sel) == 13:
            break
    return sel


def load_done():
    if DONE.exists():
        try:
            return json.loads(DONE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_done(d):
    DONE.write_text(json.dumps(d, indent=2), encoding="utf-8")


def run_one(base, distance, parts, idx, indices=None):
    if indices is None:
        arch = load_archive()
        e = next(x for x in arch["archive"] if x["id"] == base)
        indices = pick13([tuple(x) for x in e["edges"]])
    key = f"{base}:{distance}:{idx}"
    out = OUT / f"matching_master_{base}_distance{distance}_p{parts}_b{idx}.json"
    cmd = [
        PY, str(SCRIPT),
        "--base", base,
        "--indices", ",".join(str(i) for i in indices),
        "--distance", str(distance),
        "--partition-parts", str(parts),
        "--partition-index", str(idx),
        "--max-matchings", "200000",
        "--master-time-limit", "20.0",
        "--orientation-time-limit", "2.0",
        "--workers", "4",
        "--out", str(out),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True,
                       cwd=str(ROOT), timeout=PER_PART_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"base": base, "distance": distance, "idx": idx, "timeout": True}
    except subprocess.CalledProcessError as ex:
        return {"base": base, "distance": distance, "idx": idx,
                "error": ex.stderr[-500:]}
    try:
        a = json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        return {"base": base, "distance": distance, "idx": idx, "parse_error": True}
    hist = a.get("objective_histogram", {})
    best = min((int(k) for k in hist), default=None)
    return {
        "base": base, "distance": distance, "idx": idx, "parts": parts,
        "indices": indices,
        "closed": a.get("enumeration_closed"),
        "status": a.get("final_master_status"),
        "count": a.get("matching_count"),
        "best_objective": best,
    }


def summary_for(base):
    d = load_done()
    vs = [v["best_objective"] for k, v in d.items()
          if k.startswith(f"{base}:") and v.get("best_objective") is not None]
    return {"base": base, "min_objective": min(vs) if vs else None,
            "all_closed": all(v.get("closed") for k, v in d.items()
                              if k.startswith(f"{base}:") and "closed" in v)}


def main():
    args = sys.argv[1:]
    done = load_done()
    if args and args[0] != "--sweep":
        base = args[0]; distance = int(args[1])
        parts = int(args[2]) if len(args) > 2 else 1
        idx = int(args[3]) if len(args) > 3 else 0
        r = run_one(base, distance, parts, idx)
        done[f"{base}:{distance}:{idx}"] = r
        save_done(done)
        print(json.dumps(r, indent=2), flush=True)
        print("CURRENT", json.dumps(summary_for(base), indent=2), flush=True)
        return
    for base, dmap in PLAN.items():
        for distance, parts in dmap.items():
            for idx in range(parts):
                key = f"{base}:{distance}:{idx}"
                if key in done and done[key].get("closed"):
                    print(f"skip {key}", flush=True)
                    continue
                print(f"\n=== run {key} ===", flush=True)
                r = run_one(base, distance, parts, idx)
                done[key] = r
                save_done(done)
                print(json.dumps(r, indent=2), flush=True)
        print("BASIN", json.dumps(summary_for(base), indent=2), flush=True)
    print("\n=== SWEEP DONE ===", flush=True)
    for base in PLAN:
        print(json.dumps(summary_for(base), indent=2), flush=True)


if __name__ == "__main__":
    main()
