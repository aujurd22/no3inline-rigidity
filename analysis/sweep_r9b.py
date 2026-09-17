"""
sweep_r9b.py -- systematic small-n -> large-n scaling study for the R9b C4-NTIL
(rot4 No-Three-In-Line) 2-factor CP-SAT model.

For each m in [m_start, m_end]:
  * build the fast R9b 2-factor model (generate_constraints)
  * solve with a per-m timelimit, watching the wall-clock
  * record build_s, solve_s, status, #found, and the 2-factor cycle decomposition
  * APPEND a row to results/sweep_timing.csv   (PERSISTENT, append, resume-safe)
  * APPEND a line to   results/sweep_r9b.log    (PERSISTENT, append, never truncated)
  * if SAT, save the solution to results/solutions/m{XX:02d}.json (never overwritten)

RESUME: an m already present in the CSV is skipped, so a killed sweep just
continues on the next launch.  No file is ever deleted by this script -- logs
and solutions accumulate, exactly per the user's "logs must survive" rule.

Strategy (user directive): grow n from small to large and WATCH THE TIME.  A
per-m UNKNOWN (timeout) is itself the key data point -- it tells us where the
model stops scaling and focuses the next theoretical breakthrough.
"""
import os, sys, time, json, csv, argparse
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from solve_m37_r9b import (generate_constraints, solve_ortools,
                           verify_cells, cycle_decomp)

RESULTS = os.path.join(HERE, "results")
CSV = os.path.join(RESULTS, "sweep_timing.csv")
LOG = os.path.join(RESULTS, "sweep_r9b.log")
SOL_DIR = os.path.join(RESULTS, "solutions")
os.makedirs(SOL_DIR, exist_ok=True)


def log(msg):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def done_ms():
    if not os.path.exists(CSV):
        return set()
    with open(CSV) as f:
        return {int(r["m"]) for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m-start", type=int, default=5)
    ap.add_argument("--m-end", type=int, default=30)
    ap.add_argument("--per-m", type=float, default=600.0,
                    help="per-m solver timelimit (s); UNKNOWN = timed out")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-2factor", action="store_true")
    args = ap.parse_args()

    use_2f = not args.no_2factor
    done = done_ms()
    log(f"SWEEP START m={args.m_start}..{args.m_end} per-m={args.per_m}s "
        f"workers={args.workers} 2F_on={use_2f} already_done={sorted(done)}")

    if not os.path.exists(CSV):
        with open(CSV, "w", newline="") as f:
            csv.writer(f).writerow(
                ["m", "n", "build_s", "solve_s", "status", "found",
                 "n_cycles", "cycle_lengths", "ts"])

    for m in range(args.m_start, args.m_end + 1):
        if m in done:
            log(f"  m={m}: SKIP (already in CSV)")
            continue
        t0 = time.time()
        reps, lc, tf = generate_constraints(m, use_2f)
        tgen = time.time() - t0
        log(f"  m={m}: gen reps={len(reps)} line_cons={len(lc)} "
            f"2F_on={use_2f} gen={tgen:.1f}s")
        status, cells, ts = solve_ortools(
            reps, lc, tf, args.per_m, workers=args.workers,
            checkpoint=None, resume=None, verbose=False)
        cyc = cycle_decomp(cells, m) if cells else []
        vf = verify_cells(cells, m)[0] if cells else False
        log(f"  m={m}: status={status} found={len(cells)} verify={vf} "
            f"solve={ts:.1f}s cycles={cyc}")
        if cells and status in ("OPTIMAL", "FEASIBLE"):
            sp = os.path.join(SOL_DIR, f"m{m:02d}.json")
            if not os.path.exists(sp):
                with open(sp, "w") as f:
                    json.dump({"m": m, "n": 2 * m, "cells": cells,
                               "cycles": cyc, "verify": vf}, f, indent=1)
                log(f"  m={m}: solution saved -> {sp}")
        with open(CSV, "a", newline="") as f:
            csv.writer(f).writerow(
                [m, 2 * m, f"{tgen:.1f}", f"{ts:.1f}", status, len(cells),
                 len(cyc), ",".join(map(str, cyc)),
                 datetime.now().isoformat(timespec='seconds')])
        if status == "INFEASIBLE":
            log(f"  m={m}: INFEASIBLE -> stop sweep (unsat found)")
            break
    log("SWEEP END")


if __name__ == "__main__":
    main()
