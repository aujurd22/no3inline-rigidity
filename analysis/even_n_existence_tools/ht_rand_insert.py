"""Randomized insertion + improvement loop for the half-turn extension.

Start from an embedded clean core (E=0, m reps).  Repeatedly:
  - pick a random "good" cell (weighted toward low insertion dE),
  - insert it, run best_improvement, record the best E seen.
The randomization gives the search a chance to find basins the deterministic
greedy misses."""

import argparse
import json
import random
import sys
import time

import ht_repair as HR


def excess_of(reps, n):
    m = len(reps)
    N1, N2, *_ = HR.census_and_violations(reps, n)
    return (N1 - (3 * m * m - 2 * m)) + 3 * (N2 - m * m)


def run(n, reps, target_m, rounds=200, seed=1, log=None, topk=200):
    rng = random.Random(seed)
    best = (excess_of(reps, n), [p for p in reps])
    E = best[0]
    t0 = time.time()
    for rnd in range(rounds):
        m = len(reps)
        used_full = set(reps)
        for (x, y) in reps:
            used_full.add((n - 1 - x, n - 1 - y))
        cells = [(x, y) for x in range(n) for y in range((n - 1) // 2 + 1)
                 if (x, y) not in used_full]
        if not cells:
            break
        # score all cells (exact single-insertion dE)
        vals = []
        for cell in cells:
            d1, d2 = HR.insert_delta(reps, n, cell)
            dE = (d1 - (6 * m + 1)) + 3 * (d2 - (2 * m + 1))
            vals.append((dE, cell))
        vals.sort()
        # pick randomly among the top-k
        pool = vals[:min(topk, len(vals))]
        # weight: prefer small dE
        weights = [1.0 / (1 + max(0, d)) for (d, _) in pool]
        cell = rng.choices([c for (_, c) in pool], weights=weights, k=1)[0]
        if m >= target_m:
            # at target size: replace a random rep instead of growing
            i = rng.randrange(m)
            old = reps[i]
            d = HR.move_delta(n, reps, i, cell)
            if d is None:
                continue
            dE = d[0] + 3 * d[1]
            if dE <= 0 or rng.random() < 0.2:
                reps[i] = cell
                reps, E = HR.best_improvement(n, reps, max_sweeps=5, log=None)
            else:
                E = excess_of(reps, n)
        else:
            reps = reps + [cell]
            reps, E = HR.best_improvement(n, reps, max_sweeps=5, log=None)
        if E < best[0]:
            best = (E, [p for p in reps])
            if log:
                log.write(f"  round {rnd}: NEW BEST E={E} m={len(reps)} "
                          f"({time.time()-t0:.0f}s)\n")
                log.flush()
            if E == 0 and len(reps) == target_m:
                return best[1], 0
        if log and rnd % 20 == 0:
            log.write(f"round {rnd}: E={E} m={len(reps)} best={best[0]} "
                      f"({time.time()-t0:.0f}s)\n")
            log.flush()
    return best[1], best[0]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seedfile", type=str, required=True)
    ap.add_argument("--rounds", type=int, default=200)
    ap.add_argument("--topk", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()
    with open(args.seedfile) as f:
        reps = [tuple(p) for p in json.load(f)["reps"]]
    reps, E = run(args.n, reps, args.n, rounds=args.rounds, seed=args.seed,
                  log=sys.stdout, topk=args.topk)
    out = {"n": args.n, "E": E, "solution": E == 0, "reps": reps}
    if args.out:
        with open(args.out, "w") as f:
            json.dump(out, f, indent=1)
    print("final E:", E, "m:", len(reps))
