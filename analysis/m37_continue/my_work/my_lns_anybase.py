"""Bounded closed LNS descent probe that works for ANY archive base (not just V=40).

Reuses directed_cell_lns.solve_neighborhood (proven: asserts geometry==objective,
diagonal_safe, is_2factor) and make_neighborhoods (defect-coverage modes).
Writes to outputs/<out>. Each neighborhood is a closed CP-SAT solve with a
hard time-limit and an optional target upper bound (INFEASIBLE == provably no
config with <= target in that neighborhood). The whole sweep is finite.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # m37_continue
sys.path.insert(0, ROOT)  # allow importing directed_cell_lns + its deps

from directed_cell_lns import solve_neighborhood, make_neighborhoods

OUTDIR = os.path.join(ROOT, "outputs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bases", required=True, help="comma-separated archive ids (any value)")
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--iterations", type=int, default=4)
    ap.add_argument("--target", type=int, default=36, help="upper bound; -1 disables")
    ap.add_argument("--time-limit", type=float, default=30.0)
    ap.add_argument("--modes", default="0,1,2,3,4")
    ap.add_argument("--seed0", type=int, default=202607175000)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    modes = tuple(int(x) for x in args.modes.split(","))
    archive = json.load(open(os.path.join(OUTDIR, "exact_factor_archive.json")))
    by_id = {e["id"]: e for e in archive["archive"]}
    wanted = [b for b in args.bases.split(",") if b in by_id]
    if not wanted:
        raise SystemExit("no matching bases")
    bases = [by_id[b] for b in wanted]

    target_val = None if args.target < 0 else args.target
    payload = {"parameters": vars(args), "runs": [], "best_candidate": None}
    out_path = os.path.join(OUTDIR, args.out)
    for bi, base in enumerate(bases):
        defects, neighborhoods = make_neighborhoods(
            base, args.k, args.iterations, args.seed0 + bi, modes
        )
        print(f"base={base['id']} value={base['value']} defects={len(defects)} "
              f"neighborhoods={len(neighborhoods)}", flush=True)
        for ni, nb in enumerate(neighborhoods, 1):
            sol = solve_neighborhood(
                base, nb["indices"], target_val, args.time_limit,
                8, 1, 0, False, None, None,
            )
            rec = {"base": base["id"], "base_value": base["value"],
                   "covered_defects": nb["covered_defects"], "solve": sol}
            payload["runs"].append(rec)
            if sol.get("objective") is not None:
                best = payload["best_candidate"]
                if best is None or sol["objective"] < best["solve"]["objective"]:
                    payload["best_candidate"] = rec
            json.dump(payload, open(out_path, "w"), indent=2)
            print(f"  run={ni}/{len(neighborhoods)} k={args.k} -> "
                  f"{sol['status']} obj={sol.get('objective')} "
                  f"bound={sol.get('best_bound')}", flush=True)
            if target_val is not None and sol.get("objective", 10**9) <= target_val:
                print("TARGET REACHED", out_path)
                return
    print("DONE", out_path)


if __name__ == "__main__":
    main()
